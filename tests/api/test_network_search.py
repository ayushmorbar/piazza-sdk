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
