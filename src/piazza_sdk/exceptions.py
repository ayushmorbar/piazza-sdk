"""Exception hierarchy for Piazza SDK.

Provides a structured exception tree rooted at PiazzaSDKError for
fine-grained error handling across authentication, network, and
data validation operations.

Usage::

    from piazza_sdk.exceptions import AuthenticationError, PiazzaSDKError, RateLimitError

    try:
        await session.login(email="user@example.com", password="pass")
    except AuthenticationError as exc:
        print(f"Login failed: {exc}")
    except RateLimitError as exc:
        print(f"Rate limited; retry after {exc.retry_after_ms} ms")
    except PiazzaSDKError as exc:
        print(f"SDK error (status {exc.status_code}): {exc}")
"""

from __future__ import annotations

from typing import Any


class PiazzaSDKError(Exception):
    """Base exception for all Piazza SDK errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code, if applicable.
        response_body: Parsed response body, if available.
    """

    def __init__(
        self,
        message: str = "An SDK error occurred",
        *,
        status_code: int | None = None,
        response_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __repr__(self) -> str:
        cls = type(self).__name__
        msg = str(self)
        parts = [f"{cls}({msg!r}"]
        if self.status_code is not None:
            parts.append(f", status_code={self.status_code}")
        if self.response_body is not None:
            parts.append(f", response_body={self.response_body!r}")
        parts.append(")")
        return "".join(parts)


class AuthenticationError(PiazzaSDKError):
    """Raised when login or session validation fails."""


class RateLimitError(PiazzaSDKError):
    """Raised when the API rate limit is exceeded.

    Attributes:
        retry_after_ms: Milliseconds to wait before retrying.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after_ms: int | None = None,
        status_code: int | None = None,
        response_body: Any = None,
    ) -> None:
        super().__init__(message, status_code=status_code, response_body=response_body)
        self.retry_after_ms = retry_after_ms


class NotFoundError(PiazzaSDKError):
    """Raised when a requested resource does not exist."""


class PermissionError(PiazzaSDKError):
    """Raised when the current user lacks permission for an operation."""


class ValidationError(PiazzaSDKError):
    """Raised when response data fails model validation."""


class NetworkError(PiazzaSDKError):
    """Raised when a network or connection error occurs."""


class ContentError(PiazzaSDKError):
    """Raised when content processing or parsing fails."""


class FeedError(PiazzaSDKError):
    """Raised when feed retrieval or filtering fails."""


class UserError(PiazzaSDKError):
    """Raised when user-related operations fail."""


class SearchError(PiazzaSDKError):
    """Raised when search operations fail."""


class StatisticsError(PiazzaSDKError):
    """Raised when statistics retrieval fails."""


class UploadError(PiazzaSDKError):
    """Raised when an asset upload fails."""


class SessionClosedError(PiazzaSDKError):
    """Raised when attempting operations on a closed session."""
