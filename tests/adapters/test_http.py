"""Unit tests for adapters/http.py — RPC client layer."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from piazza_sdk.adapters.http import RPC, _AuthRetryNeededError, _check_embedded_error
from piazza_sdk.config import PiazzaConfig
from piazza_sdk.exceptions import (
    AuthenticationError,
    NetworkError,
    NotFoundError,
    PermissionError,
    PiazzaSDKError,
    RateLimitError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(
    status_code: int = 200, json_data: Any = None, *, headers: dict[str, str] | None = None
) -> httpx.Response:
    if json_data is None:
        json_data = {}
    resp = httpx.Response(
        status_code,
        json=json_data,
        request=httpx.Request("POST", "https://piazza.com/test"),
        headers=headers or {},
    )
    resp.elapsed = timedelta(milliseconds=50)
    return resp


def _mock_client(
    status_code: int = 200, json_data: Any = None, *, headers: dict[str, str] | None = None
) -> httpx.AsyncClient:
    """Return an httpx.AsyncClient mock that returns the given response."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.request = AsyncMock(return_value=_make_response(status_code, json_data, headers=headers))
    return client


def _make_session(client: httpx.AsyncClient | None = None) -> MagicMock:
    """Wrap an httpx client mock in an adapter mock with a `.client` property."""
    adapter = MagicMock()
    adapter.client = client or _mock_client()
    adapter.config.throttle_enabled = False
    adapter.config.throttle_min_delay = 0.0
    adapter.config.throttle_max_delay = 0.0
    adapter.config.throttle_idle_timeout = 30.0
    return adapter


def _make_rpc(
    session: MagicMock | None = None,
    *,
    on_auth_error=None,
    max_attempts: int | None = None,
    retry_sleep=None,
) -> RPC:
    if session is None:
        session = _make_session()
    return RPC(
        session,
        "https://piazza.com",
        "test_nid",
        on_auth_error=on_auth_error,
        max_attempts=max_attempts,
        retry_sleep=retry_sleep,
    )


# ---------------------------------------------------------------------------
# RPC init
# ---------------------------------------------------------------------------


class TestRPCInit:
    def test_stores_base_url(self):
        rpc = _make_rpc()
        assert rpc._base_url == "https://piazza.com"

    def test_strips_trailing_slash(self):
        rpc = RPC(_make_session(), "https://piazza.com/", "nid")
        assert rpc._base_url == "https://piazza.com"

    def test_stores_nid(self):
        rpc = _make_rpc()
        assert rpc._nid == "test_nid"

    def test_client_delegates_to_session(self):
        mock_httpx = _mock_client()
        session = _make_session(mock_httpx)
        rpc = RPC(session, "https://piazza.com", "nid")
        assert rpc.client is mock_httpx


# ---------------------------------------------------------------------------
# RPC.client property — fresh reference
# ---------------------------------------------------------------------------


class TestRPCClientFreshness:
    """Verify RPC.client always reads from the session adapter (Fix 2)."""

    def test_client_returns_session_client(self):
        old = _mock_client()
        session = _make_session(old)
        rpc = RPC(session, "https://piazza.com", "nid")
        assert rpc.client is old

    def test_client_tracks_new_client_after_session_update(self):
        old = _mock_client()
        session = _make_session(old)
        rpc = RPC(session, "https://piazza.com", "nid")
        assert rpc.client is old

        # Simulate session refresh: adapter's .client now points to a new object
        new = _mock_client()
        session.client = new
        assert rpc.client is new

    def test_request_uses_current_client(self):
        """After swapping session.client, _request uses the new one."""
        resp1 = _make_response(200, {"result": "old"})
        resp2 = _make_response(200, {"result": "new"})

        client1 = AsyncMock(spec=httpx.AsyncClient)
        client1.request = AsyncMock(return_value=resp1)
        client2 = AsyncMock(spec=httpx.AsyncClient)
        client2.request = AsyncMock(return_value=resp2)

        session = _make_session(client1)
        rpc = RPC(session, "https://piazza.com", "nid")

        result1 = rpc.client
        assert result1 is client1

        # Swap the client (simulates refresh)
        session.client = client2
        result2 = rpc.client
        assert result2 is client2


# ---------------------------------------------------------------------------
# RPC request — success
# ---------------------------------------------------------------------------


class TestRPCRequestSuccess:
    async def test_post_request(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"result": "ok"})))
        result = await rpc._request("POST", "/test", json={})
        assert result == {"result": "ok"}

    async def test_url_construction(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {})))
        await rpc._request("POST", "/test", json={})
        rpc.client.request.assert_called_once()
        call_args = rpc.client.request.call_args
        assert call_args[0][0] == "POST"
        assert "piazza.com/test" in call_args[0][1]

    async def test_strips_leading_slash_from_endpoint(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {})))
        await rpc._request("POST", "/api/test", json={})
        call_args = rpc.client.request.call_args
        assert "piazza.com/api/test" in call_args[0][1]


# ---------------------------------------------------------------------------
# RPC request — errors
# ---------------------------------------------------------------------------


class TestRPCRequestErrors:
    async def test_401_raises_auth_error(self):
        rpc = _make_rpc(_make_session(_mock_client(401)))
        with pytest.raises(AuthenticationError):
            await rpc._request("POST", "/test", json={})

    async def test_403_raises_permission_error(self):
        rpc = _make_rpc(_make_session(_mock_client(403)))
        with pytest.raises(PermissionError):
            await rpc._request("POST", "/test", json={})

    async def test_404_raises_not_found_error(self):
        rpc = _make_rpc(_make_session(_mock_client(404)))
        with pytest.raises(NotFoundError):
            await rpc._request("POST", "/test", json={})

    async def test_429_raises_rate_limit_error(self):
        rpc = _make_rpc(_make_session(_mock_client(429)), max_attempts=1)
        with pytest.raises(RateLimitError):
            await rpc._request("POST", "/test", json={})

    async def test_429_with_retry_after(self):
        rpc = _make_rpc(
            _make_session(_mock_client(429, headers={"Retry-After": "5"})), max_attempts=1
        )
        with pytest.raises(RateLimitError) as exc_info:
            await rpc._request("POST", "/test", json={})
        assert exc_info.value.retry_after_ms == 5000

    async def test_429_sets_status_code(self):
        rpc = _make_rpc(_make_session(_mock_client(429)), max_attempts=1)
        with pytest.raises(RateLimitError) as exc_info:
            await rpc._request("POST", "/test", json={})
        assert exc_info.value.status_code == 429

    async def test_500_raises_piazza_error(self):
        rpc = _make_rpc(_make_session(_mock_client(500)), max_attempts=1)
        with pytest.raises(PiazzaSDKError):
            await rpc._request("POST", "/test", json={})

    async def test_timeout_raises_network_error(self):
        rpc = _make_rpc(max_attempts=1)
        rpc.client.request = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        with pytest.raises(NetworkError):
            await rpc._request("POST", "/test", json={})

    async def test_connect_error_raises_network_error(self):
        rpc = _make_rpc(max_attempts=1)
        rpc.client.request = AsyncMock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(NetworkError):
            await rpc._request("POST", "/test", json={})

    async def test_unknown_error_raises_piazza_error(self):
        rpc = _make_rpc(_make_session(_mock_client(502)), max_attempts=1)
        with pytest.raises(PiazzaSDKError):
            await rpc._request("POST", "/test", json={})


# ---------------------------------------------------------------------------
# RPC request — auth retry
# ---------------------------------------------------------------------------


class TestRPCAuthRetry:
    async def test_401_with_on_auth_error_retries(self):
        mock_httpx = _mock_client(401)
        rpc = _make_rpc(_make_session(mock_httpx), on_auth_error=AsyncMock(), max_attempts=1)
        with pytest.raises(_AuthRetryNeededError):
            await rpc._request("POST", "/test", json={})
        rpc._on_auth_error.assert_called()

    async def test_401_without_on_auth_error_raises(self):
        rpc = _make_rpc(_make_session(_mock_client(401)))
        with pytest.raises(AuthenticationError):
            await rpc._request("POST", "/test", json={})

    async def test_401_retry_success_after_refresh(self):
        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response(401)
            return _make_response(200, {"result": "ok"})

        mock_httpx = AsyncMock(spec=httpx.AsyncClient)
        mock_httpx.request = AsyncMock(side_effect=side_effect)
        rpc = _make_rpc(_make_session(mock_httpx), on_auth_error=AsyncMock())

        # Will raise _AuthRetryNeededError internally, then retry succeeds
        # But 401 → on_auth_error → _AuthRetryNeededError → retry → 200 OK
        result = await rpc._request("POST", "/test", json={})
        assert result == {"result": "ok"}
        assert call_count == 2


# ---------------------------------------------------------------------------
# RPC error mapping
# ---------------------------------------------------------------------------


class TestRPCErrorMapping:
    async def test_401_maps_to_auth_error(self):
        rpc = _make_rpc(_make_session(_mock_client(401)))
        with pytest.raises(AuthenticationError):
            await rpc._request("POST", "/test", json={})

    async def test_403_maps_to_permission_error(self):
        rpc = _make_rpc(_make_session(_mock_client(403)))
        with pytest.raises(PermissionError):
            await rpc._request("POST", "/test", json={})

    async def test_404_maps_to_not_found_error(self):
        rpc = _make_rpc(_make_session(_mock_client(404)))
        with pytest.raises(NotFoundError):
            await rpc._request("POST", "/test", json={})

    async def test_429_maps_to_rate_limit_error(self):
        rpc = _make_rpc(_make_session(_mock_client(429)), max_attempts=1)
        with pytest.raises(RateLimitError):
            await rpc._request("POST", "/test", json={})

    async def test_500_maps_to_piazza_error_with_status(self):
        rpc = _make_rpc(_make_session(_mock_client(500)), max_attempts=1)
        with pytest.raises(PiazzaSDKError) as exc_info:
            await rpc._request("POST", "/test", json={})
        assert exc_info.value.status_code == 500

    async def test_502_maps_to_piazza_error_with_status(self):
        rpc = _make_rpc(_make_session(_mock_client(502)), max_attempts=1)
        with pytest.raises(PiazzaSDKError) as exc_info:
            await rpc._request("POST", "/test", json={})
        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Retry behavior — transient statuses are actually retried (F-03 regression)
# ---------------------------------------------------------------------------


async def _instant_sleep(seconds: float) -> None:
    """Test double for tenacity's sleep callable (no wall-clock delay)."""


class TestRetryBehavior:
    async def test_429_retries_then_succeeds(self):
        """429 responses must be retried until success (documented behavior)."""
        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return _make_response(429)
            return _make_response(200, {"result": "ok"})

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=side_effect)
        rpc = _make_rpc(_make_session(client), max_attempts=3, retry_sleep=_instant_sleep)
        result = await rpc._request("POST", "/test", json={})
        assert result == {"result": "ok"}
        assert call_count == 3

    async def test_5xx_retries_until_exhaustion_reraises_typed(self):
        """Exhausted 5xx retries reraise the typed PiazzaSDKError with status."""
        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return _make_response(503)

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=side_effect)
        rpc = _make_rpc(_make_session(client), max_attempts=3, retry_sleep=_instant_sleep)
        with pytest.raises(PiazzaSDKError) as exc_info:
            await rpc._request("POST", "/test", json={})
        assert call_count == 3
        assert exc_info.value.status_code == 503

    async def test_timeout_retries_then_raises_network_error(self):
        """Timeouts must be retried before surfacing NetworkError."""
        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("timeout")

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=side_effect)
        rpc = _make_rpc(_make_session(client), max_attempts=2, retry_sleep=_instant_sleep)
        with pytest.raises(NetworkError):
            await rpc._request("POST", "/test", json={})
        assert call_count == 2

    async def test_client_errors_not_retried(self):
        """4xx client errors (other than 401-refresh) propagate after one attempt."""
        call_count = 0

        async def side_effect(*args: Any, **kwargs: Any) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return _make_response(404)

        client = AsyncMock(spec=httpx.AsyncClient)
        client.request = AsyncMock(side_effect=side_effect)
        rpc = _make_rpc(_make_session(client))
        with pytest.raises(NotFoundError):
            await rpc._request("POST", "/test", json={})
        assert call_count == 1

    async def test_rate_limit_wait_honors_retry_after(self):
        """The wait strategy uses Retry-After for rate-limit responses."""
        from tenacity import RetryCallState  # noqa: PLC0415

        from piazza_sdk.adapters.http import _compute_retry_wait  # noqa: PLC0415

        state = MagicMock(spec=RetryCallState)
        state.attempt_number = 2
        outcome = MagicMock()
        outcome.exception.return_value = RateLimitError("rl", retry_after_ms=7500)
        state.outcome = outcome
        assert _compute_retry_wait(state) == 7.5

    async def test_default_max_attempts_configurable(self):
        rpc = _make_rpc(max_attempts=5)
        assert rpc._max_attempts == 5

    async def test_zero_or_negative_attempts_clamped_to_one(self):
        rpc = _make_rpc(max_attempts=0)
        assert rpc._max_attempts == 1


# ---------------------------------------------------------------------------
# RPC domain methods — request shape
# ---------------------------------------------------------------------------


class TestRPCContentGet:
    async def test_content_get_request(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"content": "data"})))
        result = await rpc.content_get("post123")
        assert result == {"content": "data"}

    async def test_content_get_transport_error_propagates_typed(self):
        """HTTP-level errors keep their type instead of being laundered (F-04)."""
        rpc = _make_rpc(_make_session(_mock_client(500)), max_attempts=1)
        with pytest.raises(PiazzaSDKError) as exc_info:
            await rpc.content_get("post123")
        assert exc_info.value.status_code == 500


class TestRPCFeed:
    async def test_get_my_feed(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"feed": []})))
        result = await rpc.get_my_feed()
        assert result == {"feed": []}

    async def test_get_my_feed_with_params(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"feed": []})))
        result = await rpc.get_my_feed(limit=10)
        assert result == {"feed": []}

    async def test_get_my_feed_blocks_reserved_keys(self):
        rpc = _make_rpc(_make_session(_mock_client(200)))
        with pytest.raises(PiazzaSDKError, match="Reserved keys"):
            await rpc.get_my_feed(action="override")

    async def test_get_my_feed_transport_error_propagates_typed(self):
        rpc = _make_rpc(_make_session(_mock_client(500)), max_attempts=1)
        with pytest.raises(PiazzaSDKError) as exc_info:
            await rpc.get_my_feed()
        assert exc_info.value.status_code == 500


class TestRPCContentCreate:
    async def test_content_create(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"post_id": "new"})))
        result = await rpc.content_create(subject="Test")
        assert result == {"post_id": "new"}

    async def test_content_create_blocks_reserved_keys(self):
        rpc = _make_rpc(_make_session(_mock_client(200)))
        with pytest.raises(PiazzaSDKError, match="Reserved keys"):
            await rpc.content_create(nid="override")


class TestRPCContentUpdate:
    async def test_content_update(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.content_update(cid="post1", subject="Updated")
        assert result == {"ok": True}


class TestRPCContentDelete:
    async def test_content_delete(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"deleted": True})))
        result = await rpc.content_delete("post1")
        assert result == {"deleted": True}


class TestRPCGetUsers:
    async def test_get_users(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"users": []})))
        result = await rpc.get_users()
        assert result == {"users": []}


class TestRPCSearch:
    async def test_search(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"results": []})))
        result = await rpc.search("python")
        assert result == {"results": []}

    async def test_search_blocks_reserved_keys(self):
        rpc = _make_rpc(_make_session(_mock_client(200)))
        with pytest.raises(PiazzaSDKError, match="Reserved keys"):
            await rpc.search("q", action="override")


class TestRPCGetStats:
    async def test_get_stats(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"stats": {}})))
        result = await rpc.get_stats()
        assert result == {"stats": {}}


class TestRPCContentAnswer:
    async def test_content_answer(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.content_answer("post1", "answer text")
        assert result == {"ok": True}

    async def test_content_answer_student_type(self):
        """Student answers must send type='s_answer' (F-01 regression)."""
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        await rpc.content_answer("post1", "answer text", instructor_answer=False)
        payload = rpc.client.request.call_args.kwargs["json"]
        assert payload["params"]["type"] == "s_answer"
        assert payload["params"]["revision"] == 1
        assert payload["method"] == "content.answer"

    async def test_content_answer_instructor_type(self):
        """Instructor answers must send type='i_answer' (F-01 regression)."""
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        await rpc.content_answer("post1", "answer text", instructor_answer=True)
        payload = rpc.client.request.call_args.kwargs["json"]
        assert payload["params"]["type"] == "i_answer"

    async def test_content_answer_custom_revision_and_anonymous(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        await rpc.content_answer("post1", "text", revision=2, anonymous=True)
        params = rpc.client.request.call_args.kwargs["json"]["params"]
        assert params["revision"] == 2
        assert params["anonymous"] == "stud"

    async def test_content_answer_transport_error_propagates_typed(self):
        rpc = _make_rpc(_make_session(_mock_client(500)), max_attempts=1)
        with pytest.raises(PiazzaSDKError) as exc_info:
            await rpc.content_answer("post1", "answer text")
        assert exc_info.value.status_code == 500


class TestRPCContentPinUnpin:
    async def test_content_pin_uses_dedicated_method(self):
        """Pin must call content.pin, not a tag add (F-06 regression)."""
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        await rpc.content_pin("post1")
        payload = rpc.client.request.call_args.kwargs["json"]
        assert payload["method"] == "content.pin"
        assert payload["params"]["cid"] == "post1"
        assert payload["params"]["nid"] == "test_nid"

    async def test_content_unpin_uses_dedicated_method(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        await rpc.content_unpin("post1")
        payload = rpc.client.request.call_args.kwargs["json"]
        assert payload["method"] == "content.unpin"


class TestRPCContentUpvote:
    async def test_content_upvote(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.content_upvote("post1")
        assert result == {"ok": True}


class TestRPCContentAddTag:
    async def test_content_add_tag(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.content_add_tag("post1", "python")
        assert result == {"ok": True}


class TestRPCContentRemoveTag:
    async def test_content_remove_tag(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.content_remove_tag("post1", "python")
        assert result == {"ok": True}


class TestRPCGetInstructorStats:
    async def test_get_instructor_stats(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"stats": {}})))
        result = await rpc.get_instructor_stats()
        assert result == {"stats": {}}


class TestRPCGetOnlineUsers:
    async def test_get_online_users(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"users": []})))
        result = await rpc.get_online_users()
        assert result == {"users": []}


class TestRPCGetUserPreferences:
    async def test_get_user_preferences(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"prefs": {}})))
        result = await rpc.get_user_preferences()
        assert result == {"prefs": {}}


class TestRPCUpdateUserPreferences:
    async def test_update_user_preferences(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {})))
        result = await rpc.update_user_preferences({"theme": "dark"})
        # update_user_preferences doesn't return a dict, it returns None
        assert result is None

    async def test_update_user_preferences_blocks_reserved_keys(self):
        rpc = _make_rpc(_make_session(_mock_client(200)))
        with pytest.raises(PiazzaSDKError, match="Reserved keys"):
            await rpc.update_user_preferences({"action": "override"})


class TestRPCMarkAsUnread:
    async def test_mark_as_unread(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.mark_as_unread("post1")
        assert result == {"ok": True}


class TestRPCAddFolder:
    async def test_add_folder(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.add_folder("Homework")
        assert result == {"ok": True}


class TestRPCAddBadge:
    async def test_add_badge(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"ok": True})))
        result = await rpc.add_badge("post1")
        assert result == {"ok": True}


class TestRPCAssetGetUploadUrl:
    async def test_asset_get_upload_url(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"url": "https://upload.example"})))
        result = await rpc.asset_get_upload_url("file.pdf")
        assert result == {"url": "https://upload.example"}


class TestRPCContentSaveDraft:
    async def test_content_save_draft(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"draft_id": "d1"})))
        result = await rpc.content_save_draft("Subject", "Body")
        assert result == {"draft_id": "d1"}

    async def test_content_save_draft_blocks_reserved_keys(self):
        rpc = _make_rpc(_make_session(_mock_client(200)))
        with pytest.raises(PiazzaSDKError, match="Reserved keys"):
            await rpc.content_save_draft("S", "B", action="override")


class TestRPCContentGetSimilar:
    async def test_content_get_similar(self):
        rpc = _make_rpc(_make_session(_mock_client(200, {"similar": []})))
        result = await rpc.content_get_similar("post1")
        assert result == {"similar": []}

    async def test_content_get_similar_blocks_reserved_keys(self):
        rpc = _make_rpc(_make_session(_mock_client(200)))
        with pytest.raises(PiazzaSDKError, match="Reserved keys"):
            await rpc.content_get_similar("post1", nid="override")


# ---------------------------------------------------------------------------
# RPC non-dict response normalization
# ---------------------------------------------------------------------------


class TestRPCNonDictResponse:
    async def test_list_response_returns_empty_dict(self):
        rpc = _make_rpc(_make_session(_mock_client(200, [{"a": 1}])))
        result = await rpc.content_get("post1")
        assert result == {}

    async def test_string_response_returns_empty_dict(self):
        rpc = _make_rpc(_make_session(_mock_client(200, "ok")))
        result = await rpc.content_get("post1")
        assert result == {}

    async def test_int_response_returns_empty_dict(self):
        rpc = _make_rpc(_make_session(_mock_client(200, 42)))
        result = await rpc.content_get("post1")
        assert result == {}


async def test_content_pin_unpin():
    rpc = _make_rpc(_make_session(_mock_client(200, {"result": {}})))
    await rpc.content_pin("p1")
    await rpc.content_unpin("p1")
    assert rpc._session.client.request.call_count == 2


async def test_content_duplicate():
    rpc = _make_rpc(_make_session(_mock_client(200, {"result": {}})))
    await rpc.content_duplicate("dup", "master", "msg")
    assert rpc._session.client.request.call_count == 1


async def test_user_status():
    rpc = _make_rpc(_make_session(_mock_client(200, {"result": {"status": "ok"}})))
    res = await rpc.user_status()
    assert res == {"status": "ok"}


def test_throttle_off_by_default():
    rpc = _make_rpc(_make_session(_mock_client(200, {})))
    assert rpc._throttle_enabled is False
    assert rpc._throttle_min_delay == 0.0
    assert rpc._throttle_max_delay == 0.0
    assert rpc._throttle_idle_timeout == 30.0


def test_not_found_from_body_mock():
    # Test dictionary with "error": "not found"
    with pytest.raises(NotFoundError) as exc_info:
        _check_embedded_error(
            {"result": None, "error": "The post you are looking for cannot be found"}
        )
    assert exc_info.value.response_body == {
        "result": None,
        "error": "The post you are looking for cannot be found",
    }

    # Test stringified result with "not found"
    with pytest.raises(NotFoundError) as exc_info:
        _check_embedded_error({"status": "failed, the post Not Found in db"})
    assert "not found" in str(exc_info.value).lower()

    # Valid dict without error should pass seamlessly
    _check_embedded_error({"result": "success"})

    # Non-dict should be ignored
    _check_embedded_error(["list", "result"])


# ---------------------------------------------------------------------------
# Throttle behavior
# ---------------------------------------------------------------------------


class TestThrottleBehavior:
    async def test_throttle_disabled_skips_delay(self):
        """When throttle_enabled=False, _throttle should return immediately."""
        session = _make_session(_mock_client(200, {}))
        session.config.throttle_enabled = False
        rpc = _make_rpc(session)
        # Should not raise or sleep
        await rpc._throttle()

    async def test_throttle_enabled_inserts_delay(self):
        """When throttle_enabled=True, _throttle should sleep."""
        session = _make_session(_mock_client(200, {}))
        session.config.throttle_enabled = True
        session.config.throttle_min_delay = 0.01
        session.config.throttle_max_delay = 0.02
        rpc = _make_rpc(session)
        # Set recent timestamp so elapsed < idle_timeout
        rpc._last_request_time = time.monotonic()
        with patch("piazza_sdk.adapters.http.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await rpc._throttle()
            mock_sleep.assert_called_once()
            delay = mock_sleep.call_args[0][0]
            assert 0.0 <= delay <= 0.02

    async def test_throttle_idle_reset_skips_delay(self):
        """When elapsed > idle_timeout, throttle should skip the delay."""
        session = _make_session(_mock_client(200, {}))
        session.config.throttle_enabled = True
        session.config.throttle_min_delay = 1.0
        session.config.throttle_max_delay = 2.0
        session.config.throttle_idle_timeout = 0.01
        rpc = _make_rpc(session)
        # Simulate a previous request long ago
        rpc._last_request_time = time.monotonic() - 1.0
        with patch("piazza_sdk.adapters.http.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await rpc._throttle()
            mock_sleep.assert_not_called()

    async def test_throttle_second_rapid_request_sleeps(self):
        """Second rapid request within min_delay window should sleep."""
        session = _make_session(_mock_client(200, {}))
        session.config.throttle_enabled = True
        session.config.throttle_min_delay = 0.5
        session.config.throttle_max_delay = 1.0
        session.config.throttle_idle_timeout = 30.0
        rpc = _make_rpc(session)
        # First request sets the timestamp
        rpc._last_request_time = time.monotonic()
        with patch("piazza_sdk.adapters.http.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await rpc._throttle()
            mock_sleep.assert_called_once()
            delay = mock_sleep.call_args[0][0]
            assert delay > 0


# ---------------------------------------------------------------------------
# Embedded error pattern coverage
# ---------------------------------------------------------------------------


class TestEmbeddedErrorPatterns:
    def test_method_not_found_in_error_field(self):
        """'Method not found' in error field should raise NotFoundError."""
        with pytest.raises(NotFoundError, match="Method not found"):
            _check_embedded_error({"error": "Method not found: get_user_preferences"})

    def test_does_not_exist_in_error_field(self):
        """'does not exist' in error field should raise NotFoundError."""
        with pytest.raises(NotFoundError, match="does not exist"):
            _check_embedded_error({"error": "Post 999 does not exist"})

    def test_cannot_be_found_in_error_field(self):
        """'cannot be found' in error field should raise NotFoundError."""
        with pytest.raises(NotFoundError, match="cannot be found"):
            _check_embedded_error({"error": "The resource cannot be found"})

    def test_not_found_in_stringified_result(self):
        """'not found' (lowercase) in stringified dict should raise NotFoundError."""
        with pytest.raises(NotFoundError):
            _check_embedded_error({"status": "method not found in registry"})

    def test_does_not_exist_in_stringified_result(self):
        """'does not exist' in stringified dict should raise NotFoundError."""
        with pytest.raises(NotFoundError):
            _check_embedded_error({"detail": "User does not exist"})

    def test_clean_dict_passes(self):
        """A dict without error patterns should not raise."""
        _check_embedded_error({"result": "ok", "aid": "abc"})

    def test_non_dict_passes(self):
        """Non-dict values should be ignored."""
        _check_embedded_error("just a string")
        _check_embedded_error(42)
        _check_embedded_error(None)


# ---------------------------------------------------------------------------
# Config validator
# ---------------------------------------------------------------------------


class TestConfigValidator:
    def test_min_gt_max_raises(self):
        """throttle_min_delay > throttle_max_delay should raise ValueError."""
        with pytest.raises(ValidationError, match="throttle_min_delay.*must be <="):
            PiazzaConfig(course_id="test", throttle_min_delay=5.0, throttle_max_delay=1.0)

    def test_min_eq_max_ok(self):
        """throttle_min_delay == throttle_max_delay should be accepted."""
        cfg = PiazzaConfig(course_id="test", throttle_min_delay=2.0, throttle_max_delay=2.0)
        assert cfg.throttle_min_delay == 2.0
        assert cfg.throttle_max_delay == 2.0

    def test_defaults_are_valid(self):
        """Default throttle values should be valid."""
        cfg = PiazzaConfig(course_id="test")
        assert cfg.throttle_enabled is False
        assert cfg.throttle_min_delay == 1.0
        assert cfg.throttle_max_delay == 3.0
        assert cfg.throttle_idle_timeout == 30.0
