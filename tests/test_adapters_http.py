"""Tests for piazza_sdk.adapters.http — RPC client and error mapping."""

from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from piazza_sdk.adapters.http import RPC, _map_http_error
from piazza_sdk.exceptions import (
    AuthenticationError,
    ContentError,
    FeedError,
    NetworkError,
    NotFoundError,
    PermissionError,
    PiazzaSDKError,
    RateLimitError,
    SearchError,
    StatisticsError,
    UploadError,
    UserError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(
    status: int = 200,
    json_data: dict | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Build a properly-read httpx.Response with JSON body."""
    content = b"{}" if json_data is None else json.dumps(json_data).encode()
    resp = httpx.Response(
        status_code=status,
        content=content,
        headers=headers or {},
        request=httpx.Request("POST", "http://test.com"),
    )
    resp.read()
    resp._elapsed = timedelta(milliseconds=1)
    return resp


def _make_error_response(status: int, headers: dict[str, str] | None = None) -> httpx.Response:
    """Build an error response suitable for raise_for_status()."""
    return _make_response(status, json_data={"error": f"HTTP {status}"}, headers=headers)


def _mock_client(
    response: httpx.Response | None = None,
    side_effect: Exception | None = None,
) -> httpx.AsyncClient:
    """Create a mock httpx.AsyncClient whose .request() returns/raises."""
    client = MagicMock(spec=httpx.AsyncClient)
    client.request = AsyncMock(return_value=response, side_effect=side_effect)
    return client


# ---------------------------------------------------------------------------
# _map_http_error unit tests
# ---------------------------------------------------------------------------

class TestMapHttpError:
    """Unit tests for the _map_http_error free function."""

    def test_401_maps_to_authentication_error(self) -> None:
        resp = _make_error_response(401)
        exc = httpx.HTTPStatusError("401", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, AuthenticationError)
        assert "401" in str(result)

    def test_403_maps_to_permission_error(self) -> None:
        resp = _make_error_response(403)
        exc = httpx.HTTPStatusError("403", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, PermissionError)

    def test_404_maps_to_not_found_error(self) -> None:
        resp = _make_error_response(404)
        exc = httpx.HTTPStatusError("404", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, NotFoundError)

    def test_429_maps_to_rate_limit_error(self) -> None:
        resp = _make_error_response(429)
        exc = httpx.HTTPStatusError("429", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, RateLimitError)
        assert result.retry_after_ms is None

    def test_429_with_retry_after_header(self) -> None:
        resp = _make_error_response(429, {"Retry-After": "30"})
        exc = httpx.HTTPStatusError("429", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, RateLimitError)
        assert result.retry_after_ms == 30_000

    def test_429_with_non_numeric_retry_after(self) -> None:
        resp = _make_error_response(429, {"Retry-After": "bad"})
        exc = httpx.HTTPStatusError("429", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, RateLimitError)
        assert result.retry_after_ms is None

    def test_500_maps_to_piazza_sdk_error(self) -> None:
        resp = _make_error_response(500)
        exc = httpx.HTTPStatusError("500", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, PiazzaSDKError)
        assert "500" in str(result)

    def test_418_maps_to_piazza_sdk_error(self) -> None:
        resp = _make_error_response(418)
        exc = httpx.HTTPStatusError("418", request=httpx.Request("GET", "http://x"), response=resp)
        result = _map_http_error(exc)
        assert isinstance(result, PiazzaSDKError)


# ---------------------------------------------------------------------------
# RPC constructor
# ---------------------------------------------------------------------------

class TestRPCInit:
    """Test RPC constructor stores attributes correctly."""

    def test_strips_trailing_slash_from_base_url(self) -> None:
        client = httpx.AsyncClient()
        rpc = RPC(client, "https://piazza.com/", "net_123")
        assert rpc._base_url == "https://piazza.com"

    def test_preserves_base_url_without_slash(self) -> None:
        client = httpx.AsyncClient()
        rpc = RPC(client, "https://piazza.com", "net_123")
        assert rpc._base_url == "https://piazza.com"

    def test_stores_network_id(self) -> None:
        client = httpx.AsyncClient()
        rpc = RPC(client, "https://piazza.com", "net_123")
        assert rpc._nid == "net_123"


# ---------------------------------------------------------------------------
# RPC._request — success path
# ---------------------------------------------------------------------------

class TestRPCRequestSuccess:
    """Test _request success path."""

    @pytest.mark.anyio
    async def test_returns_json_on_200(self) -> None:
        resp = _make_response(200, {"ok": True})
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        result = await rpc._request("POST", "/api/test")
        assert result == {"ok": True}
        client.request.assert_awaited_once()

    @pytest.mark.anyio
    async def test_constructs_correct_url(self) -> None:
        resp = _make_response(200, {"ok": True})
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        await rpc._request("POST", "/api/test")
        called_url = client.request.call_args[0][1]
        assert called_url == "https://piazza.com/api/test"

    @pytest.mark.anyio
    async def test_strips_leading_slash_from_endpoint(self) -> None:
        resp = _make_response(200, {"ok": True})
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        await rpc._request("POST", "api/test")
        called_url = client.request.call_args[0][1]
        assert called_url == "https://piazza.com/api/test"


# ---------------------------------------------------------------------------
# RPC._request — error mapping
# ---------------------------------------------------------------------------

class TestRPCRequestErrors:
    """Test _request maps HTTP errors to SDK exceptions."""

    @pytest.mark.anyio
    async def test_401_raises_authentication_error(self) -> None:
        resp = _make_error_response(401)
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(AuthenticationError):
            await rpc._request("POST", "/api/test")

    @pytest.mark.anyio
    async def test_403_raises_permission_error(self) -> None:
        resp = _make_error_response(403)
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(PermissionError):
            await rpc._request("POST", "/api/test")

    @pytest.mark.anyio
    async def test_404_raises_not_found_error(self) -> None:
        resp = _make_error_response(404)
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(NotFoundError):
            await rpc._request("POST", "/api/test")

    @pytest.mark.anyio
    async def test_429_raises_rate_limit_error(self) -> None:
        resp = _make_error_response(429)
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(RateLimitError):
            await rpc._request("POST", "/api/test")

    @pytest.mark.anyio
    async def test_500_raises_piazza_sdk_error(self) -> None:
        resp = _make_error_response(500)
        client = _mock_client(response=resp)
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(PiazzaSDKError):
            await rpc._request("POST", "/api/test")


# ---------------------------------------------------------------------------
# RPC._request — timeout / connect errors
# ---------------------------------------------------------------------------

class TestRPCRequestNetworkErrors:
    """Test timeout and connection error handling."""

    @pytest.mark.anyio
    async def test_timeout_raises_network_error(self) -> None:
        client = _mock_client(side_effect=httpx.TimeoutException("timeout"))
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(NetworkError, match="timed out"):
            await rpc._request("POST", "/api/test")

    @pytest.mark.anyio
    async def test_connect_error_raises_network_error(self) -> None:
        client = _mock_client(side_effect=httpx.ConnectError("connection refused"))
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(NetworkError, match="Connection failed"):
            await rpc._request("POST", "/api/test")

    @pytest.mark.anyio
    async def test_connect_error_preserves_cause(self) -> None:
        client = _mock_client(side_effect=httpx.ConnectError("refused"))
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(NetworkError) as exc_info:
            await rpc._request("POST", "/api/test")
        assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


# ---------------------------------------------------------------------------
# RPC._request — unexpected exception
# ---------------------------------------------------------------------------

class TestRPCRequestUnexpectedError:
    """Test that non-HTTP exceptions are wrapped in PiazzaSDKError."""

    @pytest.mark.anyio
    async def test_unexpected_error_wrapped(self) -> None:
        client = _mock_client(side_effect=ValueError("something weird"))
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(PiazzaSDKError, match="Unexpected error"):
            await rpc._request("POST", "/api/test")

    @pytest.mark.anyio
    async def test_piazza_sdk_error_reraised_directly(self) -> None:
        """PiazzaSDKError subclasses that aren't caught by other handlers pass through."""
        client = _mock_client(side_effect=ContentError("already mapped"))
        rpc = RPC(client, "https://piazza.com", "net_123")

        with pytest.raises(ContentError, match="already mapped"):
            await rpc._request("POST", "/api/test")


# ---------------------------------------------------------------------------
# RPC domain methods — happy path (mock _request)
# ---------------------------------------------------------------------------

class TestRPCContentGet:
    """Test content_get method."""

    @pytest.mark.anyio
    async def test_calls_correct_endpoint(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"content": "hello"})

        result = await rpc.content_get("post_123")
        assert result == {"content": "hello"}
        rpc._request.assert_awaited_once_with(
            "POST",
            "/class/api/content_get",
            json={"action": "content.get", "cid": "post_123", "nid": "net_123"},
        )

    @pytest.mark.anyio
    async def test_returns_empty_dict_on_non_dict(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value="string")

        result = await rpc.content_get("post_123")
        assert result == {}

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="post_123"):
            await rpc.content_get("post_123")


class TestRPCGetMyFeed:
    """Test get_my_feed method."""

    @pytest.mark.anyio
    async def test_passes_extra_kwargs(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"feed": []})

        await rpc.get_my_feed(limit=10, offset=5)
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["limit"] == 10
        assert call_kwargs["offset"] == 5

    @pytest.mark.anyio
    async def test_raises_feed_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(FeedError):
            await rpc.get_my_feed()


class TestRPCContentCreate:
    """Test content_create method."""

    @pytest.mark.anyio
    async def test_calls_correct_endpoint(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"nid": "new_post"})

        result = await rpc.content_create(type="question", subject="Help!")
        assert result == {"nid": "new_post"}
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "content.create"
        assert call_kwargs["type"] == "question"
        assert call_kwargs["subject"] == "Help!"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError):
            await rpc.content_create()


class TestRPCContentUpdate:
    """Test content_update method."""

    @pytest.mark.anyio
    async def test_calls_correct_endpoint(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"updated": True})

        await rpc.content_update(cid="post_1", content="updated text")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "content.update"
        assert call_kwargs["cid"] == "post_1"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="update"):
            await rpc.content_update(cid="post_1", content="x")


class TestRPCContentDelete:
    """Test content_delete method."""

    @pytest.mark.anyio
    async def test_sends_correct_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"success": True})

        await rpc.content_delete("post_456")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "content.delete"
        assert call_kwargs["cid"] == "post_456"

    @pytest.mark.anyio
    async def test_returns_empty_dict_on_non_dict(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value=None)

        result = await rpc.content_delete("post_456")
        assert result == {}

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="post_456"):
            await rpc.content_delete("post_456")


class TestRPCGetUsers:
    """Test get_users method."""

    @pytest.mark.anyio
    async def test_sends_correct_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"users": []})

        await rpc.get_users()
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "get_users"
        assert call_kwargs["nid"] == "net_123"

    @pytest.mark.anyio
    async def test_raises_user_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(UserError):
            await rpc.get_users()


class TestRPCSearch:
    """Test search method."""

    @pytest.mark.anyio
    async def test_sends_query(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"results": []})

        await rpc.search("python asyncio")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["query"] == "python asyncio"
        assert call_kwargs["action"] == "search"

    @pytest.mark.anyio
    async def test_passes_extra_kwargs(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.search("query", limit=5)
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["limit"] == 5

    @pytest.mark.anyio
    async def test_raises_search_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(SearchError):
            await rpc.search("query")


class TestRPCGetStats:
    """Test get_stats method."""

    @pytest.mark.anyio
    async def test_sends_correct_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"total_users": 100})

        await rpc.get_stats()
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "get_stats"

    @pytest.mark.anyio
    async def test_raises_statistics_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(StatisticsError):
            await rpc.get_stats()


class TestRPCContentAnswer:
    """Test content_answer method."""

    @pytest.mark.anyio
    async def test_sends_answer_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"nid": "answer_1"})

        await rpc.content_answer("post_1", "This is the answer", instructor_answer=True)
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "content.answer"
        assert call_kwargs["cid"] == "post_1"
        assert call_kwargs["content"] == "This is the answer"
        assert call_kwargs["instructor_answer"] is True

    @pytest.mark.anyio
    async def test_defaults_instructor_answer_false(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.content_answer("post_1", "answer")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["instructor_answer"] is False

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="answer"):
            await rpc.content_answer("post_1", "ans")


class TestRPCContentUpvote:
    """Test content_upvote method."""

    @pytest.mark.anyio
    async def test_sends_correct_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.content_upvote("post_1")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "content.upvote"
        assert call_kwargs["cid"] == "post_1"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="upvote"):
            await rpc.content_upvote("post_1")


class TestRPCContentAddTag:
    """Test content_add_tag method."""

    @pytest.mark.anyio
    async def test_sends_tag(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.content_add_tag("post_1", "important")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "content.add_tag"
        assert call_kwargs["tag"] == "important"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="add tag"):
            await rpc.content_add_tag("post_1", "tag")


class TestRPCContentRemoveTag:
    """Test content_remove_tag method."""

    @pytest.mark.anyio
    async def test_sends_remove_tag(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.content_remove_tag("post_1", "outdated")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "content.remove_tag"
        assert call_kwargs["tag"] == "outdated"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="remove tag"):
            await rpc.content_remove_tag("post_1", "tag")


class TestRPCGetInstructorStats:
    """Test get_instructor_stats method."""

    @pytest.mark.anyio
    async def test_sends_correct_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"stats": {}})

        await rpc.get_instructor_stats()
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "get_instructor_stats"

    @pytest.mark.anyio
    async def test_raises_statistics_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(StatisticsError):
            await rpc.get_instructor_stats()


class TestRPCGetOnlineUsers:
    """Test get_online_users method."""

    @pytest.mark.anyio
    async def test_sends_correct_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"users": []})

        await rpc.get_online_users()
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "get_online_users"

    @pytest.mark.anyio
    async def test_raises_user_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(UserError):
            await rpc.get_online_users()


class TestRPCGetUserPreferences:
    """Test get_user_preferences method."""

    @pytest.mark.anyio
    async def test_sends_correct_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"prefs": {}})

        await rpc.get_user_preferences()
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["action"] == "get_user_preferences"

    @pytest.mark.anyio
    async def test_raises_user_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(UserError):
            await rpc.get_user_preferences()


class TestRPCUpdateUserPreferences:
    """Test update_user_preferences method."""

    @pytest.mark.anyio
    async def test_sends_preferences(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value=None)

        await rpc.update_user_preferences({"email_digest": True})
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["email_digest"] is True
        assert call_kwargs["action"] == "update_user_preferences"

    @pytest.mark.anyio
    async def test_returns_none(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value=None)

        result = await rpc.update_user_preferences({})
        assert result is None

    @pytest.mark.anyio
    async def test_raises_user_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(UserError):
            await rpc.update_user_preferences({})


class TestRPCMarkAsUnread:
    """Test mark_as_unread method."""

    @pytest.mark.anyio
    async def test_uses_logic_api_endpoint(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.mark_as_unread("post_99")
        call_args = rpc._request.call_args
        assert call_args[0][1] == "/logic/api"
        call_kwargs = call_args[1]["json"]
        assert call_kwargs["method"] == "content.mark_unread"
        assert call_kwargs["params"]["cid"] == "post_99"
        assert call_kwargs["params"]["nid"] == "net_123"

    @pytest.mark.anyio
    async def test_returns_empty_dict_on_non_dict(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value=None)

        result = await rpc.mark_as_unread("post_99")
        assert result == {}

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="unread"):
            await rpc.mark_as_unread("post_99")


class TestRPCAddFolder:
    """Test add_folder method."""

    @pytest.mark.anyio
    async def test_sends_folder_name(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.add_folder("Exam Review")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["method"] == "network.add_folder"
        assert call_kwargs["params"]["name"] == "Exam Review"
        assert call_kwargs["params"]["nid"] == "net_123"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="folder"):
            await rpc.add_folder("Bad Folder")


class TestRPCAddBadge:
    """Test add_badge method."""

    @pytest.mark.anyio
    async def test_default_badge_type(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.add_badge("post_1")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["method"] == "content.add_badge"
        assert call_kwargs["params"]["type"] == "good_answer"

    @pytest.mark.anyio
    async def test_custom_badge_type(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.add_badge("post_1", "instructor_answer")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["params"]["type"] == "instructor_answer"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="badge"):
            await rpc.add_badge("post_1")


class TestRPCAssetGetUploadUrl:
    """Test asset_get_upload_url method."""

    @pytest.mark.anyio
    async def test_sends_filename(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"upload_url": "https://s3.example.com/upload"})

        result = await rpc.asset_get_upload_url("homework.pdf")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["method"] == "asset.get_upload_url"
        assert call_kwargs["params"]["filename"] == "homework.pdf"
        assert result["upload_url"] == "https://s3.example.com/upload"

    @pytest.mark.anyio
    async def test_raises_upload_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(UploadError, match="Failed to get upload URL for file.pdf"):
            await rpc.asset_get_upload_url("file.pdf")


class TestRPCContentSaveDraft:
    """Test content_save_draft method."""

    @pytest.mark.anyio
    async def test_sends_draft_payload(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"draft_id": "d1"})

        await rpc.content_save_draft("Title", "Body here", post_type="note")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["method"] == "content.save_draft"
        assert call_kwargs["params"]["subject"] == "Title"
        assert call_kwargs["params"]["content"] == "Body here"
        assert call_kwargs["params"]["type"] == "note"
        assert call_kwargs["params"]["has_stale_thread"] is True
        assert call_kwargs["params"]["nid"] == "net_123"

    @pytest.mark.anyio
    async def test_defaults_to_question_type(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.content_save_draft("T", "C")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["params"]["type"] == "question"

    @pytest.mark.anyio
    async def test_passes_extra_kwargs(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.content_save_draft("T", "C", folder="Homework")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["params"]["folder"] == "Homework"

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="draft"):
            await rpc.content_save_draft("T", "C")


class TestRPCContentGetSimilar:
    """Test content_get_similar method."""

    @pytest.mark.anyio
    async def test_sends_post_id(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={"similar": []})

        await rpc.content_get_similar("post_55")
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["method"] == "content.get_similar"
        assert call_kwargs["params"]["cid"] == "post_55"
        assert call_kwargs["params"]["nid"] == "net_123"

    @pytest.mark.anyio
    async def test_passes_extra_kwargs(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(return_value={})

        await rpc.content_get_similar("post_55", limit=5)
        call_kwargs = rpc._request.call_args[1]["json"]
        assert call_kwargs["params"]["limit"] == 5

    @pytest.mark.anyio
    async def test_raises_content_error(self) -> None:
        rpc = RPC(httpx.AsyncClient(), "https://piazza.com", "net_123")
        rpc._request = AsyncMock(side_effect=PiazzaSDKError("fail"))

        with pytest.raises(ContentError, match="similar"):
            await rpc.content_get_similar("post_55")
