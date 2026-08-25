"""Unit tests for adapters/session.py — SessionStateManager lifecycle and authentication."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import Request, Response

from piazza_sdk.adapters.auth import SessionState
from piazza_sdk.adapters.session import SessionStateManager, _parse_login_error
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


# ---------------------------------------------------------------------------
# Login hardening: dedicated CSRF endpoint + inline ERROR_MSG surfacing
# ---------------------------------------------------------------------------


class TestFetchCsrfToken:
    """CSRF acquisition: /main/csrf_token endpoint first, page scrape fallback."""

    def _manager(self) -> SessionStateManager:
        config = PiazzaConfig(course_id="test_course")
        return SessionStateManager(config)

    @pytest.mark.asyncio
    async def test_endpoint_token_preferred(self):
        mgr = self._manager()
        endpoint_resp = Response(
            200, text='window.CSRF_TOKEN = "' + "a" * 40 + '";', request=Request("GET", "x")
        )
        page_resp = Response(200, text="<html></html>", request=Request("GET", "y"))
        mgr._client = AsyncMock()
        mgr._client.get = AsyncMock(side_effect=[endpoint_resp, page_resp])

        token = await mgr._fetch_csrf_token()
        assert token == "a" * 40
        assert mgr._client.get.await_count == 1  # fallback page never fetched

    @pytest.mark.asyncio
    async def test_falls_back_to_page_scrape(self):
        mgr = self._manager()
        endpoint_resp = Response(200, text="Not Found", request=Request("GET", "x"))
        page_html = '<meta name="csrf-token" content="' + "b" * 32 + '">'
        page_resp = Response(200, text=page_html, request=Request("GET", "https://y"))
        mgr._client = AsyncMock()
        mgr._client.get = AsyncMock(side_effect=[endpoint_resp, page_resp])

        token = await mgr._fetch_csrf_token()
        assert token == "b" * 32
        assert mgr._client.get.await_count == 2

    @pytest.mark.asyncio
    async def test_endpoint_network_error_falls_back(self):
        mgr = self._manager()
        page_html = '<meta name="csrf-token" content="' + "c" * 32 + '">'
        page_resp = Response(200, text=page_html, request=Request("GET", "y"))
        mgr._client = AsyncMock()

        async def _get(url: str, **kwargs: object) -> Response:
            if "/main/csrf_token" in str(url):
                raise httpx.ConnectError("boom")
            return page_resp

        mgr._client.get = AsyncMock(side_effect=_get)
        assert await mgr._fetch_csrf_token() == "c" * 32

    @pytest.mark.asyncio
    async def test_endpoint_short_token_rejected_then_fallback(self):
        mgr = self._manager()
        endpoint_resp = Response(
            200, text='window.CSRF_TOKEN = "tiny";', request=Request("GET", "x")
        )
        page_resp = Response(200, text="", request=Request("GET", "y"))
        mgr._client = AsyncMock()
        mgr._client.get = AsyncMock(side_effect=[endpoint_resp, page_resp])
        assert await mgr._fetch_csrf_token() is None


class TestParseLoginError:
    """Inline ERROR_MSG extraction from failed-login HTML."""

    def test_extracts_quoted_message(self):
        html = '<script>var ERROR_MSG = "Incorrect email/password";</script>'

        assert _parse_login_error(html) == "Incorrect email/password"

    def test_returns_none_when_absent(self):

        assert _parse_login_error("<html>ok</html>") is None

    def test_empty_message_is_none(self):

        assert _parse_login_error('var ERROR_MSG = "";') is None

    def test_malformed_assignment_is_none(self):

        assert _parse_login_error("var ERROR_MSG") is None


class TestLoginErrorSurfacing:
    """Failed logins surface the server's inline message."""

    @pytest.mark.asyncio
    async def test_bad_credentials_raise_server_message(self):
        mgr = SessionStateManager(PiazzaConfig(course_id="test_course"))
        csrf_resp = Response(
            200, text='window.CSRF_TOKEN = "' + "t" * 40 + '";', request=Request("GET", "x")
        )
        login_resp = Response(
            200,
            text='<script>var ERROR_MSG = "Incorrect email or password";</script>',
            request=Request("POST", "x"),
        )
        mgr._state = SessionState.AUTHENTICATING
        mgr._client = AsyncMock()
        mgr._client.get = AsyncMock(return_value=csrf_resp)
        mgr._client.post = AsyncMock(return_value=login_resp)
        mgr._client.cookies.items.return_value = []

        with pytest.raises(AuthenticationError, match="Incorrect email or password"):
            await mgr.login("a@b.com", "wrong")
        assert mgr._state == SessionState.UNAUTHENTICATED


# ---------------------------------------------------------------------------
# Plain-dict cookie export/import on the session facade
# ---------------------------------------------------------------------------


class TestSessionCookieDictFacade:
    """export_cookies/import_cookies hand-off with live-client re-application."""

    def test_export_defensive_copy(self):
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        mgr._cookies.set("session", "abc")
        exported = mgr.export_cookies()
        exported["session"] = "MUTATED"
        assert mgr.export_cookies() == {"session": "abc"}

    def test_import_applies_to_live_client_when_active(self):
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        mgr._client = httpx.AsyncClient()
        count = mgr.import_cookies({"session_id": "s9", "_piazza_s": "p9"})
        assert count == 2
        assert mgr._client.cookies.get("session_id") == "s9"

    def test_import_lands_in_jar_and_adopts_session(self):
        """Importing cookies transitions UNAUTHENTICATED -> AUTHENTICATED."""
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        assert mgr._state == SessionState.UNAUTHENTICATED
        count = mgr.import_cookies({"session_id": "s1"})
        assert count == 1
        assert mgr._cookies.get("session_id") == "s1"
        assert mgr._state == SessionState.AUTHENTICATED

    def test_closed_session_not_adopted_by_import(self):
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        mgr._state = SessionState.CLOSED
        mgr.import_cookies({"session_id": "s1"})
        assert mgr._state == SessionState.CLOSED


# ---------------------------------------------------------------------------
# Interactive prompt login (R2 — reference-client login() parity)
# ---------------------------------------------------------------------------


class TestInteractivePromptLogin:
    """When email/password are None, login() prompts interactively."""

    @pytest.fixture(autouse=True)
    def _patch_prompts(self, monkeypatch) -> None:  # noqa: ANN202
        """Provide default prompt stubs; individual tests override as needed."""
        monkeypatch.setattr("builtins.input", lambda _msg="": "prompted@x.com")
        monkeypatch.setattr(
            "piazza_sdk.adapters.session.getpass.getpass", lambda _msg="": "prompted_pass"
        )

    def _mock_login_success(self, mgr: SessionStateManager) -> None:
        """Wire up a fake client so login completes after prompting."""
        csrf_resp = Response(
            200, text='window.CSRF_TOKEN = "' + "t" * 40 + '";', request=Request("GET", "x")
        )
        # Successful login: 200 + no ERROR_MSG
        login_resp = Response(200, text="<html>ok</html>", request=Request("POST", "x"))
        mgr._client = AsyncMock()
        mgr._client.get = AsyncMock(return_value=csrf_resp)
        mgr._client.post = AsyncMock(return_value=login_resp)
        # cookies must be a plain dict (items() is sync in httpx)
        fake_cookies: dict[str, str] = {"session_id": "sid123"}
        mgr._client.cookies = fake_cookies

    @pytest.mark.asyncio
    async def test_both_none_triggers_both_prompts(self):
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        self._mock_login_success(mgr)
        await mgr.login(email=None, password=None)
        assert mgr._state == SessionState.AUTHENTICATED
        # Verify the prompted email reached the POST payload
        call_kwargs = mgr._client.post.call_args
        assert call_kwargs[1]["data"]["email"] == "prompted@x.com"
        assert call_kwargs[1]["data"]["password"] == "prompted_pass"

    @pytest.mark.asyncio
    async def test_only_password_none(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg="": "should-not-be-used")
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        self._mock_login_success(mgr)
        await mgr.login(email="explicit@x.com", password=None)
        call_kwargs = mgr._client.post.call_args
        assert call_kwargs[1]["data"]["email"] == "explicit@x.com"
        assert call_kwargs[1]["data"]["password"] == "prompted_pass"

    @pytest.mark.asyncio
    async def test_explicit_args_skip_prompts(self, monkeypatch):
        monkeypatch.setattr(
            "builtins.input",
            lambda _msg="": (_ for _ in ()).throw(AssertionError("input() called")),
        )
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        self._mock_login_success(mgr)
        await mgr.login(email="a@b.com", password="secret")
        assert mgr._state == SessionState.AUTHENTICATED
        call_kwargs = mgr._client.post.call_args
        assert call_kwargs[1]["data"]["email"] == "a@b.com"

    @pytest.mark.asyncio
    async def test_blank_prompted_email_rejected(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg="": "   ")
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        self._mock_login_success(mgr)
        with pytest.raises(AuthenticationError, match="empty or whitespace"):
            await mgr.login(email=None, password="pw")
        assert mgr._state == SessionState.UNAUTHENTICATED

    @pytest.mark.asyncio
    async def test_blank_prompted_password_rejected(self, monkeypatch):
        monkeypatch.setattr("piazza_sdk.adapters.session.getpass.getpass", lambda _msg="": "   ")
        mgr = SessionStateManager(PiazzaConfig(course_id="c1"))
        self._mock_login_success(mgr)
        with pytest.raises(AuthenticationError, match="empty or whitespace"):
            await mgr.login(email="a@b.com", password=None)
        assert mgr._state == SessionState.UNAUTHENTICATED
