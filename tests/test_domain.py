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
        rpc.content_get = AsyncMock(
            return_value={
                "history": [{"subject": "Question Subject", "content": "Question Body"}],
                "folders": ["hw1"],
                "default_anonymity": "no",
            }
        )
        rpc.content_update = AsyncMock(return_value={"result": "success"})
        result = await resolve_post(rpc, post_id="post_abc")
        assert result is True
        rpc.content_update.assert_awaited_once_with(
            cid="post_abc",
            subject="Question Subject",
            content="Question Body",
            folders=["hw1"],
            anonymous="no",
            status="resolved",
        )

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
        rpc.content_get = AsyncMock(return_value={})
        rpc.content_update = AsyncMock(side_effect=RuntimeError("backend failure"))
        with pytest.raises(RuntimeError, match="backend failure"):
            await resolve_post(rpc, post_id="post_abc")

    async def test_piazza_sdk_error_passthrough(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(return_value={})
        rpc.content_update = AsyncMock(side_effect=PiazzaSDKError("not found"))
        with pytest.raises(PiazzaSDKError, match="not found"):
            await resolve_post(rpc, post_id="post_abc")
