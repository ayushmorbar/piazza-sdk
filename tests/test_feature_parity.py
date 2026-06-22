"""Tests for additional feature parity additions."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.api.network import Network
from piazza_sdk.exceptions import ValidationError
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType
from piazza_sdk.models.feed import Feed, FeedItem, FolderFilter
from piazza_sdk.models.network import NetworkInfo
from piazza_sdk.models.post import Post
from piazza_sdk.models.user import User

# --- Phase 5a: Post unique_views + student_answer/instructor_answer ---


class TestPostUniqueViews:
    def test_default_is_none(self) -> None:
        post = Post(id="p1", title="t", raw={})
        assert post.unique_views is None

    def test_explicit_value(self) -> None:
        post = Post(id="p1", title="t", raw={}, unique_views=50)
        assert post.unique_views == 50


class TestPostAnswerProperties:
    def test_student_answer_filters_children(self) -> None:
        post = Post(
            id="p1",
            title="t",
            raw={},
            children=[
                {"id": "c1", "type": "s_answer", "subject": "student response"},
                {"id": "c2", "type": "i_answer", "subject": "instructor response"},
                {"id": "c3", "type": "followup", "subject": "followup"},
            ],
        )
        assert post.student_answer is not None
        assert post.student_answer.subject == "student response"

    def test_instructor_answer_filters_children(self) -> None:
        post = Post(
            id="p1",
            title="t",
            raw={},
            children=[
                {"id": "c1", "type": "s_answer", "subject": "student"},
                {"id": "c2", "type": "i_answer", "subject": "instructor"},
                {"id": "c3", "type": "i_answer", "subject": "instructor2"},
            ],
        )
        assert post.instructor_answer is not None
        assert post.instructor_answer.subject == "instructor"

    def test_no_answers_returns_none(self) -> None:
        post = Post(
            id="p1", title="t", raw={}, children=[{"id": "c1", "type": "followup", "subject": "f"}]
        )
        assert post.student_answer is None
        assert post.instructor_answer is None


# --- Phase 5b: FeedItem content_snippet alias ---


class TestFeedItemContentSnippet:
    def test_default_is_none(self) -> None:
        item = FeedItem(
            id="f1",
            subject="s",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
        )
        assert item.content_snippet is None

    def test_alias_content_snipet(self) -> None:
        item = FeedItem(
            id="f1",
            subject="s",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
            content_snipet="hello world",
        )
        assert item.content_snippet == "hello world"

    def test_populate_by_name(self) -> None:
        item = FeedItem(
            id="f1",
            subject="s",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
            content_snippet="test snippet",
        )
        assert item.content_snippet == "test snippet"


# --- Phase 5c: NetworkInfo new fields ---


class TestNetworkInfoNewFields:
    def test_folders_default_empty(self) -> None:
        info = NetworkInfo(id="n1", name="CS101")
        assert info.folders == []

    def test_instructors_default_empty(self) -> None:
        info = NetworkInfo(id="n1", name="CS101")
        assert info.instructors == []

    def test_status_default_none(self) -> None:
        info = NetworkInfo(id="n1", name="CS101")
        assert info.status is None

    def test_explicit_values(self) -> None:
        info = NetworkInfo(
            id="n1", name="CS101", folders=["HW1", "HW2"], instructors=["Prof X"], status="active"
        )
        assert info.folders == ["HW1", "HW2"]
        assert info.instructors == ["Prof X"]
        assert info.status == "active"


# --- Phase 5d: User class_roles + get_classes_by_role ---


class TestUserClassRoles:
    def test_default_empty(self) -> None:
        user = User(id="u1", name="Test")
        assert user.class_roles == {}

    def test_get_classes_by_role(self) -> None:
        user = User(
            id="u1",
            name="Test",
            class_roles={"network_1": "student", "network_2": "student", "network_3": "ta"},
        )
        assert user.get_classes_by_role("student") == ["network_1", "network_2"]
        assert user.get_classes_by_role("ta") == ["network_3"]

    def test_get_classes_by_role_empty(self) -> None:
        user = User(id="u1", name="Test")
        assert user.get_classes_by_role("student") == []


# --- Phase 6b: Network write methods ---


def _make_network() -> Network:
    """Create a Network with mocked internals."""
    net = object.__new__(Network)
    net._rpc = AsyncMock()
    net._session = AsyncMock()
    net._nid = "test_nid"
    net._client = MagicMock()
    return net


class TestNetworkAnswerPost:
    @pytest.mark.asyncio
    async def test_calls_rpc(self) -> None:
        net = _make_network()
        net._rpc.content_answer = AsyncMock()
        await net.answer_post("post_1", "my answer")
        net._rpc.content_answer.assert_called_once_with("post_1", "my answer", False)

    @pytest.mark.asyncio
    async def test_instructor_answer_flag(self) -> None:
        net = _make_network()
        net._rpc.content_answer = AsyncMock()
        await net.answer_post("post_1", "my answer", instructor_answer=True)
        net._rpc.content_answer.assert_called_once_with("post_1", "my answer", True)

    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.answer_post("", "answer")

    @pytest.mark.asyncio
    async def test_empty_content_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="content must be non-empty"):
            await net.answer_post("post_1", "")


class TestNetworkEndorsePost:
    @pytest.mark.asyncio
    async def test_calls_rpc(self) -> None:
        net = _make_network()
        net._rpc.content_upvote = AsyncMock()
        net._rpc.content_get = AsyncMock(return_value={
            "id": "post_1", "type": "question", "title": "t",
            "subject": "s", "author": "a", "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z", "nr": 0, "raw": {},
            "tags": [], "folder": "f", "views": 0,
            "config": {}, "children": [], "user_name": "u",
        })
        result = await net.endorse_post("post_1")
        net._rpc.content_upvote.assert_called_once_with("post_1")
        assert result.id == "post_1"

    @pytest.mark.asyncio
    async def test_empty_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.endorse_post("")


class TestNetworkAddTag:
    @pytest.mark.asyncio
    async def test_calls_rpc(self) -> None:
        net = _make_network()
        net._rpc.content_add_tag = AsyncMock()
        await net.add_tag("post_1", "important")
        net._rpc.content_add_tag.assert_called_once_with("post_1", "important")

    @pytest.mark.asyncio
    async def test_empty_tag_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="tag must be non-empty"):
            await net.add_tag("post_1", "")


class TestNetworkRemoveTag:
    @pytest.mark.asyncio
    async def test_calls_rpc(self) -> None:
        net = _make_network()
        net._rpc.content_remove_tag = AsyncMock()
        await net.remove_tag("post_1", "outdated")
        net._rpc.content_remove_tag.assert_called_once_with("post_1", "outdated")


class TestNetworkGetInstructorStats:
    @pytest.mark.asyncio
    async def test_calls_rpc(self) -> None:
        net = _make_network()
        net._rpc.get_instructor_stats = AsyncMock(return_value={"posts": 5})
        result = await net.get_instructor_stats()
        assert result == {"posts": 5}


class TestNetworkGetOnlineUsers:
    @pytest.mark.asyncio
    async def test_calls_rpc(self) -> None:
        net = _make_network()
        net._rpc.get_online_users = AsyncMock(return_value={"users": [{"id": "u1"}]})
        result = await net.get_online_users()
        assert result == [{"id": "u1"}]


class TestNetworkIterAllPosts:
    @pytest.mark.asyncio
    async def test_yields_posts(self) -> None:
        net = _make_network()
        item = FeedItem(
            id="post_1",
            subject="s",
            type=FeedItemType.QUESTION,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
        )
        feed = MagicMock(spec=Feed)
        feed.feed = [item]
        net.get_feed = AsyncMock(return_value=feed)
        mock_post = Post(id="post_1", title="t", raw={})
        net.get_post = AsyncMock(return_value=mock_post)

        posts = []
        async for post in net.iter_all_posts(limit=5, delay_seconds=0):
            posts.append(post)

        assert len(posts) == 1
        assert posts[0].id == "post_1"
        net.get_feed.assert_called_once_with(limit=5)
        net.get_post.assert_called_once_with("post_1")


class TestNetworkGetFolderContents:
    @pytest.mark.asyncio
    async def test_calls_get_filtered_feed(self) -> None:
        net = _make_network()
        feed = MagicMock(spec=Feed)
        net.get_filtered_feed = AsyncMock(return_value=feed)
        result = await net.get_folder_contents("Homework 1")
        assert result is feed
        net.get_filtered_feed.assert_called_once()
        call_arg = net.get_filtered_feed.call_args[0][0]
        assert isinstance(call_arg, FolderFilter)
        assert call_arg.folder_name == "Homework 1"
