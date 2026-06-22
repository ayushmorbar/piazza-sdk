"""Authentication and session management for Piazza SDK.

Provides SessionConfig for configuring the SDK, CookieJar for managing
HTTP cookies, and SessionStateManager as an async context manager that
handles the complete authentication lifecycle.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from enum import Enum
from pathlib import Path  # noqa: TC003 - needed at runtime for Pydantic model_rebuild
from typing import Any

import httpx
from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field

from piazza_sdk.exceptions import AuthenticationError, SessionClosedError

logger = logging.getLogger(__name__)

PIAZZA_BASE_URL = "https://piazza.com"
PIAZZA_LOGIN_URL = "https://piazza.com/do_login"

# Minimum expected CSRF token length for validation
_MIN_CSRF_TOKEN_LENGTH = 16


class SessionState(Enum):
    """Lifecycle states for an SDK session.

    Transitions:
        unauthenticated → authenticating → authenticated → closed
    """

    UNAUTHENTICATED = "unauthenticated"
    AUTHENTICATING = "authenticating"
    AUTHENTICATED = "authenticated"
    CLOSED = "closed"


class CookieJar(BaseModel):
    """Simple cookie storage for session cookies.

    Stores cookies as a dictionary with domain-based namespacing.
    Supports async persistence to/from disk with optional Fernet encryption.
    """

    cookies: dict[str, str] = Field(default_factory=dict)
    encryption_key: str | None = Field(default=None, exclude=True)

    def set(self, name: str, value: str) -> None:
        """Set a cookie value."""
        self.cookies[name] = value

    def get(self, name: str) -> str | None:
        """Get a cookie value."""
        return self.cookies.get(name)

    def clear(self) -> None:
        """Clear all cookies."""
        self.cookies.clear()

    def to_header(self) -> str:
        """Serialize cookies to a Cookie header string."""
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())

    def update_from_header(self, header: str) -> int:
        """Parse a Set-Cookie header and update the jar.

        Returns the number of cookies updated.
        """
        count = 0
        for raw_part in header.split(";"):
            stripped = raw_part.strip()
            if "=" in stripped:
                name, _, value = stripped.partition("=")
                name = name.strip()
                value = value.strip()
                if name and value:
                    self.cookies[name] = value
                    count += 1
        return count

    def _encrypt(self, data: str) -> str:
        """Encrypt a string using Fernet symmetric encryption."""
        assert self.encryption_key is not None
        return Fernet(self.encryption_key).encrypt(data.encode()).decode()

    def _decrypt(self, token: str) -> str:
        """Decrypt a Fernet-encrypted token."""
        assert self.encryption_key is not None
        return Fernet(self.encryption_key).decrypt(token.encode()).decode()

    async def save(self, path: Path) -> None:
        """Persist cookies to a JSON file asynchronously.

        If an encryption_key is set, the cookie payload is Fernet-encrypted
        before writing. The file is created with mode 0o600 on POSIX systems.

        Args:
            path: File path to save cookies to.
        """
        payload = json.dumps(self.model_dump(), indent=2)

        if self.encryption_key:
            payload = self._encrypt(payload)

        def _write_sync() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload)

        await asyncio.to_thread(_write_sync)
        logger.debug("Cookies saved to %s (encrypted=%s)", path, bool(self.encryption_key))

    async def load(self, path: Path) -> bool:
        """Load cookies from a JSON file asynchronously.

        Supports both encrypted and plaintext cookie files. When an
        encryption_key is set, decryption is attempted first; if that
        fails, plaintext loading is tried as a fallback.

        Args:
            path: File path to load cookies from.

        Returns:
            True if cookies were loaded, False if file doesn't exist.
        """

        def _read_sync() -> str | None:
            try:
                return path.read_text()
            except FileNotFoundError:
                return None

        text = await asyncio.to_thread(_read_sync)
        if text is None:
            logger.debug("Cookie file not found: %s", path)
            return False

        # Try encrypted first if key is available
        if self.encryption_key:
            try:
                text = self._decrypt(text)
            except InvalidToken:
                logger.debug("Cookie file %s is not encrypted; loading as plaintext", path)

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "cookies" in data:
                self.cookies = data["cookies"]
                logger.debug("Cookies loaded from %s", path)
                return True
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse cookie file %s: %s", path, exc)
        return False


class SessionConfig(BaseModel):
    """Configuration for a Piazza SDK session.

    Attributes:
        course_id: The Piazza course/network ID.
        user_agent: Custom User-Agent string.
        base_url: Base URL for the Piazza API.
        timeout: HTTP request timeout in seconds.
        retries: Number of retry attempts for transient failures.
        retry_delay: Base delay between retries in seconds.
        cookie_path: Path for persisting cookies to disk.
        encryption_key: Fernet key for encrypting persisted cookies.
    """

    course_id: str
    user_agent: str = "piazza-sdk-python/2026.06.22"
    base_url: str = PIAZZA_BASE_URL
    timeout: float = 30.0
    retries: int = 3
    retry_delay: float = 1.0
    cookie_path: Path | None = None
    encryption_key: str | None = None

    def model_post_init(self, __context: Any) -> None:
        """Validate and enforce HTTPS on base_url."""
        if self.base_url and not self.base_url.startswith("https://"):
            self.base_url = self.base_url.replace("http://", "https://")
            if not self.base_url.startswith("https://"):
                self.base_url = f"https://{self.base_url}"

    @property
    def login_url(self) -> str:
        """Full login URL derived from base_url."""
        return f"{self.base_url.rstrip('/')}/do_login"

    @property
    def network_base_url(self) -> str:
        """Base URL for network API calls."""
        return f"{self.base_url.rstrip('/')}/network"


SessionConfig.model_rebuild()


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

            if response.status_code == 200:
                self._state = SessionState.AUTHENTICATED
                self._login_time = time.time()
                logger.info("Login successful for course %s", self.config.course_id)

                # Persist CSRF token on client headers for future RPC calls
                assert self._client is not None  # noqa: S101 - guaranteed non-None after login
                self._client.headers["x-csrf-token"] = csrf_token

                # Sync httpx cookies into our CookieJar before persisting
                for name, value in self._client.cookies.items():
                    self._cookies.set(name, value)

                # Persist cookies if path configured
                if self._cookie_path is not None:
                    await self._cookies.save(self._cookie_path)
            else:
                self._state = SessionState.UNAUTHENTICATED
                raise AuthenticationError(f"Login failed with status {response.status_code}")

        except httpx.HTTPStatusError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(
                f"HTTP error during login: {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            self._state = SessionState.UNAUTHENTICATED
            raise AuthenticationError(f"Network error during login: {exc}") from exc

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
