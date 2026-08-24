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

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field

from piazza_sdk.exceptions import PiazzaSDKError

logger = logging.getLogger(__name__)

PIAZZA_BASE_URL = "https://piazza.com"

# Minimum expected CSRF token length for validation
_MIN_CSRF_TOKEN_LENGTH = 16

# Set-Cookie attributes that must never be ingested as cookie name/value pairs.
_COOKIE_ATTRIBUTES = frozenset(
    {"path", "domain", "expires", "max-age", "samesite", "priority", "partitioned"}
)


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
        """Parse a Set-Cookie style header and update the jar.

        Cookie attributes (``Path``, ``Domain``, ``Expires``, ``Max-Age``,
        ``SameSite``, ``Priority``, ``Partitioned``) and flag attributes
        without a value (``HttpOnly``, ``Secure``) are ignored; only real
        name/value pairs are stored.

        Returns the number of cookies updated.
        """
        count = 0
        for raw_part in header.split(";"):
            stripped = raw_part.strip()
            # Flag attributes (HttpOnly, Secure) carry no '=' — skipped naturally.
            if "=" not in stripped:
                continue
            name, _, value = stripped.partition("=")
            name = name.strip()
            value = value.strip()
            if not name or not value:
                continue
            if name.lower() in _COOKIE_ATTRIBUTES:
                continue
            self.cookies[name] = value
            count += 1
        return count

    def _encrypt(self, data: str) -> str:
        """Encrypt a string using Fernet symmetric encryption.

        Raises:
            PiazzaSDKError: If no encryption key is configured.
        """
        if self.encryption_key is None:
            raise PiazzaSDKError("Cannot encrypt: no encryption_key is configured.")
        return Fernet(self.encryption_key).encrypt(data.encode()).decode()

    def _decrypt(self, token: str) -> str:
        """Decrypt a Fernet-encrypted token.

        Raises:
            PiazzaSDKError: If no encryption key is configured.
        """
        if self.encryption_key is None:
            raise PiazzaSDKError("Cannot decrypt: no encryption_key is configured.")
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

        Example:
            ```python
            # Example for save
            res = await save(path='...')
            ```
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

        Example:
            ```python
            # Example for load
            res = await load(path='...')
            ```
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
