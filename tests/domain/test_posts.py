"""Tests for domain logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.posts import resolve_post
from piazza_sdk.exceptions import PiazzaSDKError, ValidationError


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


def _make_rpc() -> MagicMock:
    """Create a mock RPC client for domain function tests."""
    return MagicMock()
