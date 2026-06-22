"""Tests for auth.py session state manager and error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet

from piazza_sdk.auth import CookieJar, SessionConfig, SessionState, SessionStateManager
from piazza_sdk.exceptions import AuthenticationError, SessionClosedError


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
        config = SessionConfig(
            email="test@example.com", password="pass123", course_id="test", **kwargs
        )
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
    async def test_load_plaintext_file_with_key_falls_back(self, tmp_path, fernet_key):
        """A plaintext file loaded with a key should fall back to plaintext."""
        path = tmp_path / "plain.json"
        original = CookieJar(cookies={"a": "b"})
        await original.save(path)

        loaded = CookieJar(cookies={}, encryption_key=fernet_key)
        result = await loaded.load(path)
        assert result is True
        assert loaded.cookies == {"a": "b"}

    def test_encryption_key_excluded_from_dump(self, fernet_key):
        jar = CookieJar(cookies={"x": "y"}, encryption_key=fernet_key)
        dumped = jar.model_dump()
        assert "encryption_key" not in dumped
