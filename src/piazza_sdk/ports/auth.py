"""Authentication port definitions for hexagonal architecture.

Defines the contract for authentication adapters, decoupling domain
logic from concrete auth implementations (session managers, token
storage backends, configuration providers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


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

    Matches the :class:`~piazza_sdk.adapters.auth.CookieJar` contract:
    async load/save against a filesystem path, with adapters free to
    target other media (keyring, database) behind the same shape.
    """

    async def load(self, path: Path) -> bool:
        """Load persisted token data from *path*.

        Args:
            path: File path to read from.

        Returns:
            True if data was loaded, False if nothing was stored.

        Example:
            ```python
            # Example for load
            res = await load(path='...')
            ```
        """
        ...

    async def save(self, path: Path) -> None:
        """Persist token data to *path*.

        Args:
            path: File path to write to store.

        Example:
            ```python
            # Example for save
            res = await save(path='...')
            ```
        """
        ...

    def clear(self) -> None:
        """Remove all persisted in-memory token data."""
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

        Example:
            ```python
            # Example for login
            res = await login(email='...', password='...')
            ```
        """
        ...

    async def logout(self) -> None:
        """Terminate the current session and release resources.
        Example:
            ```python
            # Example for logout
            res = await logout()
            ```
        """
        ...

    async def refresh(self, email: str | None = None, password: str | None = None) -> None:
        """Refresh an expired session (re-authenticate with stored credentials).

        Args:
            email: Optional credential override for this refresh.
            password: Optional credential override for this refresh.

        Example:
            ```python
            # Example for refresh
            res = await refresh(email='...', password='...')
            ```
        """
        ...

    @property
    def needs_refresh(self) -> bool:
        """True when the session has exceeded its lifetime and must be refreshed."""
        ...

    def get_auth_headers(self) -> dict[str, str]:
        """Return headers required for authenticated API requests.

        Returns:
            Dictionary of header name/value pairs (e.g. ``csrf-token``).
        """
        ...
