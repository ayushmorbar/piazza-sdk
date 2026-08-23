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
from piazza_sdk.exceptions import FeedError
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType
from piazza_sdk.models.feed import Feed, FeedItem
from piazza_sdk.models.network import HallOfFameItem, Statistics
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
        # Post-envelope shape: RPC._safe_call already unwrapped {"result": ...}
        net._rpc.get_my_feed = AsyncMock(
            return_value={"hof": {"best_answer": [{"uid": "u1", "nr": 10, "text": "Great answer"}]}}
        )
        result = await net.get_hall_of_fame()
        assert len(result) == 1
        assert isinstance(result[0], HallOfFameItem)

    @pytest.mark.asyncio
    async def test_missing_hof_returns_empty(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(return_value={})
        result = await net.get_hall_of_fame()
        assert result == []

    @pytest.mark.asyncio
    async def test_non_dict_hof_returns_empty(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(return_value={"hof": "unexpected"})
        result = await net.get_hall_of_fame()
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_best_answer_returns_empty(self) -> None:
        net = _make_network()
        net._rpc.get_my_feed = AsyncMock(return_value={"hof": {"best_answer": []}})
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
