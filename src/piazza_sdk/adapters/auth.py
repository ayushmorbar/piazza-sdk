"""Authentication and session management for Piazza SDK.

Provides SessionConfig for configuring the SDK, CookieJar for managing
HTTP cookies, and SessionStateManager as an async context manager that
handles the complete authentication lifecycle.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from enum import Enum
from pathlib import Path  # noqa: TC003 - needed at runtime for Pydantic model_rebuild
from typing import Any
from urllib.parse import urlparse

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings

from piazza_sdk.exceptions import PiazzaSDKError

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

    Attributes:
        cookies: Dictionary of cookie name-value pairs.
        csrf_token: Persisted CSRF token for session restoration.
        encryption_key: Fernet key for encrypting the cookie file (excluded from serialization).
    """

    cookies: dict[str, str] = Field(default_factory=dict)
    csrf_token: str | None = Field(default=None)
    encryption_key: str | None = Field(default=None, exclude=True)

    def set(self, name: str, value: str) -> None:
        """Set a cookie value."""
        self.cookies[name] = value

    def get(self, name: str) -> str | None:
        """Get a cookie value."""
        return self.cookies.get(name)

    def clear(self) -> None:
        """Clear all cookies and the persisted CSRF token."""
        self.cookies.clear()
        self.csrf_token = None

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
        before writing. The file is created with mode 0o600 on POSIX systems
        using an atomic write to prevent TOCTOU race conditions.

        Args:
            path: File path to save cookies to.

        Raises:
            PiazzaSDKError: If the file cannot be written.
        """
        payload = json.dumps(self.model_dump(), indent=2)

        if self.encryption_key:
            payload = self._encrypt(payload)

        def _write_sync() -> None:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                # Atomic write: create with restrictive permissions (0o600)
                # to prevent TOCTOU race condition between write and chmod.
                fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                try:
                    os.write(fd, payload.encode())
                finally:
                    os.close(fd)
            except OSError as exc:
                raise PiazzaSDKError(f"Failed to write cookie file {path}: {exc}") from exc

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

        Raises:
            PiazzaSDKError: If the file exists but cannot be read.
        """

        def _read_sync() -> str | None:
            try:
                return path.read_text()
            except FileNotFoundError:
                return None
            except OSError as exc:
                raise PiazzaSDKError(f"Failed to read cookie file {path}: {exc}") from exc

        text = await asyncio.to_thread(_read_sync)
        if text is None:
            logger.debug("Cookie file not found: %s", path)
            return False

        # Try encrypted first if key is available
        if self.encryption_key:
            try:
                text = self._decrypt(text)
            except InvalidToken:
                raise PiazzaSDKError(
                    f"Cookie file {path} could not be decrypted. "
                    "This may indicate the file was tampered with or the "
                    "encryption key has changed. Delete the cookie file and "
                    "re-authenticate."
                )

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "cookies" in data:
                self.cookies = data["cookies"]
                # Restore persisted CSRF token (backward-compatible with old files)
                self.csrf_token = data.get("csrf_token")
                logger.debug("Cookies loaded from %s", path)
                return True
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Failed to parse cookie file %s: %s", path, exc)
        return False


class FernetTokenStorage:
    """Placeholder for Fernet-based token storage.

    Kept for backward compatibility. The actual encryption logic lives
    in CookieJar._encrypt/_decrypt.
    """


class SessionConfig(BaseSettings):
    """Configuration for a Piazza SDK session.

    Supports loading from environment variables with the ``PIAZZA_`` prefix
    (e.g. ``PIAZZA_COURSE_ID``, ``PIAZZA_TIMEOUT``). Explicit constructor
    arguments always take precedence over environment variables.

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

    model_config = {"env_prefix": "PIAZZA_"}

    course_id: str
    user_agent: str = "piazza-sdk-python/2026.06.22"
    base_url: str = PIAZZA_BASE_URL
    timeout: float = 30.0
    retries: int = 3
    retry_delay: float = 1.0
    cookie_path: Path | None = None
    encryption_key: str | None = None

    @field_validator("encryption_key")
    @classmethod
    def _validate_fernet_key(cls, v: str | None) -> str | None:
        """Validate that the encryption key is a valid Fernet key."""
        if v is None:
            return v
        try:
            Fernet(v.encode() if isinstance(v, str) else v)
        except Exception as e:
            raise ValueError(
                f"Invalid Fernet encryption key: {e}. "
                "Generate a valid key with: from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())"
            ) from e
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate and enforce HTTPS on base_url."""
        if self.base_url:
            parsed = urlparse(self.base_url)
            if parsed.scheme != "https":
                # Rebuild URL with HTTPS scheme
                self.base_url = parsed._replace(scheme="https").geturl()

    @property
    def login_page_url(self) -> str:
        """Full URL for the login page (GET to capture CSRF token)."""
        return f"{self.base_url.rstrip('/')}/account/login"

    @property
    def login_url(self) -> str:
        """Full login POST URL for credential submission."""
        return f"{self.base_url.rstrip('/')}/class"

    @property
    def network_base_url(self) -> str:
        """Base URL for network API calls."""
        return f"{self.base_url.rstrip('/')}/network"


SessionConfig.model_rebuild()
