"""Tests for domain functions: statistics, search, and posts."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.posts import resolve_post
from piazza_sdk.domain.search import search
from piazza_sdk.domain.statistics import get_statistics
from piazza_sdk.exceptions import PiazzaSDKError, ValidationError
from piazza_sdk.models.feed import Feed
from piazza_sdk.models.network import Statistics


def _make_rpc() -> MagicMock:
    """Create a mock RPC client for domain function tests."""
    return MagicMock()


# --- get_statistics ---


class TestGetStatistics:
    async def test_happy_path_returns_statistics(self) -> None:
        rpc = _make_rpc()
        rpc.get_stats = AsyncMock(
            return_value={
                "posts": 150,
                "resolved": 80,
                "unresolved": 70,
                "users": 200,
                "instructors": 5,
                "students": 195,
                "total_views": 10000,
                "total_endorsements": 300,
            }
        )
        result = await get_statistics(rpc)
        assert isinstance(result, Statistics)
        assert result.posts == 150
        assert result.resolved == 80
        assert result.unresolved == 70
        assert result.users == 200
        assert result.instructors == 5
        assert result.students == 195
        assert result.total_views == 10000
        assert result.total_endorsements == 300
        rpc.get_stats.assert_awaited_once()

    async def test_happy_path_missing_keys_use_defaults(self) -> None:
        rpc = _make_rpc()
        rpc.get_stats = AsyncMock(return_value={})
        result = await get_statistics(rpc)
        assert isinstance(result, Statistics)
        assert result.posts == 0
        assert result.resolved == 0
        assert result.users == 0

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


class TestResolvePost:
    async def test_happy_path_returns_response(self) -> None:
        rpc = _make_rpc()
        rpc.content_update = AsyncMock(return_value={"result": "success"})
        result = await resolve_post(rpc, post_id="post_abc")
        assert result is True
        rpc.content_update.assert_awaited_once_with(cid="post_abc", status="resolved")

    async def test_empty_post_id_raises_validation_error(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await resolve_post(rpc, post_id="")

    async def test_whitespace_post_id_raises_validation_error(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await resolve_post(rpc, post_id="   ")

    async def test_rpc_error_propagates_unwrapped(self) -> None:
        rpc = _make_rpc()
        rpc.content_update = AsyncMock(side_effect=RuntimeError("backend failure"))
        with pytest.raises(RuntimeError, match="backend failure"):
            await resolve_post(rpc, post_id="post_abc")

    async def test_piazza_sdk_error_passthrough(self) -> None:
        rpc = _make_rpc()
        rpc.content_update = AsyncMock(side_effect=PiazzaSDKError("not found"))
        with pytest.raises(PiazzaSDKError, match="not found"):
            await resolve_post(rpc, post_id="post_abc")
