"""Session state manager adapter for Piazza SDK.

Manages the authenticated HTTP session with Piazza, handling login,
cookie management, request lifecycle, and automatic session refresh.
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import httpx

from piazza_sdk.adapters.auth import CookieJar, SessionConfig, SessionState
from piazza_sdk.exceptions import AuthenticationError, SessionClosedError

logger = logging.getLogger(__name__)

# Minimum expected CSRF token length for validation
_MIN_CSRF_TOKEN_LENGTH = 16


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

    async def login(self, email: str, password: str) -> None:
        """Authenticate with Piazza using email and password.

        Transitions: UNAUTHENTICATED → AUTHENTICATING → AUTHENTICATED

        Raises:
            AuthenticationError: If login fails or CSRF token is invalid.
            SessionClosedError: If session is already closed.
        """
        if self._state == SessionState.CLOSED:
            raise SessionClosedError("Cannot login — session is closed.")
        if self._state == SessionState.AUTHENTICATED:
            raise AuthenticationError("Already authenticated.")

        self._state = SessionState.AUTHENTICATING
        self._email = email
        self._password = password

        try:
            # Fetch login page to get CSRF token
            login_page = await self.client.get(
                self.config.login_url, headers={"User-Agent": self.config.user_agent}
            )
            csrf_token = self._extract_csrf_token(login_page.text)

            if csrf_token is None or len(csrf_token) < _MIN_CSRF_TOKEN_LENGTH:
                self._state = SessionState.UNAUTHENTICATED
                raise AuthenticationError(
                    f"CSRF token validation failed: token missing or too short "
                    f"(expected >= {_MIN_CSRF_TOKEN_LENGTH} chars)"
                )

            payload = {
                "email": email,
                "password": password,
                "action": "login",
                "course_id": self.config.course_id,
                "csrf_token": csrf_token,
            }

            response = await self.client.post(
                self.config.login_url,
                data=payload,
                headers={"User-Agent": self.config.user_agent},
                follow_redirects=True,
            )

            await self._finish_login(response, csrf_token)

        except httpx.HTTPStatusError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(
                f"HTTP error during login: {exc.response.status_code}"
            ) from exc
        except TimeoutError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(
                f"Login request timed out: {exc}"
            ) from exc
        except httpx.RequestError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(f"Network error during login: {exc}") from exc

    async def _finish_login(self, response: httpx.Response, csrf_token: str) -> None:
        """Validate login response and persist session state."""
        if response.status_code != 200:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(f"Login failed with status {response.status_code}")

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
        self._client.headers["x-csrf-token"] = csrf_token

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
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={"User-Agent": self.config.user_agent},
                follow_redirects=True,
            )
            self._state = SessionState.UNAUTHENTICATED

        await self.login(email, password)
        logger.info("Session refreshed for course %s", self.config.course_id)

    async def _rpc_refresh(self) -> None:
        """Refresh callback invoked by RPC on HTTP 401 (Issue 6).

        Re-authenticates using stored credentials and re-applies cookies
        to the active httpx client.
        """
        await self.refresh()
        # Re-apply refreshed cookies to the live httpx client so the
        # retried RPC request carries the new session cookies.
        if self._client is not None:
            for name, value in self._cookies.cookies.items():
                self._client.cookies.set(name, value)

    async def restore_cookies(self) -> bool:
        """Restore cookies from disk if a cookie path is configured.

        Returns:
            True if cookies were restored, False otherwise.
        """
        if self._cookie_path is None:
            return False
        return await self._cookies.load(self._cookie_path)

    async def close(self) -> None:
        """Close the session and release resources.

        Transitions: any → CLOSED
        """
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

        Args:
            html: Raw HTML content from the login page.

        Returns:
            The CSRF token string, or None if not found.
        """
        patterns = [
            r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']',
            r'name=["\']_token["\']\s+value=["\']([^"\']+)["\']',
            r'"csrf_token"\s*:\s*"([^"]+)"',
            r'data-csrf=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return None

    async def __aenter__(self) -> SessionStateManager:
        """Enter async context — creates the HTTP client and restores cookies."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers={"User-Agent": self.config.user_agent},
            follow_redirects=True,
        )
        # Auto-restore persisted cookies if available
        await self.restore_cookies()
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: Any
    ) -> None:
        """Exit async context — closes the session."""
        await self.close()
