"""Tests for domain logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.statistics import get_statistics
from piazza_sdk.exceptions import PiazzaSDKError
from piazza_sdk.models.network import Statistics


class TestGetStatistics:
    async def test_happy_path_returns_statistics(self) -> None:
        rpc = _make_rpc()
        rpc.get_stats = AsyncMock(
            return_value={
                "daily": [{"day": "06/24", "users": 5, "posts": 11, "questions": 9}],
                "users": [
                    {
                        "user_id": "u1",
                        "name": "Alice",
                        "email": "a@x.com",
                        "days": 3,
                        "posts": 10,
                        "asks": 5,
                        "answers": 3,
                        "views": 20,
                    }
                ],
                "profs": [
                    {
                        "user_id": "p1",
                        "name": "Prof",
                        "email": "p@x.com",
                        "days": 5,
                        "posts": 2,
                        "asks": 0,
                        "answers": 1,
                        "views": 10,
                    }
                ],
                "total": {
                    "posts": 150,
                    "questions": 80,
                    "i_answers": 10,
                    "s_answers": 60,
                    "net_time": 3600,
                    "anon_pool": 0,
                    "response_time": 120.5,
                },
                "top_users": [],
                "top_askers": [],
                "top_answerers": [],
                "top_listeners": [],
                "top_good_q": [],
                "top_good_a": [],
            }
        )
        result = await get_statistics(rpc)
        assert isinstance(result, Statistics)
        assert result.total.posts == 150
        assert result.total.questions == 80
        assert result.total.s_answers == 60
        assert len(result.users) == 1
        assert result.users[0].name == "Alice"
        assert len(result.profs) == 1
        assert result.profs[0].name == "Prof"
        assert len(result.daily) == 1
        assert result.daily[0].posts == 11
        rpc.get_stats.assert_awaited_once()

    async def test_happy_path_missing_keys_use_defaults(self) -> None:
        rpc = _make_rpc()
        rpc.get_stats = AsyncMock(return_value={})
        result = await get_statistics(rpc)
        assert isinstance(result, Statistics)
        assert result.total.posts == 0
        assert result.users == []
        assert result.profs == []

    async def test_rpc_error_wraps_in_piazza_sdk_error(self) -> None:
        rpc = _make_rpc()
        rpc.get_stats = AsyncMock(side_effect=RuntimeError("connection lost"))
        with pytest.raises(PiazzaSDKError, match="Failed to get statistics"):
            await get_statistics(rpc)

    async def test_piazza_sdk_error_passthrough(self) -> None:
        rpc = _make_rpc()
        rpc.get_stats = AsyncMock(side_effect=PiazzaSDKError("api error"))
        with pytest.raises(PiazzaSDKError, match="api error"):
            await get_statistics(rpc)


# --- search ---


def _make_rpc() -> MagicMock:
    """Create a mock RPC client for domain function tests."""
    return MagicMock()
