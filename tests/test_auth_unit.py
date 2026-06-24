"""Tests for auth.py session state manager and error paths."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from httpx import Request, Response

from piazza_sdk.auth import CookieJar, SessionConfig, SessionState, SessionStateManager
from piazza_sdk.exceptions import AuthenticationError, PiazzaSDKError, SessionClosedError


class TestSessionState:
    """Tests for SessionState enum."""

    def test_states_exist(self):
        assert SessionState.UNAUTHENTICATED
        assert SessionState.AUTHENTICATING
        assert SessionState.AUTHENTICATED
        assert SessionState.CLOSED


class TestSessionStateManager:
    """Tests for SessionStateManager lifecycle."""

    def _make_manager(self, **kwargs) -> SessionStateManager:
        config = SessionConfig(course_id="test", **kwargs)
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


class TestCookieJar:
    """Tests for CookieJar."""

    def test_update_from_header(self):
        jar = CookieJar()
        jar.update_from_header("session=abc123; path=/")
        assert "session" in jar.cookies

    def test_update_from_header_multiple(self):
        jar = CookieJar()
        jar.update_from_header("a=1; b=2")
        assert "a" in jar.cookies
        assert "b" in jar.cookies

    def test_to_header(self):
        jar = CookieJar()
        jar.cookies["session"] = "abc"
        jar.cookies["csrf"] = "xyz"
        header = jar.to_header()
        assert "session=abc" in header
        assert "csrf=xyz" in header

    def test_to_header_empty(self):
        jar = CookieJar()
        assert jar.to_header() == ""


class TestCookieJarEncryption:
    """Tests for CookieJar Fernet encryption round-trip."""

    @pytest.fixture
    def fernet_key(self) -> str:
        return Fernet.generate_key().decode()

    @pytest.mark.asyncio
    async def test_save_load_encrypted(self, tmp_path, fernet_key):
        path = tmp_path / "encrypted_cookies.json"
        original = CookieJar(
            cookies={"session_id": "abc123", "csrf": "xyz789"}, encryption_key=fernet_key
        )
        await original.save(path)

        loaded = CookieJar(cookies={}, encryption_key=fernet_key)
        result = await loaded.load(path)
        assert result is True
        assert loaded.cookies == original.cookies

    @pytest.mark.asyncio
    async def test_save_load_plaintext(self, tmp_path):
        path = tmp_path / "plain_cookies.json"
        original = CookieJar(cookies={"session_id": "abc123"})
        await original.save(path)

        loaded = CookieJar()
        result = await loaded.load(path)
        assert result is True
        assert loaded.cookies == {"session_id": "abc123"}

    @pytest.mark.asyncio
    async def test_load_encrypted_file_without_key_falls_back(self, tmp_path, fernet_key):
        """An encrypted file loaded without a key should fail gracefully."""
        path = tmp_path / "encrypted.json"
        original = CookieJar(cookies={"x": "y"}, encryption_key=fernet_key)
        await original.save(path)

        loaded = CookieJar()
        result = await loaded.load(path)
        assert result is False

    @pytest.mark.asyncio
    async def test_load_plaintext_file_with_key_fails(self, tmp_path, fernet_key):
        """A plaintext file loaded with a key should raise, not silently fall back."""
        path = tmp_path / "plain.json"
        original = CookieJar(cookies={"a": "b"})
        await original.save(path)

        loaded = CookieJar(cookies={}, encryption_key=fernet_key)
        with pytest.raises(PiazzaSDKError, match="could not be decrypted"):
            await loaded.load(path)

    def test_encryption_key_excluded_from_dump(self, fernet_key):
        jar = CookieJar(cookies={"x": "y"}, encryption_key=fernet_key)
        dumped = jar.model_dump()
        assert "encryption_key" not in dumped

    @pytest.mark.asyncio
    async def test_csrf_token_persists_round_trip(self, tmp_path, fernet_key):
        """csrf_token survives save → load cycle (encrypted)."""
        path = tmp_path / "csrf_encrypted.json"
        original = CookieJar(
            cookies={"session_id": "abc"}, csrf_token="tok_123_secret", encryption_key=fernet_key
        )
        await original.save(path)

        loaded = CookieJar(cookies={}, encryption_key=fernet_key)
        await loaded.load(path)
        assert loaded.csrf_token == "tok_123_secret"
        assert loaded.cookies == {"session_id": "abc"}

    @pytest.mark.asyncio
    async def test_csrf_token_persists_plaintext(self, tmp_path):
        """csrf_token survives save → load cycle (plaintext)."""
        path = tmp_path / "csrf_plain.json"
        original = CookieJar(cookies={"s": "v"}, csrf_token="plain_tok")
        await original.save(path)

        loaded = CookieJar()
        await loaded.load(path)
        assert loaded.csrf_token == "plain_tok"

    @pytest.mark.asyncio
    async def test_csrf_token_backward_compat_no_field(self, tmp_path):
        """Loading an old file without csrf_token leaves csrf_token as None."""
        path = tmp_path / "old_format.json"
        path.write_text('{"cookies": {"session_id": "abc"}}')

        loaded = CookieJar()
        await loaded.load(path)
        assert loaded.csrf_token is None
        assert loaded.cookies == {"session_id": "abc"}

    def test_clear_resets_csrf_token(self):
        """clear() wipes both cookies dict and csrf_token."""
        jar = CookieJar(cookies={"s": "v"}, csrf_token="tok_xyz")
        jar.clear()
        assert jar.cookies == {}
        assert jar.csrf_token is None


class TestSessionStateManagerProtocol:
    """Tests for SessionManagerProtocol methods (logout, get_auth_headers, is_session_alive)."""

    def _make_manager(self, **kwargs) -> SessionStateManager:
        config = SessionConfig(course_id="test", **kwargs)
        return SessionStateManager(config)

    @pytest.mark.asyncio
    async def test_logout_calls_close(self):
        """logout() should call close() and set state to CLOSED."""
        mgr = self._make_manager()
        mgr._client = AsyncMock()
        await mgr.logout()
        assert mgr._state == SessionState.CLOSED
        assert mgr._client is None

    def test_get_auth_headers_with_token(self):
        """get_auth_headers() returns CSRF token header when available."""
        mgr = self._make_manager()
        mgr._cookies.csrf_token = "test_token_123"
        headers = mgr.get_auth_headers()
        assert headers == {"csrf-token": "test_token_123"}

    def test_get_auth_headers_without_token(self):
        """get_auth_headers() returns empty dict when no CSRF token."""
        mgr = self._make_manager()
        headers = mgr.get_auth_headers()
        assert headers == {}

    @pytest.mark.asyncio
    async def test_is_session_alive_returns_false_when_unauthenticated(self):
        """is_session_alive() returns False when not authenticated."""
        mgr = self._make_manager()
        result = await mgr.is_session_alive()
        assert result is False

    @pytest.mark.asyncio
    async def test_is_session_alive_returns_false_when_no_client(self):
        """is_session_alive() returns False when client is None."""
        mgr = self._make_manager()
        mgr._state = SessionState.AUTHENTICATED
        result = await mgr.is_session_alive()
        assert result is False

    @pytest.mark.asyncio
    async def test_is_session_alive_returns_true_on_success(self):
        """is_session_alive() returns True when RPC call succeeds."""
        mgr = self._make_manager()
        mgr._client = AsyncMock()
        mgr._state = SessionState.AUTHENTICATED

        # Build a real httpx.Response so elapsed/aread works
        fake_request = Request("POST", "https://piazza.com/logic/api")
        real_response = Response(200, json={"unread": 5}, request=fake_request)
        real_response.elapsed = timedelta(milliseconds=50)

        mgr._client.request = AsyncMock(return_value=real_response)

        result = await mgr.is_session_alive()
        assert result is True

    @pytest.mark.asyncio
    async def test_is_session_alive_returns_false_on_error(self):
        """is_session_alive() returns False when RPC call fails."""
        mgr = self._make_manager()
        mgr._client = AsyncMock()
        mgr._state = SessionState.AUTHENTICATED
        mgr._client.request = AsyncMock(side_effect=Exception("Network error"))

        result = await mgr.is_session_alive()
        assert result is False
