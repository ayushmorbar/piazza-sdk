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


class TestNetworkSettingsFacade:
    @pytest.mark.asyncio
    async def test_update_office_hours_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_update_office_hours") as mock:
            mock.return_value = {"result": "success"}
            res = await net.update_office_hours("uid123", "4", "dse")
            assert res == {"result": "success"}
            mock.assert_awaited_once_with(net._rpc, staff_uid="uid123", time="4", location="dse")

    @pytest.mark.asyncio
    async def test_update_general_information_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_update_general_information") as mock:
            mock.return_value = {"result": "success"}
            res = await net.update_general_information([{"label": "hi", "text": "there"}])
            assert res == {"result": "success"}
            mock.assert_awaited_once_with(net._rpc, info=[{"label": "hi", "text": "there"}])

    @pytest.mark.asyncio
    async def test_update_course_description_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_update_course_description") as mock:
            mock.return_value = {"result": "success"}
            res = await net.update_course_description("new desc")
            assert res == {"result": "success"}
            mock.assert_awaited_once_with(net._rpc, description="new desc")
