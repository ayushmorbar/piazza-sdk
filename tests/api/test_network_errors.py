"""Tests for api/network.py facade layer.

Covers session lifecycle, delegation to domain functions, input validation,
error wrapping, and async iterators. Methods already tested in
test_feature_parity.py and test_advanced_features.py are excluded.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from piazza_sdk.api.network import Network
from piazza_sdk.exceptions import NotFoundError
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType
from piazza_sdk.models.feed import Feed, FeedItem

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
