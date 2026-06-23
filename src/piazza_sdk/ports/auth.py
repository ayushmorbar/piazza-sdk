"""Authentication port definitions for hexagonal architecture.

Defines the contract for authentication adapters, decoupling domain
logic from concrete auth implementations (session managers, token
storage backends, configuration providers).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SessionConfigProtocol(Protocol):
    """Port for session configuration providers.

    Any config object used by the auth adapter must expose at least
    the base URL and course identifier.
    """

    @property
    def base_url(self) -> str:
        """Base URL for the Piazza API."""
        ...

    @property
    def course_id(self) -> str:
        """Piazza course / network identifier."""
        ...


@runtime_checkable
class TokenStorageProtocol(Protocol):
    """Port for token persistence backends.

    Adapters may store opaque token bytes to any medium (disk,
    keyring, database) as long as they satisfy this interface.
    """

    def load(self) -> bytes:
        """Load persisted token data.

        Returns:
            Raw token bytes, or empty bytes if nothing is stored.
        """
        ...

    def save(self, token_data: bytes) -> None:
        """Persist token data.

        Args:
            token_data: Raw token bytes to store.
        """
        ...

    def clear(self) -> None:
        """Remove all persisted token data."""
        ...


@runtime_checkable
class AuthProtocol(Protocol):
    """Port for authentication lifecycle management.

    Concrete adapters (e.g. ``SessionStateManager``) implement this
    protocol to let the domain layer authenticate, refresh, and
    obtain auth headers without knowing the underlying transport.
    """

    async def login(self, email: str, password: str) -> None:
        """Authenticate with Piazza using email and password.

        Args:
            email: User email address.
            password: User password.
        """
        ...

    async def logout(self) -> None:
        """Terminate the current session and release resources."""
        ...

    async def refresh(self) -> None:
        """Refresh an expired session (re-authenticate with stored credentials)."""
        ...

    @property
    def needs_refresh(self) -> bool:
        """True when the session has exceeded its lifetime and must be refreshed."""
        ...

    def get_auth_headers(self) -> dict[str, str]:
        """Return headers required for authenticated API requests.

        Returns:
            Dictionary of header name/value pairs (e.g. ``x-csrf-token``).
        """
        ...
