"""Session manager port definition for hexagonal architecture.

Combines authentication and HTTP transport into a single higher-level
port that the domain layer (e.g. ``Piazza`` client) depends on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import httpx

    from piazza_sdk.ports.auth import SessionConfigProtocol


@runtime_checkable
class SessionManagerProtocol(Protocol):
    """Port for the full session lifecycle.

    Combines authentication, HTTP client management, and configuration
    access into one cohesive interface that the application layer
    (e.g. ``Piazza``) programs against, without knowing whether the
    underlying adapter uses ``httpx``, ``aiohttp``, or anything else.
    """

    @property
    def client(self) -> httpx.AsyncClient:
        """The authenticated HTTP client for making API requests.

        Raises:
            SessionClosedError: If the session has not been opened or
                has already been closed.
        """
        ...

    @property
    def config(self) -> SessionConfigProtocol:
        """Session configuration (base_url, course_id, etc.)."""
        ...

    @property
    def needs_refresh(self) -> bool:
        """True when the session has exceeded its lifetime and must be refreshed."""
        ...

    async def login(self, email: str, password: str) -> None:
        """Authenticate with Piazza using email and password.

        Args:
            email: User email address.
            password: User password.
        """
        ...

    async def logout(self) -> None:
        """Terminate the current session and release all resources."""
        ...

    async def refresh(self) -> None:
        """Refresh an expired session by re-authenticating with stored credentials."""
        ...

    def get_auth_headers(self) -> dict[str, str]:
        """Return headers required for authenticated API requests.

        Returns:
            Dictionary of header name/value pairs (e.g. ``x-csrf-token``).
        """
        ...
