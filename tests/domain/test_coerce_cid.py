"""Tests for polymorphic cid support (P4).

Validates that ``_coerce_cid`` correctly normalises str, int, and Post
arguments, and that domain functions (add_followup, create_reply,
resolve_post, unresolve_post) forward the coerced string to the RPC layer.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.posts import (
    _coerce_cid,
    add_followup,
    create_reply,
    resolve_post,
    unresolve_post,
)
from piazza_sdk.exceptions import ValidationError
from piazza_sdk.models.post import Post

# ── _coerce_cid unit tests ──────────────────────────────────────────────


class TestCoerceCid:
    """Unit tests for the _coerce_cid normalisation helper."""

    def test_str_passthrough(self) -> None:
        assert _coerce_cid("j5yj4g5d4p2qg3") == "j5yj4g5d4p2qg3"

    def test_int_to_str(self) -> None:
        assert _coerce_cid(42) == "42"

    def test_int_zero(self) -> None:
        assert _coerce_cid(0) == "0"

    def test_int_negative(self) -> None:
        assert _coerce_cid(-1) == "-1"

    def test_post_model_extracts_id(self) -> None:
        post = Post(id="abc123")
        assert _coerce_cid(post) == "abc123"

    def test_post_model_with_long_id(self) -> None:
        post = Post(id="j5yj4g5d4p2qg3")
        assert _coerce_cid(post) == "j5yj4g5d4p2qg3"

    def test_bool_rejected(self) -> None:
        with pytest.raises(TypeError, match="cid must be str, int, or Post, got bool"):
            _coerce_cid(True)  # type: ignore[arg-type]

    def test_none_rejected(self) -> None:
        with pytest.raises(TypeError, match="cid must be str, int, or Post, got NoneType"):
            _coerce_cid(None)  # type: ignore[arg-type]

    def test_dict_rejected(self) -> None:
        with pytest.raises(TypeError, match="cid must be str, int, or Post, got dict"):
            _coerce_cid({"id": "x"})  # type: ignore[arg-type]

    def test_list_rejected(self) -> None:
        with pytest.raises(TypeError, match="cid must be str, int, or Post, got list"):
            _coerce_cid(["abc"])  # type: ignore[arg-type]


# ── Domain function polymorphic cid integration tests ────────────────────


def _make_rpc() -> MagicMock:
    """Create a mock RPC client for domain function tests."""
    return MagicMock()


class TestAddFollowupPolymorphic:
    """Verify add_followup forwards coerced cid for each accepted type."""

    async def test_str_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_create = AsyncMock(return_value={"result": {"id": "fu1"}})
        await add_followup(rpc, post_id="parent_1", content="hello")
        rpc.content_create.assert_awaited_once()
        assert rpc.content_create.call_args.kwargs["cid"] == "parent_1"

    async def test_int_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_create = AsyncMock(return_value={"result": {"id": "fu2"}})
        await add_followup(rpc, post_id=99, content="hello")
        assert rpc.content_create.call_args.kwargs["cid"] == "99"

    async def test_post_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_create = AsyncMock(return_value={"result": {"id": "fu3"}})
        post = Post(id="post_xyz")
        await add_followup(rpc, post_id=post, content="hello")
        assert rpc.content_create.call_args.kwargs["cid"] == "post_xyz"


class TestCreateReplyPolymorphic:
    """Verify create_reply forwards coerced cid for each accepted type."""

    async def test_str_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_create = AsyncMock(return_value={"result": {"id": "r1"}})
        await create_reply(rpc, post_id="followup_1", content="reply")
        assert rpc.content_create.call_args.kwargs["cid"] == "followup_1"

    async def test_int_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_create = AsyncMock(return_value={"result": {"id": "r2"}})
        await create_reply(rpc, post_id=7, content="reply")
        assert rpc.content_create.call_args.kwargs["cid"] == "7"

    async def test_post_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_create = AsyncMock(return_value={"result": {"id": "r3"}})
        post = Post(id="followup_abc")
        await create_reply(rpc, post_id=post, content="reply")
        assert rpc.content_create.call_args.kwargs["cid"] == "followup_abc"


class TestResolvePostPolymorphic:
    """Verify resolve_post forwards coerced cid for each accepted type."""

    async def test_str_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_mark_resolved = AsyncMock(return_value={"result": "success"})
        result = await resolve_post(rpc, post_id="post_abc")
        assert result is True
        rpc.content_mark_resolved.assert_awaited_once_with("post_abc", resolved=True)

    async def test_int_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_mark_resolved = AsyncMock(return_value={"result": "success"})
        result = await resolve_post(rpc, post_id=123)
        assert result is True
        rpc.content_mark_resolved.assert_awaited_once_with("123", resolved=True)

    async def test_post_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_mark_resolved = AsyncMock(return_value={"result": "success"})
        post = Post(id="post_xyz")
        result = await resolve_post(rpc, post_id=post)
        assert result is True
        rpc.content_mark_resolved.assert_awaited_once_with("post_xyz", resolved=True)

    async def test_empty_str_post_id_raises(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await resolve_post(rpc, post_id="")

    async def test_whitespace_str_post_id_raises(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await resolve_post(rpc, post_id="   ")


class TestUnresolvePostPolymorphic:
    """Verify unresolve_post forwards coerced cid for each accepted type."""

    async def test_str_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_mark_resolved = AsyncMock(return_value={"result": "success"})
        result = await unresolve_post(rpc, post_id="post_abc")
        assert result is True
        rpc.content_mark_resolved.assert_awaited_once_with("post_abc", resolved=False)

    async def test_int_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_mark_resolved = AsyncMock(return_value={"result": "success"})
        result = await unresolve_post(rpc, post_id=456)
        assert result is True
        rpc.content_mark_resolved.assert_awaited_once_with("456", resolved=False)

    async def test_post_cid(self) -> None:
        rpc = _make_rpc()
        rpc.content_mark_resolved = AsyncMock(return_value={"result": "success"})
        post = Post(id="post_xyz")
        result = await unresolve_post(rpc, post_id=post)
        assert result is True
        rpc.content_mark_resolved.assert_awaited_once_with("post_xyz", resolved=False)

    async def test_empty_str_post_id_raises(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await unresolve_post(rpc, post_id="")

    async def test_whitespace_str_post_id_raises(self) -> None:
        rpc = _make_rpc()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await unresolve_post(rpc, post_id="   ")
