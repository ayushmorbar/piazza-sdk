"""Unit tests for adapters/session.py — SessionStateManager lifecycle and authentication."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import Request, Response

from piazza_sdk.adapters.auth import SessionState
from piazza_sdk.adapters.session import SessionStateManager
from piazza_sdk.config import PiazzaConfig
from piazza_sdk.exceptions import AuthenticationError, SessionClosedError


class TestSessionStateManagerLifecycle:
    """Tests for SessionStateManager state transitions and context manager."""

    def _make_manager(self, **kwargs) -> SessionStateManager:
        config = PiazzaConfig(course_id="test_course", **kwargs)
        return SessionStateManager(config)

    def test_initial_state(self):
        mgr = self._make_manager()
        assert mgr._state == SessionState.UNAUTHENTICATED
        assert not mgr.needs_refresh
        assert mgr._email is None
        assert mgr._password is None

    @pytest.mark.asyncio
    async def test_login_closed_raises(self):
        mgr = self._make_manager()
        mgr._state = SessionState.CLOSED
        with pytest.raises(SessionClosedError):
            await mgr.login("a@b.com", "pw")

    @pytest.mark.asyncio
    async def test_login_already_authenticated_raises(self):
        mgr = self._make_manager()
        mgr._state = SessionState.AUTHENTICATED
        with pytest.raises(AuthenticationError, match="Already authenticated"):
            await mgr.login("a@b.com", "pw")

    @pytest.mark.asyncio
    async def test_refresh_no_stored_creds_raises(self):
        mgr = self._make_manager()
        with pytest.raises(AuthenticationError, match="no credentials available"):
            await mgr.refresh()

    @pytest.mark.asyncio
    async def test_refresh_with_stored_creds(self):
        mgr = self._make_manager()
        mgr._email = "a@b.com"
        mgr._password = "secret"
        with patch.object(mgr, "login", new_callable=AsyncMock) as mock_login:
            await mgr.refresh()
            mock_login.assert_called_once_with("a@b.com", "secret")

    @pytest.mark.asyncio
    async def test_refresh_with_explicit_creds(self):
        mgr = self._make_manager()
        with patch.object(mgr, "login", new_callable=AsyncMock) as mock_login:
            await mgr.refresh("x@y.com", "pw123")
            mock_login.assert_called_once_with("x@y.com", "pw123")

    @pytest.mark.asyncio
    async def test_close_sets_closed(self):
        mgr = self._make_manager()
        mgr._client = AsyncMock()
        await mgr.close()
        assert mgr._state == SessionState.CLOSED
        assert mgr._client is None

    @pytest.mark.asyncio
    async def test_close_when_already_closed_noop(self):
        mgr = self._make_manager()
        mgr._state = SessionState.CLOSED
        await mgr.close()  # should not raise

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        config = PiazzaConfig(course_id="test_course")
        async with SessionStateManager(config) as session:
            assert session._client is not None
        assert session._client is None
        assert session.state == SessionState.CLOSED
        with pytest.raises(SessionClosedError):
            _ = session.client


class TestSessionStateManagerProtocols:
    """Tests for SessionStateManager helper protocol methods."""

    def _make_manager(self, **kwargs) -> SessionStateManager:
        config = PiazzaConfig(course_id="test_course", **kwargs)
        return SessionStateManager(config)

    @pytest.mark.asyncio
    async def test_logout_calls_close(self):
        mgr = self._make_manager()
        mgr._client = AsyncMock()
        await mgr.logout()
        assert mgr._state == SessionState.CLOSED
        assert mgr._client is None

    def test_get_auth_headers_with_token(self):
        mgr = self._make_manager()
        mgr._cookies.csrf_token = "test_token_123"
        headers = mgr.get_auth_headers()
        assert headers == {"csrf-token": "test_token_123"}

    def test_get_auth_headers_without_token(self):
        mgr = self._make_manager()
        headers = mgr.get_auth_headers()
        assert headers == {}

    @pytest.mark.asyncio
    async def test_is_session_alive_unauthenticated(self):
        mgr = self._make_manager()
        result = await mgr.is_session_alive()
        assert result is False

    @pytest.mark.asyncio
    async def test_is_session_alive_authenticated_success(self):
        mgr = self._make_manager()
        mgr._client = AsyncMock()
        mgr._state = SessionState.AUTHENTICATED

        fake_request = Request("POST", "https://piazza.com/logic/api")
        real_response = Response(200, json={"unread": 5}, request=fake_request)
        real_response.elapsed = timedelta(milliseconds=50)
        mgr._client.request = AsyncMock(return_value=real_response)

        result = await mgr.is_session_alive()
        assert result is True

    @pytest.mark.asyncio
    async def test_is_session_alive_error_returns_false(self):
        mgr = self._make_manager()
        mgr._client = AsyncMock()
        mgr._state = SessionState.AUTHENTICATED
        mgr._client.request = AsyncMock(side_effect=Exception("Connection reset"))

        result = await mgr.is_session_alive()
        assert result is False
