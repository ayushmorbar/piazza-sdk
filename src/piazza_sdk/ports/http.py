"""HTTP / RPC port definitions for hexagonal architecture.

Defines the contract for HTTP transport adapters and the low-level
RPC layer, allowing the domain to remain independent of specific
HTTP libraries or retry strategies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    import httpx


@runtime_checkable
class HTTPClientProtocol(Protocol):
    """Port for generic HTTP transport.

    Wraps the minimal ``httpx.AsyncClient`` surface the SDK actually
    uses so that alternative transports (e.g. ``aiohttp``, mock
    clients) can satisfy the contract.
    """

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, …).
            url: Fully-qualified request URL.
            **kwargs: Additional keyword arguments forwarded to the
                underlying transport (headers, json, data, timeout, …).

        Returns:
            The HTTP response object.
        """
        ...

    async def aclose(self) -> None:
        """Close the transport and release associated resources."""
        ...


@runtime_checkable
class RPCProtocol(Protocol):
    """Port for the low-level RPC client.

    Encapsulates HTTP communication with Piazza's internal API,
    including retry logic, error mapping, and response parsing.
    Adapters may wrap ``httpx``, ``aiohttp``, or any other async
    HTTP library behind this interface.
    """

    @property
    def client(self) -> httpx.AsyncClient:
        """The underlying HTTP client used for requests."""
        ...

    @property
    def base_url(self) -> str:
        """Base URL prepended to every RPC endpoint."""
        ...

    @property
    def network_id(self) -> str:
        """Piazza network (course) identifier sent with every request."""
        ...

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> Any:
        """Make an HTTP request with retry and error handling.

        Args:
            method: HTTP method (GET, POST, …).
            endpoint: API endpoint path (e.g. ``/class/api/content_get``).
            **kwargs: Extra keyword arguments forwarded to the HTTP
                transport (json, data, headers, …).

        Returns:
            Parsed JSON response body.

        Raises:
            PiazzaSDKError: On HTTP, timeout, or unexpected errors.
        """
        ...
