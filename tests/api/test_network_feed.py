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
from piazza_sdk.exceptions import ValidationError
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType
from piazza_sdk.models.feed import Feed, FeedFilter, FeedItem, FolderFilter
from piazza_sdk.models.post import Post

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
        # Single page: 2 items < page size 10 → no second fetch
        net.get_feed.assert_awaited_once_with(limit=10, offset=0)

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

        # The mock returns the same 5 items for any offset, so the stall guard
        # stops iteration after page 2; only the first call's args matter here.
        assert net.get_feed.await_count >= 1
        first_call = net.get_feed.await_args_list[0]
        assert first_call.kwargs["limit"] == 3
        assert first_call.kwargs["offset"] == 0


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
