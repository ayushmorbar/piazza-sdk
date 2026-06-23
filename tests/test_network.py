"""Tests for api/network.py facade layer.

Covers session lifecycle, delegation to domain functions, input validation,
error wrapping, and async iterators. Methods already tested in
test_feature_parity.py and test_advanced_features.py are excluded.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from piazza_sdk.api.network import Network
from piazza_sdk.exceptions import FeedError, NotFoundError, PiazzaSDKError, ValidationError
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType
from piazza_sdk.models.feed import Feed, FeedFilter, FeedItem, FolderFilter
from piazza_sdk.models.network import HallOfFameItem, Statistics
from piazza_sdk.models.post import AssetUploadResponse, Post, PostCreatedResponse, PublishingOptions
from piazza_sdk.models.user import User

# ── Helpers ───────────────────────────────────────────────────────────


def _make_network() -> Network:
    """Create a Network with mocked internals."""
    net = object.__new__(Network)
    net._rpc = AsyncMock()
    net._session = AsyncMock()
    net._nid = "test_nid"
    return net


def _make_feed_item(item_id: str = "item_1", subject: str = "Subject") -> FeedItem:
    return FeedItem(
        id=item_id,
        subject=subject,
        type=FeedItemType.QUESTION,
        created=datetime.now(UTC),
        updated=datetime.now(UTC),
        default_anonymity=FeedItemDefaultAnonymity.NO,
    )


def _make_feed(items: list[FeedItem] | None = None) -> MagicMock:
    feed = MagicMock(spec=Feed)
    feed.feed = [_make_feed_item()] if items is None else items
    return feed


# ── Session lifecycle ─────────────────────────────────────────────────


class TestEnsureSession:
    @pytest.mark.asyncio
    async def test_refreshes_when_needed(self) -> None:
        net = _make_network()
        net._session.needs_refresh = True
        net._session.refresh = AsyncMock()
        net._rpc.get_my_feed = AsyncMock(return_value={"result": {"feed": []}})
        with patch("piazza_sdk.api.network._domain_get_feed") as mock_feed:
            mock_feed.return_value = _make_feed([])
            await net.get_feed()
        net._session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_refresh_when_not_needed(self) -> None:
        net = _make_network()
        net._session.needs_refresh = False
        net._session.refresh = AsyncMock()
        with patch("piazza_sdk.api.network._domain_get_feed") as mock_feed:
            mock_feed.return_value = _make_feed([])
            await net.get_feed()
        net._session.refresh.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_session_skips_refresh(self) -> None:
        net = _make_network()
        net._session = None
        with patch("piazza_sdk.api.network._domain_get_feed") as mock_feed:
            mock_feed.return_value = _make_feed([])
            result = await net.get_feed()
        assert isinstance(result, Feed)


# ── Feed delegation ───────────────────────────────────────────────────


class TestGetFeedDelegation:
    @pytest.mark.asyncio
    async def test_passes_limit_and_offset(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_feed") as mock:
            mock.return_value = _make_feed()
            await net.get_feed(limit=25, offset=10)
        mock.assert_awaited_once_with(net._rpc, limit=25, offset=10)

    @pytest.mark.asyncio
    async def test_passes_kwargs(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_feed") as mock:
            mock.return_value = _make_feed()
            await net.get_feed(limit=50, offset=0, updated=True)
        mock.assert_awaited_once_with(net._rpc, limit=50, offset=0, updated=True)


class TestGetUserUnreadFeed:
    @pytest.mark.asyncio
    async def test_passes_updated_true(self) -> None:
        net = _make_network()
        net.get_feed = AsyncMock(return_value=_make_feed())
        result = await net.get_user_unread_feed(limit=10, offset=5)
        assert isinstance(result, Feed)
        net.get_feed.assert_awaited_once_with(limit=10, offset=5, updated=True)


class TestGetUserPostedFeed:
    @pytest.mark.asyncio
    async def test_passes_my_post_true(self) -> None:
        net = _make_network()
        net.get_feed = AsyncMock(return_value=_make_feed())
        result = await net.get_user_posted_feed(limit=20, offset=0)
        assert isinstance(result, Feed)
        net.get_feed.assert_awaited_once_with(limit=20, offset=0, my_post=True)


class TestGetFilteredFeed:
    @pytest.mark.asyncio
    async def test_passes_filter_kwargs(self) -> None:
        net = _make_network()
        net.get_feed = AsyncMock(return_value=_make_feed())

        class KwargsFilter(FeedFilter):
            def to_kwargs(self) -> dict[str, bool]:
                return {"my_post": True}

        flt = KwargsFilter()
        await net.get_filtered_feed(flt, limit=15)
        net.get_feed.assert_awaited_once_with(limit=15, offset=0, my_post=True)


class TestGetFolderContents:
    @pytest.mark.asyncio
    async def test_creates_folder_filter(self) -> None:
        net = _make_network()
        net.get_filtered_feed = AsyncMock(return_value=_make_feed())
        result = await net.get_folder_contents("Homework 1")
        assert isinstance(result, Feed)
        call_args = net.get_filtered_feed.call_args
        assert isinstance(call_args[0][0], FolderFilter)
        assert call_args[0][0].folder_name == "Homework 1"


class TestGetSimilarPosts:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_similar_posts("")

    @pytest.mark.asyncio
    async def test_whitespace_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_similar_posts("   ")

    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_similar_posts") as mock:
            mock.return_value = [_make_feed_item()]
            result = await net.get_similar_posts("post_1")
        assert len(result) == 1
        mock.assert_awaited_once_with(net._rpc, post_id="post_1")


# ── Post operations ───────────────────────────────────────────────────


class TestGetPost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_post("")

    @pytest.mark.asyncio
    async def test_whitespace_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_post("   ")

    @pytest.mark.asyncio
    async def test_empty_result_raises_not_found(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError, match="Post not found"):
            await net.get_post("missing_post")

    @pytest.mark.asyncio
    async def test_empty_dict_raises_not_found(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(return_value={})
        with pytest.raises(NotFoundError, match="Post not found"):
            await net.get_post("empty_post")

    @pytest.mark.asyncio
    async def test_returns_post_model(self) -> None:
        net = _make_network()
        raw = {
            "id": "p1",
            "title": "Test Post",
            "subject": "Test Subject",
            "type": "question",
            "author": "Alice",
            "nr": 5,
            "tags": ["hw1"],
            "folder": "Homework",
            "views": 100,
        }
        net._rpc.content_get = AsyncMock(return_value=raw)
        result = await net.get_post("p1")
        assert isinstance(result, Post)
        assert result.id == "p1"
        assert result.title == "Test Post"
        assert result.nr == 5
        assert result.tags == ["hw1"]

    @pytest.mark.asyncio
    async def test_parse_error_raises_piazza_sdk_error(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(side_effect=RuntimeError("json parse fail"))
        with pytest.raises(PiazzaSDKError, match="Failed to parse post"):
            await net.get_post("bad_post")

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(side_effect=NotFoundError("gone"))
        with pytest.raises(NotFoundError):
            await net.get_post("gone_post")


class TestCreatePost:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_create_post") as mock:
            mock.return_value = PostCreatedResponse(id="new_post")
            result = await net.create_post("title", "content")
        assert result.id == "new_post"
        mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_all_params(self) -> None:
        net = _make_network()
        opts = PublishingOptions(bypass_email=True)
        with patch("piazza_sdk.api.network._domain_create_post") as mock:
            mock.return_value = PostCreatedResponse(id="p1")
            await net.create_post(
                "title", "content", post_type="note", anonymous=True, options=opts, extra="val"
            )
        call_kwargs = mock.call_args[1]
        assert call_kwargs["title"] == "title"
        assert call_kwargs["content"] == "content"
        assert call_kwargs["post_type"] == "note"
        assert call_kwargs["anonymous"] is True
        assert call_kwargs["options"] is opts
        assert call_kwargs["extra"] == "val"


class TestCreateFollowup:
    @pytest.mark.asyncio
    async def test_string_post_id(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_add_followup") as mock:
            mock.return_value = {"ok": True}
            await net.create_followup("p1", "followup content")
        mock.assert_awaited_once()
        assert mock.call_args[1]["post_id"] == "p1"

    @pytest.mark.asyncio
    async def test_post_model_extracts_id(self) -> None:
        net = _make_network()
        post = Post(id="p2", title="t", raw={})
        with patch("piazza_sdk.api.network._domain_add_followup") as mock:
            mock.return_value = {"ok": True}
            await net.create_followup(post, "content")
        assert mock.call_args[1]["post_id"] == "p2"

    @pytest.mark.asyncio
    async def test_passes_options(self) -> None:
        net = _make_network()
        opts = PublishingOptions(silent_update=True)
        with patch("piazza_sdk.api.network._domain_add_followup") as mock:
            mock.return_value = {"ok": True}
            await net.create_followup("p1", "content", anonymous=True, options=opts)
        call_kwargs = mock.call_args[1]
        assert call_kwargs["anonymous"] is True
        assert call_kwargs["options"] is opts


class TestResolvePost:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_resolve_post") as mock:
            mock.return_value = True
            result = await net.resolve_post("p1")
        mock.assert_awaited_once_with(net._rpc, post_id="p1")
        assert result is True


class TestDeletePost:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_delete_post") as mock:
            mock.return_value = True
            result = await net.delete_post("p1")
        assert result is True
        mock.assert_awaited_once_with(net._rpc, post_id="p1")


class TestMarkAsUnread:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_mark_as_unread") as mock:
            mock.return_value = True
            result = await net.mark_as_unread("p1")
        assert result is True
        mock.assert_awaited_once_with(net._rpc, post_id="p1")


class TestEndorsePost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.endorse_post("")

    @pytest.mark.asyncio
    async def test_delegates_and_fetches_post(self) -> None:
        net = _make_network()
        with (
            patch("piazza_sdk.api.network._domain_endorse") as mock_endorse,
            patch.object(net, "get_post", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Post(id="p1", title="t", raw={})
            result = await net.endorse_post("p1", as_instructor_badge=True)
        mock_endorse.assert_awaited_once_with(net._rpc, post_id="p1", as_instructor_badge=True)
        mock_get.assert_awaited_once_with("p1")
        assert isinstance(result, Post)


class TestPinPost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.pin_post("")

    @pytest.mark.asyncio
    async def test_adds_pin_tag_and_returns_post(self) -> None:
        net = _make_network()
        with (
            patch.object(net, "add_tag", new_callable=AsyncMock) as mock_tag,
            patch.object(net, "get_post", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Post(id="p1", title="t", raw={})
            result = await net.pin_post("p1")
        mock_tag.assert_awaited_once_with("p1", "pin")
        mock_get.assert_awaited_once_with("p1")
        assert isinstance(result, Post)


class TestLockPost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.lock_post("")

    @pytest.mark.asyncio
    async def test_adds_lock_tag_and_returns_post(self) -> None:
        net = _make_network()
        with (
            patch.object(net, "add_tag", new_callable=AsyncMock) as mock_tag,
            patch.object(net, "get_post", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Post(id="p1", title="t", raw={})
            result = await net.lock_post("p1")
        mock_tag.assert_awaited_once_with("p1", "lock")
        mock_get.assert_awaited_once_with("p1")
        assert isinstance(result, Post)


class TestAddTag:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_add_tag") as mock:
            await net.add_tag("p1", "important")
        mock.assert_awaited_once_with(net._rpc, post_id="p1", tag="important")


class TestRemoveTag:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_remove_tag") as mock:
            await net.remove_tag("p1", "old_tag")
        mock.assert_awaited_once_with(net._rpc, post_id="p1", tag="old_tag")


class TestCreateFolder:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_create_folder") as mock:
            mock.return_value = ["HW1", "HW2", "HW3"]
            result = await net.create_folder("HW3")
        assert result == ["HW1", "HW2", "HW3"]
        mock.assert_awaited_once_with(net._rpc, folder_name="HW3")


class TestSaveDraft:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_save_draft") as mock:
            mock.return_value = "draft_123"
            result = await net.save_draft("subject", "content", post_type="note")
        assert result == "draft_123"
        mock.assert_awaited_once_with(
            net._rpc, subject="subject", content="content", post_type="note"
        )


class TestUploadAsset:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        file_data = b"\x89PNG\r\n"
        with patch("piazza_sdk.api.network._domain_upload_asset") as mock:
            mock.return_value = AssetUploadResponse(id="asset_1", url="https://example.com/file.png")
            result = await net.upload_asset("photo.png", file_data)
        assert result.id == "asset_1"
        mock.assert_awaited_once_with(
            net._rpc, filename="photo.png", file_data=file_data, content_type=None
        )

    @pytest.mark.asyncio
    async def test_passes_content_type(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_upload_asset") as mock:
            mock.return_value = AssetUploadResponse(id="a1")
            await net.upload_asset("doc.pdf", b"data", content_type="application/pdf")
        mock.assert_awaited_once_with(
            net._rpc, filename="doc.pdf", file_data=b"data", content_type="application/pdf"
        )


# ── Users ─────────────────────────────────────────────────────────────


class TestGetUsers:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_all_users") as mock:
            mock.return_value = [User(id="u1", name="Alice")]
            result = await net.get_users()
        assert len(result) == 1
        assert result[0].id == "u1"
        mock.assert_awaited_once_with(net._rpc)


class TestGetInstructorStats:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_instructor_stats") as mock:
            mock.return_value = {"total_questions": 50}
            result = await net.get_instructor_stats()
        assert result == {"total_questions": 50}
        mock.assert_awaited_once_with(net._rpc)


class TestGetOnlineUsers:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_online_users") as mock:
            mock.return_value = [User(id="u1")]
            result = await net.get_online_users()
        assert len(result) == 1
        assert result[0].id == "u1"
        mock.assert_awaited_once_with(net._rpc)


# ── Search & Statistics ───────────────────────────────────────────────


class TestSearch:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_search") as mock:
            mock.return_value = _make_feed()
            result = await net.search("homework 1")
        assert isinstance(result, Feed)
        mock.assert_awaited_once_with(net._rpc, query="homework 1")

    @pytest.mark.asyncio
    async def test_passes_kwargs(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_search") as mock:
            mock.return_value = _make_feed()
            await net.search("q", folder="HW1")
        mock.assert_awaited_once_with(net._rpc, query="q", folder="HW1")


class TestGetStatistics:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        mock_stats = MagicMock(spec=Statistics)
        with patch("piazza_sdk.api.network._domain_get_statistics") as mock:
            mock.return_value = mock_stats
            result = await net.get_statistics()
        assert result is mock_stats
        mock.assert_awaited_once_with(net._rpc)


# ── Hall of Fame ──────────────────────────────────────────────────────


class TestGetHallOfFame:
    @pytest.mark.asyncio
    async def test_extracts_best_answer_items(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(
            return_value={
                "result": {
                    "hof": {
                        "best_answer": [
                            {"uid": "u1", "nr": 10, "text": "Great answer"}
                        ]
                    }
                }
            }
        )
        result = await net.get_hall_of_fame()
        assert len(result) == 1
        assert isinstance(result[0], HallOfFameItem)

    @pytest.mark.asyncio
    async def test_missing_hof_returns_empty(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(return_value={"result": {}})
        result = await net.get_hall_of_fame()
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_result_returns_empty(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(return_value={})
        result = await net.get_hall_of_fame()
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_best_answer_returns_empty(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(
            return_value={"result": {"hof": {"best_answer": []}}}
        )
        result = await net.get_hall_of_fame()
        assert result == []

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(side_effect=FeedError("api fail"))
        with pytest.raises(FeedError):
            await net.get_hall_of_fame()

    @pytest.mark.asyncio
    async def test_unexpected_error_wraps_in_feed_error(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(side_effect=RuntimeError("unexpected"))
        with pytest.raises(FeedError, match="Failed to retrieve hall of fame"):
            await net.get_hall_of_fame()


# ── Async iterators ───────────────────────────────────────────────────


class TestIterAllPosts:
    @pytest.mark.asyncio
    async def test_yields_posts(self) -> None:
        net = _make_network()
        items = [_make_feed_item("p1", "Post 1"), _make_feed_item("p2", "Post 2")]
        feed = _make_feed(items)
        net.get_feed = AsyncMock(return_value=feed)
        net.get_post = AsyncMock(
            side_effect=[
                Post(id="p1", title="Post 1", raw={}),
                Post(id="p2", title="Post 2", raw={}),
            ]
        )

        posts = []
        async for post in net.iter_all_posts(limit=10, delay_seconds=0):
            posts.append(post)

        assert len(posts) == 2
        assert posts[0].id == "p1"
        assert posts[1].id == "p2"
        net.get_feed.assert_awaited_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_empty_feed_yields_nothing(self) -> None:
        net = _make_network()
        empty_feed = MagicMock(spec=Feed)
        empty_feed.feed = []
        net.get_feed = AsyncMock(return_value=empty_feed)
        net.get_post = AsyncMock()
        posts = []
        async for post in net.iter_all_posts():
            posts.append(post)
        assert posts == []
        net.get_post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_respects_limit(self) -> None:
        net = _make_network()
        items = [_make_feed_item(f"p{i}") for i in range(5)]
        net.get_feed = AsyncMock(return_value=_make_feed(items))
        net.get_post = AsyncMock(side_effect=lambda pid: Post(id=pid, title="t", raw={}))

        posts = []
        async for post in net.iter_all_posts(limit=3, delay_seconds=0):
            posts.append(post)

        net.get_feed.assert_awaited_once_with(limit=3)


class TestListenForEvents:
    @pytest.mark.asyncio
    async def test_yields_new_items(self) -> None:
        net = _make_network()
        item = _make_feed_item("item_1", "New post")
        feed = _make_feed([item])
        net.get_feed = AsyncMock(return_value=feed)

        gen = net.listen_for_events(poll_interval=0)
        result = await gen.__anext__()
        await gen.aclose()

        assert result.id == "item_1"

    @pytest.mark.asyncio
    async def test_deduplicates_across_polls(self) -> None:
        """First poll yields 1 item; second poll (same item) yields 0 → blocks → close."""
        net = _make_network()
        item = _make_feed_item("item_1", "Same post")
        call_count = 0

        async def feed_side_effect(*args: Any, **kwargs: Any) -> Feed:
            nonlocal call_count
            call_count += 1
            return _make_feed([item])

        net.get_feed = feed_side_effect  # type: ignore[assignment]

        gen = net.listen_for_events(poll_interval=0)
        first = await gen.__anext__()
        assert first.id == "item_1"
        assert call_count == 1

        # Second poll returns same item → generator should not yield again.
        # Use wait_for with timeout to avoid hanging.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(gen.__anext__(), timeout=0.05)
        await gen.aclose()
        assert call_count >= 2

    @pytest.mark.asyncio
    async def test_yields_multiple_new_items(self) -> None:
        net = _make_network()
        items = [_make_feed_item(f"i{i}", f"Item {i}") for i in range(3)]
        feed = _make_feed(items)
        net.get_feed = AsyncMock(return_value=feed)

        gen = net.listen_for_events(poll_interval=0)
        results = []
        for _ in range(3):
            results.append(await gen.__anext__())
        await gen.aclose()

        assert len(results) == 3
        assert [r.id for r in results] == ["i0", "i1", "i2"]


# ── Error wrapping via _handle_errors ─────────────────────────────────


class TestHandleErrors:
    """Test the _handle_errors decorator behavior through public methods."""

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates(self) -> None:
        """Bare delegations let errors propagate directly."""
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_search") as mock:
            mock.side_effect = RuntimeError("something broke")
            with pytest.raises(RuntimeError, match="something broke"):
                await net.search("test query")

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_not_double_wrapped(self) -> None:
        """PiazzaSDKError subclasses should pass through without wrapping."""
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_search") as mock:
            mock.side_effect = NotFoundError("not found")
            with pytest.raises(NotFoundError, match="not found"):
                await net.search("test")

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_propagates(self) -> None:
        """PiazzaSDKError subclasses pass through unchanged."""
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_search") as mock:
            mock.side_effect = NotFoundError("not found")
            with pytest.raises(NotFoundError, match="not found"):
                await net.search("test")

    @pytest.mark.asyncio
    async def test_get_statistics_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_statistics") as mock:
            mock.side_effect = RuntimeError("stats fail")
            with pytest.raises(RuntimeError, match="stats fail"):
                await net.get_statistics()

    @pytest.mark.asyncio
    async def test_get_users_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_all_users") as mock:
            mock.side_effect = RuntimeError("users fail")
            with pytest.raises(RuntimeError, match="users fail"):
                await net.get_users()

    @pytest.mark.asyncio
    async def test_get_instructor_stats_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_instructor_stats") as mock:
            mock.side_effect = RuntimeError("stats fail")
            with pytest.raises(RuntimeError, match="stats fail"):
                await net.get_instructor_stats()

    @pytest.mark.asyncio
    async def test_get_online_users_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_get_online_users") as mock:
            mock.side_effect = RuntimeError("users fail")
            with pytest.raises(RuntimeError, match="users fail"):
                await net.get_online_users()

    @pytest.mark.asyncio
    async def test_add_tag_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_add_tag") as mock:
            mock.side_effect = RuntimeError("tag fail")
            with pytest.raises(RuntimeError, match="tag fail"):
                await net.add_tag("p1", "tag")

    @pytest.mark.asyncio
    async def test_remove_tag_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_remove_tag") as mock:
            mock.side_effect = RuntimeError("tag fail")
            with pytest.raises(RuntimeError, match="tag fail"):
                await net.remove_tag("p1", "tag")

    @pytest.mark.asyncio
    async def test_delete_post_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_delete_post") as mock:
            mock.side_effect = RuntimeError("delete fail")
            with pytest.raises(RuntimeError, match="delete fail"):
                await net.delete_post("p1")

    @pytest.mark.asyncio
    async def test_mark_as_unread_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_mark_as_unread") as mock:
            mock.side_effect = RuntimeError("mark fail")
            with pytest.raises(RuntimeError, match="mark fail"):
                await net.mark_as_unread("p1")

    @pytest.mark.asyncio
    async def test_resolve_post_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_resolve_post") as mock:
            mock.side_effect = RuntimeError("resolve fail")
            with pytest.raises(RuntimeError, match="resolve fail"):
                await net.resolve_post("p1")

    @pytest.mark.asyncio
    async def test_save_draft_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_save_draft") as mock:
            mock.side_effect = RuntimeError("draft fail")
            with pytest.raises(RuntimeError, match="draft fail"):
                await net.save_draft("subj", "cont")

    @pytest.mark.asyncio
    async def test_upload_asset_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_upload_asset") as mock:
            mock.side_effect = RuntimeError("upload fail")
            with pytest.raises(RuntimeError, match="upload fail"):
                await net.upload_asset("f.txt", b"data")

    @pytest.mark.asyncio
    async def test_create_folder_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_create_folder") as mock:
            mock.side_effect = RuntimeError("folder fail")
            with pytest.raises(RuntimeError, match="folder fail"):
                await net.create_folder("HW1")

    @pytest.mark.asyncio
    async def test_answer_post_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_answer_post") as mock:
            mock.side_effect = RuntimeError("answer fail")
            with pytest.raises(RuntimeError, match="answer fail"):
                await net.answer_post("p1", "answer")

    @pytest.mark.asyncio
    async def test_endorse_post_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_endorse") as mock:
            mock.side_effect = RuntimeError("endorse fail")
            with pytest.raises(RuntimeError, match="endorse fail"):
                await net.endorse_post("p1")

    @pytest.mark.asyncio
    async def test_create_followup_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_add_followup") as mock:
            mock.side_effect = RuntimeError("followup fail")
            with pytest.raises(RuntimeError, match="followup fail"):
                await net.create_followup("p1", "content")

    @pytest.mark.asyncio
    async def test_create_post_error_propagates(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_create_post") as mock:
            mock.side_effect = RuntimeError("create fail")
            with pytest.raises(RuntimeError, match="create fail"):
                await net.create_post("title", "content")
