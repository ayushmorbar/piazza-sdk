"""Tests for domain logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.search import search
from piazza_sdk.exceptions import PiazzaSDKError, ValidationError
from piazza_sdk.models.feed import Feed


class TestSearch:
    async def test_happy_path_returns_feed(self) -> None:
        rpc = _make_rpc()
        rpc.search = AsyncMock(
            return_value={
                "feed": [
                    {"id": "post_1", "subject": "How to solve integrals?"},
                    {"id": "post_2", "subject": "Derivative rules"},
                ],
                "total": 2,
            }
        )
        result = await search(rpc, query="calculus")
        assert isinstance(result, Feed)
        assert len(result.feed) == 2
        assert result.total == 2
        assert result.feed[0].id == "post_1"
        assert result.feed[0].subject == "How to solve integrals?"
        assert result.feed[1].id == "post_2"
        rpc.search.assert_awaited_once_with("calculus")

    async def test_happy_path_passes_kwargs(self) -> None:
        rpc = _make_rpc()
        rpc.search = AsyncMock(return_value={"feed": [], "total": 0})
        await search(rpc, query="test", limit=10, sort="date")
        rpc.search.assert_awaited_once_with("test", limit=10, sort="date")

    async def test_empty_query_raises_validation_error(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="query must be non-empty"):
            await search(rpc, query="")

    async def test_whitespace_query_raises_validation_error(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="query must be non-empty"):
            await search(rpc, query="   ")

    async def test_empty_results_returns_empty_feed(self) -> None:
        rpc = _make_rpc()
        rpc.search = AsyncMock(return_value={"feed": [], "total": 0})
        result = await search(rpc, query="nonexistent")
        assert isinstance(result, Feed)
        assert result.feed == []
        assert result.total == 0

    async def test_missing_feed_key_returns_empty_feed(self) -> None:
        rpc = _make_rpc()
        rpc.search = AsyncMock(return_value={"total": 0})
        result = await search(rpc, query="query")
        assert isinstance(result, Feed)
        assert result.feed == []

    async def test_rpc_error_wraps_in_piazza_sdk_error(self) -> None:
        rpc = _make_rpc()
        rpc.search = AsyncMock(side_effect=RuntimeError("timeout"))
        with pytest.raises(PiazzaSDKError, match="Failed to search"):
            await search(rpc, query="test")

    async def test_piazza_sdk_error_passthrough(self) -> None:
        rpc = _make_rpc()
        rpc.search = AsyncMock(side_effect=PiazzaSDKError("network error"))
        with pytest.raises(PiazzaSDKError, match="network error"):
            await search(rpc, query="test")


# --- resolve_post ---


def _make_rpc() -> MagicMock:
    """Create a mock RPC client for domain function tests."""
    return MagicMock()
