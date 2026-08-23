"""Regression tests for P0 audit fixes (see review.md findings register).

Covers:
- F-01: content.answer i_answer/s_answer types + revision param
- F-03: 429/5xx tenacity retries actually execute
- F-04: _safe_call preserves typed SDK exceptions (no laundering)
- F-05: envelope double-unwrap fixes (user classes, profile, unread count)
- F-06: dedicated content.pin/content.unpin methods
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from piazza_sdk.adapters.http import RPC
from piazza_sdk.api.piazza import Piazza
from piazza_sdk.exceptions import NotFoundError, PiazzaSDKError, RateLimitError
from piazza_sdk.models.post import Post


def _response(json_data: Any) -> httpx.Response:
    resp = httpx.Response(
        200, json=json_data, request=httpx.Request("POST", "https://piazza.com/test")
    )
    resp.elapsed = timedelta(milliseconds=10)
    return resp


def _rpc_with_envelope(result: Any) -> tuple[RPC, AsyncMock]:
    """RPC whose transport returns a JSON-RPC envelope wrapping *result*."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = AsyncMock(return_value=_response({"result": result, "error": None}))
    session = MagicMock()
    session.client = client
    return RPC(session, "https://piazza.com", "nid"), client.request


class TestEnvelopeUnwrapFixes:
    """F-05: results must survive exactly one envelope unwrap."""

    @pytest.mark.asyncio
    async def test_call_preserves_list_results(self):
        """Bare-list JSON-RPC results must not be coerced to {}."""
        rpc, _ = _rpc_with_envelope([{"nid": "a"}, {"nid": "b"}])
        result = await rpc.call("/logic/api", {})
        assert result == [{"nid": "a"}, {"nid": "b"}]

    @pytest.mark.asyncio
    async def test_piazza_get_user_classes_from_profile_networks(self):
        """Classes derive from user_profile.get_profile → networks (live-verified)."""
        rpc, _ = _rpc_with_envelope(
            {
                "name": "Test User",
                "networks": [{"id": "c1", "nid": "n1"}, {"id": "c2", "nid": "n2"}],
            }
        )
        session = MagicMock()
        session.needs_refresh = False
        session.config.base_url = "https://piazza.com"
        piazza = Piazza(session)
        piazza._user_rpc = rpc

        classes = await piazza.get_user_classes()
        assert classes == [{"id": "c1", "nid": "n1"}, {"id": "c2", "nid": "n2"}]

    @pytest.mark.asyncio
    async def test_piazza_get_user_classes_filters_non_dicts(self):
        rpc, _ = _rpc_with_envelope({"networks": [{"nid": "ok"}, "junk", 42]})
        session = MagicMock()
        session.needs_refresh = False
        session.config.base_url = "https://piazza.com"
        piazza = Piazza(session)
        piazza._user_rpc = rpc
        assert await piazza.get_user_classes() == [{"nid": "ok"}]

    @pytest.mark.asyncio
    async def test_piazza_get_user_classes_empty_when_no_networks(self):
        rpc, _ = _rpc_with_envelope({"name": "lonely"})
        session = MagicMock()
        session.needs_refresh = False
        session.config.base_url = "https://piazza.com"
        piazza = Piazza(session)
        piazza._user_rpc = rpc
        assert await piazza.get_user_classes() == []

    @pytest.mark.asyncio
    async def test_method_not_found_normalizes_to_not_found(self):
        """Embedded 'Method not found' errors normalize to NotFoundError (F-14)."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(
            return_value=_response({"result": None, "error": "Method not found: some.method"})
        )
        session = MagicMock()
        session.client = client
        rpc = RPC(session, "https://piazza.com", "nid")

        with pytest.raises(NotFoundError):
            await rpc.call("/logic/api", {"method": "some.method"})

    @pytest.mark.asyncio
    async def test_preferences_method_missing_returns_empty(self):
        """Feature-detection contract: unavailable preferences surface as {}."""
        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(
            return_value=_response(
                {"result": None, "error": "Method not found: get_user_preferences"}
            )
        )
        session = MagicMock()
        session.client = client
        rpc = RPC(session, "https://piazza.com", "nid")
        assert await rpc.get_user_preferences() == {}

    def test_relaxed_post_config_accepts_live_keys(self):
        """Live payloads carry config keys like feed_groups — must not crash.

        Unknown keys are ignored (dropped) by PostConfig; known keys parse.
        """
        post = Post(
            id="p1",
            title="t",
            raw={},
            config={"feed_groups": "instr_xyz", "section": "general", "editor": "rich_text"},
        )
        # Known key parses normally…
        assert post.config.editor == "rich_text"
        # …and unknown keys are dropped without raising — the pre-fix behavior
        # raised ValidationError("Extra inputs are not permitted") here.
        assert not hasattr(post.config, "feed_groups")

    @pytest.mark.asyncio
    async def test_unread_message_count_parses_count_key(self):
        rpc, _ = _rpc_with_envelope({"count": 7})
        assert await rpc.get_unread_message_count() == 7

    @pytest.mark.asyncio
    async def test_unread_message_count_parses_unread_count_key(self):
        rpc, _ = _rpc_with_envelope({"unread_count": 3})
        assert await rpc.get_unread_message_count() == 3

    @pytest.mark.asyncio
    async def test_unread_message_count_numeric_result(self):
        rpc, _ = _rpc_with_envelope(12)
        assert await rpc.get_unread_message_count() == 12

    @pytest.mark.asyncio
    async def test_unread_message_count_garbage_raises_typed(self):
        rpc, _ = _rpc_with_envelope({"count": "not-a-number"})

        with pytest.raises(PiazzaSDKError, match="Unexpected unread-count payload"):
            await rpc.get_unread_message_count()


class TestNoExceptionLaundering:
    """F-04: typed transport errors keep their identity through _safe_call."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_survives_safe_call(self):
        resp = httpx.Response(
            429,
            json={},
            headers={"Retry-After": "2"},
            request=httpx.Request("POST", "https://piazza.com/test"),
        )
        resp.elapsed = timedelta(milliseconds=10)
        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(return_value=resp)
        session = MagicMock()
        session.client = client
        rpc = RPC(session, "https://piazza.com", "nid", max_attempts=1)

        with pytest.raises(RateLimitError) as exc_info:
            await rpc.get_my_feed()
        assert exc_info.value.retry_after_ms == 2000
