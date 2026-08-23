"""Tests for domain logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from piazza_sdk.domain.network import (
    update_course_description,
    update_general_information,
    update_office_hours,
)


class TestNetworkDomain:
    async def test_update_office_hours(self) -> None:

        rpc = _make_rpc()
        rpc.network_update = AsyncMock(return_value={"result": "success"})
        res = await update_office_hours(rpc, staff_uid="uid123", time="4", location="dse")
        assert res == {"result": "success"}
        rpc.network_update.assert_awaited_once_with(
            office_hours={"uid123": {"time": "4", "location": "dse"}}
        )

    async def test_update_general_information(self) -> None:

        rpc = _make_rpc()
        rpc.network_update = AsyncMock(return_value={"result": "success"})
        res = await update_general_information(
            rpc, info=[{"label": "label here", "text": "info here"}]
        )
        assert res == {"result": "success"}
        rpc.network_update.assert_awaited_once_with(
            general_information=[{"label": "label here", "text": "info here"}]
        )

    async def test_update_course_description(self) -> None:

        rpc = _make_rpc()
        rpc.network_update = AsyncMock(return_value={"result": "success"})
        res = await update_course_description(rpc, description="description")
        assert res == {"result": "success"}
        rpc.network_update.assert_awaited_once_with(course_description="description")


def _make_rpc() -> MagicMock:
    """Create a mock RPC client for domain function tests."""
    return MagicMock()
