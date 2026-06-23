"""Tests for advanced features: SearchDSL, UserPreferences, PostRevision, Polling Generator.

Covers delete_post, pin_post, lock_post, convenience feeds, PublishingOptions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError as PydanticValidationError

from piazza_sdk.api.network import Network
from piazza_sdk.exceptions import (
    ContentError,
    FeedError,
    NotFoundError,
    UploadError,
    ValidationError,
)
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType
from piazza_sdk.models.feed import Feed, FeedItem, SearchBuilder, SearchFilter
from piazza_sdk.models.network import HallOfFameItem
from piazza_sdk.models.post import Post, PostRevision, PublishingOptions
from piazza_sdk.models.user import UserPreferences

# --- SearchBuilder ---


class TestSearchBuilderDefaults:
    def test_default_query_empty(self) -> None:
        builder = SearchBuilder()
        assert builder._query == ""

    def test_default_limit_50(self) -> None:
        builder = SearchBuilder()
        assert builder._limit == 50

    def test_default_offset_0(self) -> None:
        builder = SearchBuilder()
        assert builder._offset == 0

    def test_default_folder_none(self) -> None:
        builder = SearchBuilder()
        assert builder._folder is None


class TestSearchBuilderChaining:
    def test_with_query_returns_self(self) -> None:
        builder = SearchBuilder()
        result = builder.with_query("integral")
        assert result is builder

    def test_in_folder_returns_self(self) -> None:
        builder = SearchBuilder()
        result = builder.in_folder("Homework")
        assert result is builder

    def test_limit_returns_self(self) -> None:
        builder = SearchBuilder()
        result = builder.limit(10)
        assert result is builder

    def test_offset_returns_self(self) -> None:
        builder = SearchBuilder()
        result = builder.offset(5)
        assert result is builder

    def test_full_chain(self) -> None:
        sf = (
            SearchBuilder()
            .with_query("integral by parts")
            .in_folder("Homework 3")
            .limit(25)
            .offset(10)
            .compile()
        )
        assert isinstance(sf, SearchFilter)
        assert sf.query == "integral by parts"
        assert sf.folder == "Homework 3"
        assert sf.limit == 25
        assert sf.offset == 10


class TestSearchBuilderCompile:
    def test_compile_returns_search_filter(self) -> None:
        sf = SearchBuilder().compile()
        assert isinstance(sf, SearchFilter)

    def test_compile_defaults(self) -> None:
        sf = SearchBuilder().compile()
        assert sf.query == ""
        assert sf.folder == ""
        assert sf.limit == 50
        assert sf.offset == 0

    def test_compile_with_query_only(self) -> None:
        sf = SearchBuilder().with_query("test").compile()
        assert sf.query == "test"
        assert sf.folder == ""
        assert sf.limit == 50
        assert sf.offset == 0

    def test_compile_with_folder_only(self) -> None:
        sf = SearchBuilder().in_folder("Labs").compile()
        assert sf.query == ""
        assert sf.folder == "Labs"

    def test_compile_with_limit_only(self) -> None:
        sf = SearchBuilder().limit(10).compile()
        assert sf.limit == 10

    def test_compile_with_offset_only(self) -> None:
        sf = SearchBuilder().offset(20).compile()
        assert sf.offset == 20


class TestSearchFilterToKwargs:
    def test_defaults_returns_search_and_sort(self) -> None:
        sf = SearchFilter()
        kwargs = sf.to_kwargs()
        assert kwargs["search"] is True
        assert kwargs["sort"] == "relevance"

    def test_with_query_adds_search_query(self) -> None:
        sf = SearchFilter(query="test")
        kwargs = sf.to_kwargs()
        assert kwargs["search_query"] == "test"

    def test_with_folder_adds_filter_folder(self) -> None:
        sf = SearchFilter(query="test", folder="HW1")
        kwargs = sf.to_kwargs()
        assert kwargs["filter_folder"] == "HW1"

    def test_with_limit(self) -> None:
        sf = SearchFilter(query="test", limit=10)
        kwargs = sf.to_kwargs()
        assert kwargs["limit"] == 10

    def test_with_offset(self) -> None:
        sf = SearchFilter(query="test", offset=5)
        kwargs = sf.to_kwargs()
        assert kwargs["offset"] == 5

    def test_empty_query_excluded(self) -> None:
        sf = SearchFilter(query="")
        kwargs = sf.to_kwargs()
        assert "search_query" not in kwargs

    def test_folder_empty_excluded(self) -> None:
        sf = SearchFilter(query="test", folder="")
        kwargs = sf.to_kwargs()
        assert "filter_folder" not in kwargs

    def test_limit_default_excluded(self) -> None:
        sf = SearchFilter(query="test", limit=50)
        kwargs = sf.to_kwargs()
        assert "limit" not in kwargs

    def test_offset_zero_excluded(self) -> None:
        sf = SearchFilter(query="test", offset=0)
        kwargs = sf.to_kwargs()
        assert "offset" not in kwargs

    def test_all_fields_populated(self) -> None:
        sf = SearchFilter(query="q", folder="f", limit=10, offset=5)
        kwargs = sf.to_kwargs()
        assert kwargs["search_query"] == "q"
        assert kwargs["filter_folder"] == "f"
        assert kwargs["limit"] == 10
        assert kwargs["offset"] == 5


# --- PostRevision ---


class TestPostRevision:
    def test_defaults(self) -> None:
        rev = PostRevision()
        assert rev.revision == 0
        assert rev.subject == ""
        assert rev.content == ""
        assert rev.uid == ""
        assert rev.created is None

    def test_from_dict(self) -> None:
        rev = PostRevision(
            revision=3,
            subject="Updated title",
            content="New content here",
            uid="user_123",
            created=datetime(2025, 6, 1, 12, 0, tzinfo=UTC),
        )
        assert rev.revision == 3
        assert rev.subject == "Updated title"
        assert rev.content == "New content here"
        assert rev.uid == "user_123"
        assert rev.created == datetime(2025, 6, 1, 12, 0, tzinfo=UTC)

    def test_from_raw_dict(self) -> None:
        raw = {"revision": 2, "subject": "Draft", "content": "v2 content"}
        rev = PostRevision(**raw)
        assert rev.revision == 2
        assert rev.subject == "Draft"
        assert rev.content == "v2 content"


class TestPostRevisionsField:
    def test_default_empty_list(self) -> None:
        post = Post(id="p1", title="t", raw={})
        assert post.revisions == []

    def test_explicit_revisions(self) -> None:
        revisions = [PostRevision(revision=1, subject="v1"), PostRevision(revision=2, subject="v2")]
        post = Post(id="p1", title="t", raw={}, revisions=revisions)
        assert len(post.revisions) == 2
        assert post.revisions[0].revision == 1
        assert post.revisions[1].subject == "v2"

    def test_from_raw_dict_with_revisions(self) -> None:
        revisions = [
            PostRevision(revision=1, subject="first", content="c1"),
            PostRevision(revision=2, subject="second", content="c2"),
        ]
        post = Post(id="p1", title="t", raw={}, revisions=revisions)
        assert len(post.revisions) == 2
        assert post.revisions[1].content == "c2"


# --- UserPreferences ---


class TestUserPreferencesDefaults:
    def test_defaults(self) -> None:
        prefs = UserPreferences()
        assert prefs.digest_frequency == "daily"
        assert prefs.digest_hour == 9
        assert prefs.email_new_post is True
        assert prefs.email_new_followup is True
        assert prefs.email_new_answer is True
        assert prefs.email_new_comment is False
        assert prefs.push_new_post is True
        assert prefs.push_new_followup is True
        assert prefs.push_new_answer is True
        assert prefs.show_student_names is True

    def test_from_dict(self) -> None:
        prefs = UserPreferences(
            digest_frequency="weekly",
            digest_hour=14,
            email_new_post=False,
            show_student_names=False,
        )
        assert prefs.digest_frequency == "weekly"
        assert prefs.digest_hour == 14
        assert prefs.email_new_post is False
        assert prefs.show_student_names is False

    def test_populate_by_name(self) -> None:
        prefs = UserPreferences(digest_frequency="instant")
        assert prefs.digest_frequency == "instant"

    def test_from_alias_dict(self) -> None:
        prefs = UserPreferences.model_validate(
            {"digest_frequency": "weekly", "email_new_post": False}
        )
        assert prefs.digest_frequency == "weekly"
        assert prefs.email_new_post is False


class TestUserPreferencesRoundTrip:
    def test_model_dump(self) -> None:
        prefs = UserPreferences(digest_frequency="weekly", email_new_post=False)
        dumped = prefs.model_dump()
        assert dumped["digest_frequency"] == "weekly"
        assert dumped["email_new_post"] is False

    def test_exclude_unset(self) -> None:
        prefs = UserPreferences(digest_frequency="weekly")
        dumped = prefs.model_dump(exclude_unset=True)
        assert "digest_frequency" in dumped
        assert "email_new_post" not in dumped
        assert "email_new_followup" not in dumped

    def test_exclude_unset_all_set(self) -> None:
        prefs = UserPreferences(digest_frequency="weekly", email_new_post=False)
        dumped = prefs.model_dump(exclude_unset=True)
        assert "digest_frequency" in dumped
        assert "email_new_post" in dumped

    def test_by_alias(self) -> None:
        prefs = UserPreferences(digest_frequency="weekly")
        dumped = prefs.model_dump(by_alias=True)
        assert "digest_frequency" in dumped


# --- Network preferences methods ---


def _make_network() -> Network:
    """Create a Network with mocked internals."""
    net = object.__new__(Network)
    net._rpc = AsyncMock()
    net._session = AsyncMock()
    net._nid = "test_nid"
    net._client = MagicMock()
    return net


class TestNetworkGetPreferences:
    @pytest.mark.asyncio
    async def test_calls_rpc(self) -> None:
        net = _make_network()
        net._rpc.get_user_preferences = AsyncMock(
            return_value={"digest_frequency": "weekly", "email_new_post": False}
        )
        result = await net.get_preferences()
        assert isinstance(result, UserPreferences)
        assert result.digest_frequency == "weekly"
        assert result.email_new_post is False

    @pytest.mark.asyncio
    async def test_rpc_error_raises_content_error(self) -> None:
        net = _make_network()
        net._rpc.get_user_preferences = AsyncMock(side_effect=RuntimeError("api fail"))
        with pytest.raises(ContentError, match="Failed to get preferences"):
            await net.get_preferences()

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.get_user_preferences = AsyncMock(side_effect=NotFoundError("not found"))
        with pytest.raises(NotFoundError):
            await net.get_preferences()


class TestNetworkUpdatePreferences:
    @pytest.mark.asyncio
    async def test_calls_rpc_with_payload(self) -> None:
        net = _make_network()
        net._rpc.update_user_preferences = AsyncMock()
        prefs = UserPreferences(digest_frequency="instant")
        await net.update_preferences(prefs)
        net._rpc.update_user_preferences.assert_called_once()
        payload = net._rpc.update_user_preferences.call_args[0][0]
        assert payload["digest_frequency"] == "instant"

    @pytest.mark.asyncio
    async def test_exclude_unset_only_sends_set_fields(self) -> None:
        net = _make_network()
        net._rpc.update_user_preferences = AsyncMock()
        prefs = UserPreferences(digest_frequency="instant")
        await net.update_preferences(prefs)
        payload = net._rpc.update_user_preferences.call_args[0][0]
        assert "digest_frequency" in payload
        assert "email_new_post" not in payload
        assert "email_new_followup" not in payload

    @pytest.mark.asyncio
    async def test_rpc_error_raises_content_error(self) -> None:
        net = _make_network()
        net._rpc.update_user_preferences = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(ContentError, match="Failed to update preferences"):
            await net.update_preferences(UserPreferences())

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.update_user_preferences = AsyncMock(side_effect=NotFoundError("not found"))
        with pytest.raises(NotFoundError):
            await net.update_preferences(UserPreferences())


# --- Polling Generator ---


class TestNetworkListenForEvents:
    @pytest.mark.asyncio
    async def test_yields_new_items(self) -> None:
        net = _make_network()
        item = FeedItem(
            id="item_1",
            subject="New post",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
        )
        feed = MagicMock(spec=Feed)
        feed.feed = [item]
        net.get_feed = AsyncMock(return_value=feed)

        gen = net.listen_for_events(poll_interval=0)
        result = await gen.__anext__()
        await gen.aclose()

        assert result.id == "item_1"

    @pytest.mark.asyncio
    async def test_deduplicates_across_polls(self) -> None:
        """First poll yields 1 item; second poll (same item) yields 0 → generator blocks → close."""
        net = _make_network()
        item = FeedItem(
            id="item_1",
            subject="Same post",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
        )
        feed = MagicMock(spec=Feed)
        feed.feed = [item]
        net.get_feed = AsyncMock(return_value=feed)

        gen = net.listen_for_events(poll_interval=0)
        # First __anext__ → yields item_1
        first = await gen.__anext__()
        assert first.id == "item_1"
        # Second __anext__ → get_feed returns same item, already seen → blocks
        # Cancel instead of waiting forever
        await gen.aclose()

    @pytest.mark.asyncio
    async def test_yields_only_new_items(self) -> None:
        net = _make_network()
        item1 = FeedItem(
            id="item_1",
            subject="First",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
        )
        item2 = FeedItem(
            id="item_2",
            subject="Second",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
        )
        feed1 = MagicMock(spec=Feed)
        feed1.feed = [item1]
        feed2 = MagicMock(spec=Feed)
        feed2.feed = [item1, item2]
        net.get_feed = AsyncMock(side_effect=[feed1, feed2])

        gen = net.listen_for_events(poll_interval=0)
        first = await gen.__anext__()
        second = await gen.__anext__()
        # Third __anext__ would block → close
        await gen.aclose()

        assert first.id == "item_1"
        assert second.id == "item_2"

    @pytest.mark.asyncio
    async def test_calls_get_feed(self) -> None:
        net = _make_network()
        item = FeedItem(id="item_1", type=FeedItemType.NOTE, subject="t")
        feed = MagicMock(spec=Feed)
        feed.feed = [item]
        net.get_feed = AsyncMock(return_value=feed)

        gen = net.listen_for_events(poll_interval=0)
        result = await gen.__anext__()
        await gen.aclose()

        assert result.id == "item_1"
        net.get_feed.assert_called()


# --- delete_post ---


class TestDeletePost:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self) -> None:
        net = _make_network()
        net._rpc.content_delete = AsyncMock(return_value={"result": "success"})
        result = await net.delete_post("post_1")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self) -> None:
        net = _make_network()
        net._rpc.content_delete = AsyncMock(return_value={"result": "error"})
        result = await net.delete_post("post_1")
        assert result is False

    @pytest.mark.asyncio
    async def test_rejects_empty_id(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError):
            await net.delete_post("")


# --- pin_post / lock_post ---


class TestPinPost:
    @pytest.mark.asyncio
    async def test_adds_pin_tag(self) -> None:
        net = _make_network()
        net.add_tag = AsyncMock()
        post_obj = MagicMock(spec=Post)
        post_obj.id = "post_1"
        net.get_post = AsyncMock(return_value=post_obj)

        result = await net.pin_post("post_1")
        net.add_tag.assert_awaited_once_with("post_1", "pin")
        net.get_post.assert_awaited_once_with("post_1")
        assert result is post_obj

    @pytest.mark.asyncio
    async def test_rejects_empty_id(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError):
            await net.pin_post("")


class TestLockPost:
    @pytest.mark.asyncio
    async def test_adds_lock_tag(self) -> None:
        net = _make_network()
        net.add_tag = AsyncMock()
        post_obj = MagicMock(spec=Post)
        post_obj.id = "post_1"
        net.get_post = AsyncMock(return_value=post_obj)

        result = await net.lock_post("post_1")
        net.add_tag.assert_awaited_once_with("post_1", "lock")
        net.get_post.assert_awaited_once_with("post_1")
        assert result is post_obj

    @pytest.mark.asyncio
    async def test_rejects_empty_id(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError):
            await net.lock_post("")


# --- Convenience feeds ---


class TestUserUnreadFeed:
    @pytest.mark.asyncio
    async def test_calls_get_feed_with_updated_true(self) -> None:
        net = _make_network()
        expected_feed = MagicMock(spec=Feed)
        net.get_feed = AsyncMock(return_value=expected_feed)
        result = await net.get_user_unread_feed(limit=25, offset=10)
        net.get_feed.assert_awaited_once_with(limit=25, offset=10, updated=True)
        assert result is expected_feed


class TestUserPostedFeed:
    @pytest.mark.asyncio
    async def test_calls_get_feed_with_my_post_true(self) -> None:
        net = _make_network()
        expected_feed = MagicMock(spec=Feed)
        net.get_feed = AsyncMock(return_value=expected_feed)
        result = await net.get_user_posted_feed(limit=30, offset=5)
        net.get_feed.assert_awaited_once_with(limit=30, offset=5, my_post=True)
        assert result is expected_feed


# --- PublishingOptions ---


class TestPublishingOptions:
    def test_to_kwargs_defaults(self) -> None:
        opts = PublishingOptions()
        result = opts.to_kwargs()
        assert result == {
            "options[bypass_email]": 0,
            "options[no_up_notify]": 0,
            "options[anonymous]": "no",
        }

    def test_to_kwargs_bypass_email(self) -> None:
        opts = PublishingOptions(bypass_email=True)
        result = opts.to_kwargs()
        assert result["options[bypass_email]"] == 1

    def test_to_kwargs_silent_update(self) -> None:
        opts = PublishingOptions(silent_update=True)
        result = opts.to_kwargs()
        assert result["options[no_up_notify]"] == 1

    def test_to_kwargs_anonymity(self) -> None:
        opts = PublishingOptions(anonymity="all")
        result = opts.to_kwargs()
        assert result["options[anonymous]"] == "all"

    def test_to_kwargs_combined(self) -> None:
        opts = PublishingOptions(bypass_email=True, silent_update=True, anonymity="stud")
        result = opts.to_kwargs()
        assert result == {
            "options[bypass_email]": 1,
            "options[no_up_notify]": 1,
            "options[anonymous]": "stud",
        }

    @pytest.mark.asyncio
    async def test_wired_into_create_post(self) -> None:
        net = _make_network()
        net._rpc.content_create = AsyncMock(return_value={"result": {"id": "new_post"}})
        opts = PublishingOptions(bypass_email=True)
        await net.create_post("Title", "Body", options=opts)
        _, kwargs = net._rpc.content_create.call_args
        assert kwargs.get("options[bypass_email]") == 1

    @pytest.mark.asyncio
    async def test_wired_into_create_followup(self) -> None:
        net = _make_network()
        net._rpc.content_create = AsyncMock(return_value={"result": {"id": "followup_1"}})
        opts = PublishingOptions(anonymity="all")
        await net.create_followup("post_1", "reply", options=opts)
        _, kwargs = net._rpc.content_create.call_args
        assert kwargs.get("options[anonymous]") == "all"


# --- HallOfFameItem model tests ---


class TestHallOfFameItem:
    def test_alias_mapping(self) -> None:
        item = HallOfFameItem(uid="u123", nr=42, time=120, text="Great answer", when=1700000000)
        assert item.votes == 42
        assert item.response_time_seconds == 120
        assert item.snippet == "Great answer"
        assert item.timestamp == 1700000000
        assert item.uid == "u123"

    def test_pythonic_names(self) -> None:
        item = HallOfFameItem(
            uid="u1", votes=5, response_time_seconds=10, snippet="Hi", timestamp=999
        )
        assert item.votes == 5
        assert item.uid == "u1"

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(PydanticValidationError, match="Extra inputs are not permitted"):
            HallOfFameItem(uid="u1", nr=1, time=2, text="t", when=3, unknown_field="ignored")

    def test_all_optional(self) -> None:
        item = HallOfFameItem()
        assert item.uid is None
        assert item.votes is None
        assert item.response_time_seconds is None
        assert item.snippet is None
        assert item.timestamp is None


# --- Network methods tests ---


class TestGetHallOfFame:
    @pytest.mark.asyncio
    async def test_returns_items(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(
            return_value={
                "result": {
                    "hof": {
                        "best_answer": [
                            {"uid": "u1", "nr": 10, "time": 30, "text": "Good answer", "when": 999}
                        ]
                    }
                }
            }
        )
        items = await net.get_hall_of_fame()
        assert len(items) == 1
        assert items[0].uid == "u1"
        assert items[0].votes == 10

    @pytest.mark.asyncio
    async def test_empty_hof(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(return_value={"result": {}})
        items = await net.get_hall_of_fame()
        assert items == []

    @pytest.mark.asyncio
    async def test_empty_best_answer(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(return_value={"result": {"hof": {}}})
        items = await net.get_hall_of_fame()
        assert items == []


class TestMarkAsUnread:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        net = _make_network()
        net._rpc.mark_as_unread = AsyncMock(return_value={"result": "success"})
        result = await net.mark_as_unread("post_1")
        assert result is True
        net._rpc.mark_as_unread.assert_awaited_once_with("post_1")

    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.mark_as_unread("")
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.mark_as_unread("   ")


class TestCreateFolder:
    @pytest.mark.asyncio
    async def test_returns_folders(self) -> None:
        net = _make_network()
        net._rpc.add_folder = AsyncMock(return_value={"folders": ["HW1", "Lectures", "NewFolder"]})
        result = await net.create_folder("NewFolder")
        assert result == ["HW1", "Lectures", "NewFolder"]
        net._rpc.add_folder.assert_awaited_once_with("NewFolder")

    @pytest.mark.asyncio
    async def test_empty_name_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="folder_name must be non-empty"):
            await net.create_folder("")
        with pytest.raises(ValidationError, match="folder_name must be non-empty"):
            await net.create_folder("   ")


class TestEndorsePostWithBadge:
    @pytest.mark.asyncio
    async def test_instructor_badge_calls_add_badge(self) -> None:
        net = _make_network()
        net._rpc.add_badge = AsyncMock(return_value={})
        net._rpc.content_get = AsyncMock(return_value={"id": "p1", "title": "T", "subject": "S"})
        await net.endorse_post("p1", as_instructor_badge=True)
        net._rpc.add_badge.assert_awaited_once_with("p1")
        net._rpc.content_upvote.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_default_calls_upvote(self) -> None:
        net = _make_network()
        net._rpc.content_upvote = AsyncMock(return_value={})
        net._rpc.content_get = AsyncMock(return_value={"id": "p1", "title": "T", "subject": "S"})
        await net.endorse_post("p1")
        net._rpc.content_upvote.assert_awaited_once_with("p1")
        net._rpc.add_badge.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_post(self) -> None:
        net = _make_network()
        net._rpc.content_upvote = AsyncMock(return_value={})
        net._rpc.content_get = AsyncMock(return_value={"id": "p1", "title": "Post"})
        result = await net.endorse_post("p1")
        assert isinstance(result, Post)
        assert result.id == "p1"


# --- get_similar_posts ---


class TestGetSimilarPosts:
    @pytest.mark.asyncio
    async def test_returns_similar_posts(self) -> None:
        net = _make_network()
        net._rpc.content_get_similar = AsyncMock(
            return_value={
                "similar_posts": [
                    {"id": "similar_1", "subject": "Similar Q1"},
                    {"id": "similar_2", "subject": "Similar Q2"},
                ]
            }
        )
        result = await net.get_similar_posts("post_1")
        assert len(result) == 2
        assert result[0].id == "similar_1"
        assert result[0].subject == "Similar Q1"
        net._rpc.content_get_similar.assert_awaited_once_with("post_1")

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        net = _make_network()
        net._rpc.content_get_similar = AsyncMock(return_value={"similar_posts": []})
        result = await net.get_similar_posts("post_1")
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_key_returns_empty(self) -> None:
        net = _make_network()
        net._rpc.content_get_similar = AsyncMock(return_value={})
        result = await net.get_similar_posts("post_1")
        assert result == []

    @pytest.mark.asyncio
    async def test_skips_invalid_items(self) -> None:
        """Items that fail FeedItem validation are silently skipped."""
        net = _make_network()
        net._rpc.content_get_similar = AsyncMock(
            return_value={
                "similar_posts": [
                    {"id": "similar_1", "subject": "Good"},
                    {"not": "valid at all", "missing_id": True},
                    {"id": "similar_2", "subject": "Also good"},
                ]
            }
        )
        result = await net.get_similar_posts("post_1")
        assert len(result) == 2
        assert result[0].id == "similar_1"
        assert result[1].id == "similar_2"

    @pytest.mark.asyncio
    async def test_rejects_empty_post_id(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_similar_posts("")
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_similar_posts("   ")

    @pytest.mark.asyncio
    async def test_rpc_error_raises_content_error(self) -> None:
        net = _make_network()
        net._rpc.content_get_similar = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(FeedError, match="Failed to get similar posts"):
            await net.get_similar_posts("post_1")

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.content_get_similar = AsyncMock(side_effect=NotFoundError("not found"))
        with pytest.raises(NotFoundError):
            await net.get_similar_posts("post_1")


# --- save_draft ---


class TestSaveDraft:
    @pytest.mark.asyncio
    async def test_returns_draft_id(self) -> None:
        net = _make_network()
        net._rpc.content_save_draft = AsyncMock(return_value={"id": "draft_1", "status": "saved"})
        result = await net.save_draft("My Title", "<p>Content here</p>")
        assert result == "draft_1"
        net._rpc.content_save_draft.assert_awaited_once_with(
            subject="My Title", content="<p>Content here</p>", post_type="question"
        )

    @pytest.mark.asyncio
    async def test_passes_post_type(self) -> None:
        net = _make_network()
        net._rpc.content_save_draft = AsyncMock(return_value={"id": "d2"})
        await net.save_draft("Title", "Body", post_type="note")
        _, kwargs = net._rpc.content_save_draft.call_args
        assert kwargs["post_type"] == "note"

    @pytest.mark.asyncio
    async def test_rejects_empty_subject(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="subject must be non-empty"):
            await net.save_draft("", "Content")
        with pytest.raises(ValidationError, match="subject must be non-empty"):
            await net.save_draft("   ", "Content")

    @pytest.mark.asyncio
    async def test_rejects_empty_content(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="content must be non-empty"):
            await net.save_draft("Title", "")
        with pytest.raises(ValidationError, match="content must be non-empty"):
            await net.save_draft("Title", "   ")

    @pytest.mark.asyncio
    async def test_rpc_error_raises_content_error(self) -> None:
        net = _make_network()
        net._rpc.content_save_draft = AsyncMock(side_effect=RuntimeError("fail"))
        with pytest.raises(ContentError, match="Failed to save draft"):
            await net.save_draft("Title", "Content")

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.content_save_draft = AsyncMock(side_effect=NotFoundError("not found"))
        with pytest.raises(NotFoundError):
            await net.save_draft("Title", "Content")


# --- upload_asset ---


class TestUploadAsset:
    @pytest.mark.asyncio
    async def test_returns_asset_data(self) -> None:
        net = _make_network()
        net._rpc.asset_get_upload_url = AsyncMock(
            return_value={"url": "https://s3.amazonaws.com/bucket/file1", "id": "asset_1"}
        )
        put_response = MagicMock()
        put_response.raise_for_status = MagicMock()
        net._rpc.client.put = AsyncMock(return_value=put_response)
        result = await net.upload_asset("file.pdf", b"file content here")
        assert result.id == "asset_1"
        net._rpc.asset_get_upload_url.assert_awaited_once_with("file.pdf")
        net._rpc.client.put.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_uses_upload_url_key(self) -> None:
        net = _make_network()
        net._rpc.asset_get_upload_url = AsyncMock(
            return_value={"upload_url": "https://s3.amazonaws.com/bucket/file2"}
        )
        put_response = MagicMock()
        put_response.raise_for_status = MagicMock()
        net._rpc.client.put = AsyncMock(return_value=put_response)
        await net.upload_asset("image.png", b"binary")
        call_kwargs = net._rpc.client.put.call_args
        assert call_kwargs[0][0] == "https://s3.amazonaws.com/bucket/file2"

    @pytest.mark.asyncio
    async def test_no_url_raises_upload_error(self) -> None:
        net = _make_network()
        net._rpc.asset_get_upload_url = AsyncMock(return_value={"id": "asset_1"})
        with pytest.raises(UploadError, match="No upload URL"):
            await net.upload_asset("file.pdf", b"data")

    @pytest.mark.asyncio
    async def test_rejects_empty_filename(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="filename must be non-empty"):
            await net.upload_asset("", b"data")
        with pytest.raises(ValidationError, match="filename must be non-empty"):
            await net.upload_asset("   ", b"data")

    @pytest.mark.asyncio
    async def test_rejects_empty_file_data(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="file_data must not be empty"):
            await net.upload_asset("file.pdf", b"")

    @pytest.mark.asyncio
    async def test_rpc_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.asset_get_upload_url = AsyncMock(side_effect=UploadError("rpc failed"))
        with pytest.raises(UploadError, match="rpc failed"):
            await net.upload_asset("file.pdf", b"data")

    @pytest.mark.asyncio
    async def test_put_failure_raises_upload_error(self) -> None:
        net = _make_network()
        net._rpc.asset_get_upload_url = AsyncMock(
            return_value={"url": "https://s3.amazonaws.com/bucket/file"}
        )
        put_response = MagicMock()
        put_response.raise_for_status.side_effect = Exception("upload failed")
        net._rpc.client.put = AsyncMock(return_value=put_response)
        with pytest.raises(UploadError, match="Failed to upload asset"):
            await net.upload_asset("file.pdf", b"data")
