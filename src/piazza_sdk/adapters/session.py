"""Session state manager adapter for Piazza SDK.

Manages the authenticated HTTP session with Piazza, handling login,
cookie management, request lifecycle, and automatic session refresh.
"""

from __future__ import annotations

import asyncio
import getpass
import logging
import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from piazza_sdk.config import SessionConfig

import httpx

from piazza_sdk.adapters.auth import _MIN_CSRF_TOKEN_LENGTH, CookieJar, SessionState
from piazza_sdk.exceptions import AuthenticationError, SessionClosedError

logger = logging.getLogger(__name__)

# Default heartbeat interval (seconds) — spec recommends 300s
_DEFAULT_HEARTBEAT_INTERVAL: float = 300.0

# Dedicated CSRF endpoint (reference client login fix): returns a JS
# assignment such as ``window.CSRF_TOKEN = "...";``
_CSRF_ENDPOINT_PATH: str = "/main/csrf_token"
_CSRF_RESPONSE_MARKER: str = "CSRF_TOKEN"

# Inline login-failure marker: failed logins return HTTP 200 with a JS
# assignment like ``var ERROR_MSG = "Incorrect email/password";``
_ERROR_MSG_MARKER: str = "VAR ERROR_MSG"


def _parse_login_error(html: str) -> str | None:
    """Extract Piazza's inline login error message from response HTML.

    Args:
        html: Raw HTML body of the login POST response.

    Returns:
        The server-supplied error text, or ``None`` when the response
        carries no inline error assignment.
    """
    pos = html.upper().find(_ERROR_MSG_MARKER)
    if pos == -1:
        return None
    end = html[pos:].find(";")
    fragment = html[pos : pos + end].translate({34: None})  # strip double quotes
    parts = fragment.split("=", 1)
    if len(parts) < 2:
        return None
    message = parts[1].strip()
    return message or None


class SessionStateManager:
    """Manages the authenticated HTTP session with Piazza.

    Handles login, cookie management, request lifecycle, and automatic
    session refresh when tokens expire.

    Usage:
        async with SessionStateManager(config) as session:
            await session.login(email="user@example.com", password="pass")
            # ... make API calls ...
    """

    # Default session lifetime before refresh (4 hours)
    DEFAULT_SESSION_LIFETIME: float = 4 * 60 * 60

    def __init__(
        self,
        config: SessionConfig,
        *,
        cookie_path: Path | None = None,
        session_lifetime: float | None = None,
    ) -> None:
        """Initialize the session state manager.

        Args:
            config: Session configuration.
            cookie_path: Optional path for persisting cookies to disk.
                         Falls back to config.cookie_path.
            session_lifetime: Seconds before auto-refresh. Defaults to 4 hours.
        """
        self.config = config
        self._state = SessionState.UNAUTHENTICATED
        self._client: httpx.AsyncClient | None = None
        self._cookies = CookieJar(encryption_key=config.encryption_key)
        self._login_time: float | None = None
        self._cookie_path = cookie_path or config.cookie_path
        self._session_lifetime = session_lifetime or self.DEFAULT_SESSION_LIFETIME
        self._email: str | None = None
        self._password: str | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._heartbeat_interval: float | None = None

    def _default_headers(self) -> dict[str, str]:
        """Build default headers matching a modern Chrome browser fingerprint."""
        platform = self.config.sec_ch_ua_platform
        return {
            "User-Agent": self.config.user_agent,
            "Content-Type": "application/json; charset=UTF-8",
            "sec-ch-ua": '"Chromium";v="125", "Not=A?Brand";v="8", "Google Chrome";v="125"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": f'"{platform}"',
        }

    def _build_client(self) -> httpx.AsyncClient:
        """Build a fresh httpx client with the standard browser fingerprint.

        Shared by ``__aenter__`` and :meth:`refresh` so every client
        carries identical default headers (a previous implementation
        omitted the Referer header on refreshed clients).
        """
        headers = self._default_headers()
        headers["Referer"] = f"{self.config.base_url}/class/{self.config.course_id}"
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=5)
        return httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers=headers,
            follow_redirects=True,
            limits=limits,
        )

    @property
    def state(self) -> SessionState:
        """Current session state."""
        return self._state

    @property
    def cookies(self) -> CookieJar:
        """Cookie jar for the session."""
        return self._cookies

    @property
    def client(self) -> httpx.AsyncClient:
        """HTTP client, raises if session is not active."""
        if self._client is None:
            raise SessionClosedError(
                "HTTP client not available — session is not active. "
                "Use 'async with SessionStateManager(config) as session'."
            )
        return self._client

    @property
    def session_age(self) -> float | None:
        """Seconds since last login, or None if not logged in."""
        if self._login_time is None:
            return None
        return time.time() - self._login_time

    @property
    def needs_refresh(self) -> bool:
        """True if session has exceeded the lifetime and should be refreshed."""
        age = self.session_age
        if age is None:
            return False
        return age > self._session_lifetime

    @staticmethod
    def _prompt_missing_credentials(email: str | None, password: str | None) -> tuple[str, str]:
        """Return (email, password), prompting interactively where *None*."""
        if email is None:
            email = input("Email: ")
        if password is None:
            password = getpass.getpass("Password: ")
        logger.info("Interactive credential entry (reference-client login UX)")
        return email, password

    async def login(self, email: str | None = None, password: str | None = None) -> None:
        """Authenticate with Piazza using email and password.

        Transitions: UNAUTHENTICATED → AUTHENTICATING → AUTHENTICATED

        When *email* or *password* is omitted, the missing values are
        prompted interactively on the terminal (``input`` for email,
        ``getpass`` for password — reference-client CLI parity), so
        ``await session.login()`` works in REPLs and scripts without
        hardcoding credentials.

        Raises:
            AuthenticationError: If login fails or CSRF token is invalid.
            SessionClosedError: If session is already closed.

        Example:
            ```python
            # Example for login
            res = await login(email='...', password='...')
            ```
        """
        if self._state == SessionState.CLOSED:
            raise SessionClosedError("Cannot login — session is closed.")
        if self._state == SessionState.AUTHENTICATED:
            raise AuthenticationError("Already authenticated.")
        if email is None or password is None:
            email, password = self._prompt_missing_credentials(email, password)
        if not email.strip() or not password.strip():
            raise AuthenticationError("Email and password cannot be empty or whitespace.")

        self._state = SessionState.AUTHENTICATING
        self._email = email
        self._password = password

        try:
            # Stage 1: Acquire a CSRF token — dedicated endpoint first,
            # login-page scrape as fallback.
            csrf_token = await self._fetch_csrf_token()

            if csrf_token is None or len(csrf_token) < _MIN_CSRF_TOKEN_LENGTH:
                self._state = SessionState.UNAUTHENTICATED
                raise AuthenticationError(
                    f"CSRF token validation failed: token missing or too short "
                    f"(expected >= {_MIN_CSRF_TOKEN_LENGTH} chars)"
                )

            # Stage 2: POST credentials as form-urlencoded to /class
            payload = {
                "from": "/signup",
                "email": email,
                "password": password,
                "remember": "on",
                "csrf_token": csrf_token,
            }

            post_headers = self._default_headers()
            post_headers["Referer"] = self.config.login_page_url
            # Override Content-Type for form-urlencoded login POST
            post_headers["Content-Type"] = "application/x-www-form-urlencoded"
            response = await self.client.post(
                self.config.login_url, data=payload, headers=post_headers, follow_redirects=True
            )

            await self._finish_login(response, csrf_token)

        except httpx.HTTPStatusError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(
                f"HTTP error during login: {exc.response.status_code}"
            ) from exc
        except TimeoutError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(f"Login request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(f"Network error during login: {exc}") from exc

    async def _fetch_csrf_token(self) -> str | None:
        """Acquire a CSRF token via the dedicated endpoint, page scrape as fallback.

        Piazza exposes ``GET /main/csrf_token`` returning a JavaScript
        assignment (e.g. ``window.CSRF_TOKEN = "...";``). When that
        endpoint is unavailable or malformed, fall back to scraping the
        login page's ``<meta name="csrf-token">`` tag (legacy path).

        Returns:
            The CSRF token string, or ``None`` when both strategies fail.
        """
        endpoint = f"{self.config.base_url}{_CSRF_ENDPOINT_PATH}"
        headers = self._default_headers()
        headers["Referer"] = self.config.login_page_url
        try:
            response = await self.client.get(endpoint, headers=headers)
            if _CSRF_RESPONSE_MARKER in response.text.upper():
                token = response.text.translate({34: None, 59: None}).split("=")[1].strip()
                if token and len(token) >= _MIN_CSRF_TOKEN_LENGTH:
                    logger.debug("CSRF token acquired from dedicated endpoint")
                    return token
                logger.warning("CSRF endpoint returned a token that failed validation")
        except httpx.HTTPError as exc:
            logger.info("CSRF endpoint fetch failed (%s); falling back to page scrape", exc)

        # Fallback: scrape the login page HTML (legacy strategy).
        login_page = await self.client.get(self.config.login_page_url, headers=headers)
        logger.debug("CSRF token scraped from login page HTML")
        return self._extract_csrf_token(login_page.text)

    async def _finish_login(self, response: httpx.Response, csrf_token: str) -> None:
        """Validate login response and persist session state."""
        if response.status_code != 200:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(f"Login failed with status {response.status_code}")

        # Piazza returns HTTP 200 even on bad credentials, embedding the
        # reason as an inline JS assignment — surface it verbatim.
        server_error = _parse_login_error(response.text)
        if server_error:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(f"Could not authenticate: {server_error}")

        # Sync httpx cookies into our CookieJar before persisting
        assert self._client is not None  # noqa: S101 - guaranteed non-None after login
        for name, value in self._client.cookies.items():
            self._cookies.set(name, value)

        # Verify session cookies actually exist (Issue 5)
        if not self._cookies.cookies:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(
                "Login returned 200 but no session cookies were set. "
                "The server may have changed its authentication flow."
            )

        self._state = SessionState.AUTHENTICATED
        self._login_time = time.time()
        logger.info("Login successful for course %s", self.config.course_id)

        # Persist CSRF token on client headers for future RPC calls
        assert self._client is not None  # noqa: S101 - guaranteed non-None after login
        self._client.headers["csrf-token"] = csrf_token
        # Persist CSRF token in cookie jar for session resumption
        self._cookies.csrf_token = csrf_token

        # Persist cookies if path configured
        if self._cookie_path is not None:
            await self._cookies.save(self._cookie_path)

    async def refresh(self, email: str | None = None, password: str | None = None) -> None:
        """Refresh an expired session by re-authenticating.

        Logs out first if currently authenticated, then performs a fresh login.
        Uses stored credentials if email/password not provided.

        Args:
            email: User email for re-authentication. Falls back to stored value.
            password: User password for re-authentication. Falls back to stored value.

        Raises:
            AuthenticationError: If refresh login fails or credentials are unavailable.

        Example:
            ```python
            # Example for refresh
            res = await refresh(email='...', password='...')
            ```
        """
        email = email or self._email
        password = password or self._password
        if email is None or password is None:
            raise AuthenticationError(
                "Cannot refresh session: no credentials available. "
                "Provide email/password or call login() first."
            )

        if self._state == SessionState.AUTHENTICATED:
            await self.close()
            self._client = self._build_client()
            self._state = SessionState.UNAUTHENTICATED

        # Clear stale CSRF token — will be re-fetched during login
        self._cookies.csrf_token = None

        await self.login(email, password)
        logger.info("Session refreshed for course %s", self.config.course_id)

    async def handle_auth_error(self) -> None:
        """Refresh callback invoked by RPC adapters on HTTP 401.

        Re-authenticates using stored credentials and re-applies cookies
        to the active httpx client so the retried request carries the new
        session. This is the public seam RPC instances program against.

        Example:
            ```python
            # Example for handle_auth_error
            res = await handle_auth_error()
            ```
        """
        await self.refresh()
        # Re-apply refreshed cookies to the live httpx client so the
        # retried RPC request carries the new session cookies.
        if self._client is not None:
            for name, value in self._cookies.cookies.items():
                self._client.cookies.set(name, value)

    async def _rpc_refresh(self) -> None:
        """Backward-compat alias for :meth:`handle_auth_error`."""
        await self.handle_auth_error()

    async def restore_cookies(self) -> bool:
        """Restore cookies from disk if a cookie path is configured.

        Returns:
            True if cookies were restored, False otherwise.

        Example:
            ```python
            # Example for restore_cookies
            res = await restore_cookies()
            ```
        """
        if self._cookie_path is None:
            return False
        loaded = await self._cookies.load(self._cookie_path)
        if loaded and self._cookies.cookies:
            self._state = SessionState.AUTHENTICATED
            if self._client is not None:
                for name, value in self._cookies.cookies.items():
                    self._client.cookies.set(name, value)
                if self._cookies.csrf_token:
                    self._client.headers["csrf-token"] = self._cookies.csrf_token
            return True
        return False

    async def logout(self) -> None:
        """Terminate the current session and release all resources.

        Alias for :meth:`close` that satisfies the ``SessionManagerProtocol``.

        Example:
            ```python
            # Example for logout
            res = await logout()
            ```
        """
        await self.close()

    def export_cookies(self) -> dict[str, str]:
        """Export session cookies as a plain name→value dictionary.

        Convenience for hand-off to browsers, ``requests.Session``, or
        any other HTTP tooling (reference-client ``get_cookies`` parity).

        Returns:
            Defensive copy of the cookie mapping.
        """
        return self._cookies.export_dict()

    def import_cookies(self, cookies: dict[str, str]) -> int:
        """Import cookies from a plain name→value dictionary.

        Mirrors the reference client's ``set_cookies``: lands in the
        persistent jar immediately, and when the session is ACTIVE the
        values are also re-applied to the live ``httpx`` client so the
        very next request carries them. The persisted CSRF token (if
        present on an active session) is re-attached as a header too.

        Adopting an externally supplied session transitions an
        UNAUTHENTICATED manager to AUTHENTICATED (same semantics as
        :meth:`restore_cookies`); verify liveness afterwards with
        :meth:`is_session_alive`. Note that JSON-RPC POSTs additionally
        require the CSRF token header — re-login or supply one when the
        imported cookies originate outside this SDK.

        Args:
            cookies: Mapping of cookie names to values.

        Returns:
            Number of cookies actually imported.
        """
        count = self._cookies.import_dict(cookies)
        if self._client is not None:
            for name, value in self._cookies.cookies.items():
                self._client.cookies.set(name, value)
            if self._cookies.csrf_token:
                self._client.headers["csrf-token"] = self._cookies.csrf_token
        if count and self._state == SessionState.UNAUTHENTICATED:
            self._state = SessionState.AUTHENTICATED
        return count

    def get_auth_headers(self) -> dict[str, str]:
        """Return headers required for authenticated API requests.

        Returns:
            Dictionary containing the ``csrf-token`` header if a CSRF
            token is available, otherwise an empty dictionary.
        """
        token = self._cookies.csrf_token
        if token:
            return {"csrf-token": token}
        return {}

    async def is_session_alive(self) -> bool:
        """Lightweight session liveness check.

        Calls ``memo.get_unread_message_count`` via RPC.  A successful
        response indicates the session cookies are still valid; any
        ``PiazzaSDKError`` or network failure returns ``False``.

        Returns:
            ``True`` if the session is alive, ``False`` otherwise.

        Example:
            ```python
            # Example for is_session_alive
            res = await is_session_alive()
            ```
        """
        if self._state != SessionState.AUTHENTICATED or self._client is None:
            return False

        try:
            from piazza_sdk.adapters.http import RPC  # noqa: PLC0415

            rpc = RPC(session=self, base_url=self.config.base_url, network_id="0")
            await rpc.memo_get_unread_message_count()
            return True
        except Exception:  # noqa: BLE001
            logger.debug("Session alive check failed", exc_info=True)
            return False

    def start_heartbeat(self, interval: float = _DEFAULT_HEARTBEAT_INTERVAL) -> None:
        """Start a background keep-alive heartbeat.

        Pings ``memo.get_unread_message_count`` every *interval* seconds
        to prevent server-side session expiration.

        Args:
            interval: Seconds between heartbeats (default 300s per spec).
        """
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            return  # already running
        self._heartbeat_interval = interval
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.debug("Heartbeat started (interval=%.0fs)", interval)

    def stop_heartbeat(self) -> None:
        """Stop the background heartbeat if running."""
        if self._heartbeat_task is not None and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            logger.debug("Heartbeat stopped")
        self._heartbeat_task = None

    async def _heartbeat_loop(self) -> None:
        """Background loop that pings the server to keep the session alive."""
        try:
            while True:
                await asyncio.sleep(self._heartbeat_interval or _DEFAULT_HEARTBEAT_INTERVAL)
                if self._state != SessionState.AUTHENTICATED:
                    break
                alive = await self.is_session_alive()
                if not alive:
                    logger.warning("Heartbeat: session expired, attempting refresh")
                    try:
                        await self.refresh()
                    except Exception:  # noqa: BLE001
                        logger.error("Heartbeat: session refresh failed", exc_info=True)
                        break
        except asyncio.CancelledError:
            pass

    async def close(self) -> None:
        """Close the session and release resources.

        Transitions: any → CLOSED

        Example:
            ```python
            # Example for close
            res = await close()
            ```
        """
        self.stop_heartbeat()
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._state = SessionState.CLOSED
        self._cookies.clear()
        self._login_time = None
        self._email = None
        self._password = None
        logger.info("Session closed")

    @staticmethod
    def _extract_csrf_token(html: str) -> str | None:
        """Extract CSRF token from login page HTML.

        Piazza embeds the CSRF token in a ``<meta>`` tag:
        ``<meta name="csrf-token" content="...">``

        Also supports legacy ``<input>`` and JSON patterns for backward
        compatibility.

        Args:
            html: Raw HTML content from the login page.

        Returns:
            The CSRF token string, or None if not found.
        """
        patterns = [
            # Piazza 2026: <meta name="csrf-token" content="...">
            r'<meta\s+name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']csrf-token["\']',
            # Legacy: <input name="csrf_token" value="...">
            r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']',
            r'name=["\']_token["\']\s+value=["\']([^"\']+)["\']',
            # JSON embedded token
            r'"csrf_token"\s*:\s*"([^"]+)"',
            r'"csrf-token"\s*:\s*"([^"]+)"',
            # Data attribute
            r'data-csrf=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None

    async def __aenter__(self) -> SessionStateManager:
        """Enter async context — creates the HTTP client and restores cookies."""
        self._client = self._build_client()
        # Auto-restore persisted cookies if available
        await self.restore_cookies()
        # Restore persisted CSRF token header for session resumption
        if self._cookies.csrf_token is not None:
            self._client.headers["csrf-token"] = self._cookies.csrf_token
            logger.debug("Restored CSRF token from cookie jar")
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Exit async context — closes the session."""
        await self.close()
