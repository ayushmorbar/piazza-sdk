"""Tests for domain logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.posts import resolve_post, unresolve_post
from piazza_sdk.exceptions import PiazzaSDKError, ValidationError


class TestResolvePost:
    async def test_happy_path_returns_response(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(
            return_value={
                "history": [{"subject": "Q?", "content": "<p>body</p>"}],
                "folders": ["cs101"],
                "default_anonymity": "no",
            }
        )
        rpc.content_update = AsyncMock(return_value={"result": "success"})
        result = await resolve_post(rpc, post_id="post_abc")
        assert result is True
        rpc.content_get.assert_awaited_once_with("post_abc")
        rpc.content_update.assert_awaited_once_with(
            cid="post_abc",
            subject="Q?",
            content="<p>body</p>",
            folders=["cs101"],
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
        rpc.content_get = AsyncMock(
            return_value={"history": [{"subject": "Q", "content": "x"}], "folders": ["other"]}
        )
        rpc.content_update = AsyncMock(side_effect=RuntimeError("backend failure"))
        with pytest.raises(RuntimeError, match="backend failure"):
            await resolve_post(rpc, post_id="post_abc")

    async def test_piazza_sdk_error_passthrough(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(
            return_value={"history": [{"subject": "Q", "content": "x"}], "folders": ["other"]}
        )
        rpc.content_update = AsyncMock(side_effect=PiazzaSDKError("not found"))
        with pytest.raises(PiazzaSDKError, match="not found"):
            await resolve_post(rpc, post_id="post_abc")

    async def test_empty_history_uses_post_data_fallback(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(
            return_value={
                "subject": "Fallback Subject",
                "content": "Fallback content",
                "folders": ["math"],
            }
        )
        rpc.content_update = AsyncMock(return_value={})
        result = await resolve_post(rpc, post_id="post_xyz")
        assert result is True
        rpc.content_update.assert_awaited_once_with(
            cid="post_xyz",
            subject="Fallback Subject",
            content="Fallback content",
            folders=["math"],
            anonymous="no",
            status="resolved",
        )

    async def test_empty_update_result_returns_true(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(return_value={})
        rpc.content_update = AsyncMock(return_value="not a dict")
        result = await resolve_post(rpc, post_id="post_q")
        assert result is True


class TestUnresolvePost:
    async def test_happy_path_returns_response(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(
            return_value={
                "history": [{"subject": "Q?", "content": "<p>body</p>"}],
                "folders": ["cs101"],
                "default_anonymity": "no",
            }
        )
        rpc.content_update = AsyncMock(return_value={"result": "success"})
        result = await unresolve_post(rpc, post_id="post_abc")
        assert result is True
        rpc.content_get.assert_awaited_once_with("post_abc")
        rpc.content_update.assert_awaited_once_with(
            cid="post_abc",
            subject="Q?",
            content="<p>body</p>",
            folders=["cs101"],
            anonymous="no",
            status="active",
        )

    async def test_empty_post_id_raises_validation_error(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await unresolve_post(rpc, post_id="")

    async def test_whitespace_post_id_raises_validation_error(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await unresolve_post(rpc, post_id="   ")

    async def test_rpc_error_propagates_unwrapped(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(
            return_value={"history": [{"subject": "Q", "content": "x"}], "folders": ["other"]}
        )
        rpc.content_update = AsyncMock(side_effect=RuntimeError("backend failure"))
        with pytest.raises(RuntimeError, match="backend failure"):
            await unresolve_post(rpc, post_id="post_abc")

    async def test_piazza_sdk_error_passthrough(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(
            return_value={"history": [{"subject": "Q", "content": "x"}], "folders": ["other"]}
        )
        rpc.content_update = AsyncMock(side_effect=PiazzaSDKError("not found"))
        with pytest.raises(PiazzaSDKError, match="not found"):
            await unresolve_post(rpc, post_id="post_abc")

    async def test_empty_history_uses_post_data_fallback(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(
            return_value={
                "subject": "Fallback Subject",
                "content": "Fallback content",
                "folders": ["math"],
            }
        )
        rpc.content_update = AsyncMock(return_value={})
        result = await unresolve_post(rpc, post_id="post_xyz")
        assert result is True
        rpc.content_update.assert_awaited_once_with(
            cid="post_xyz",
            subject="Fallback Subject",
            content="Fallback content",
            folders=["math"],
            anonymous="no",
            status="active",
        )

    async def test_empty_update_result_returns_true(self) -> None:
        rpc = _make_rpc()
        rpc.content_get = AsyncMock(return_value={})
        rpc.content_update = AsyncMock(return_value="not a dict")
        result = await unresolve_post(rpc, post_id="post_q")
        assert result is True


def _make_rpc() -> MagicMock:
    """Create a mock RPC client for domain function tests."""
    return MagicMock()
