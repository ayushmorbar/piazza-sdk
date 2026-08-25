"""Tests for exception classes."""

from __future__ import annotations

import pytest

from piazza_sdk.exceptions import (
    AuthenticationError,
    ContentError,
    FeedError,
    NotAuthenticatedError,
    NotFoundError,
    PermissionError,
    PiazzaSDKError,
    RateLimitError,
    SessionClosedError,
    ValidationError,
)


class TestPiazzaSDKError:
    """Tests for the base exception class."""

    def test_basic_message(self):
        exc = PiazzaSDKError("something failed")
        assert str(exc) == "something failed"
        assert exc.status_code is None
        assert exc.response_body is None

    def test_with_status_and_body(self):
        exc = PiazzaSDKError("error", status_code=500, response_body='{"msg":"err"}')
        assert exc.status_code == 500
        assert exc.response_body == '{"msg":"err"}'

    def test_repr(self):
        exc = PiazzaSDKError("msg", status_code=404)
        assert repr(exc) == "PiazzaSDKError('msg', status_code=404)"


class TestRateLimitError:
    """Tests for RateLimitError."""

    def test_message(self):
        exc = RateLimitError("rate limited")
        assert str(exc) == "rate limited"

    def test_retry_after_ms(self):
        exc = RateLimitError("rate limited", retry_after_ms=30000)
        assert exc.retry_after_ms == 30000


class TestHierarchy:
    """Tests that all exceptions inherit from PiazzaSDKError."""

    @pytest.mark.parametrize(
        "exc_cls",
        [
            AuthenticationError,
            RateLimitError,
            NotFoundError,
            NotAuthenticatedError,
            PermissionError,
            ValidationError,
            ContentError,
            FeedError,
            SessionClosedError,
        ],
    )
    def test_is_piazza_sdk_error(self, exc_cls):
        assert issubclass(exc_cls, PiazzaSDKError)

    def test_can_catch_all(self):
        with pytest.raises(PiazzaSDKError):
            raise NotFoundError("not found")


class TestNotAuthenticatedError:
    """Tests for NotAuthenticatedError."""

    def test_message(self):
        exc = NotAuthenticatedError("not authenticated")
        assert str(exc) == "not authenticated"

    def test_default_message(self):
        exc = NotAuthenticatedError()
        # No explicit message — base class provides a fallback
        assert str(exc)  # truthy, non-empty

    def test_inherits_piazza_sdk_error(self):
        assert issubclass(NotAuthenticatedError, PiazzaSDKError)

    def test_can_catch_as_piazza_sdk_error(self):
        with pytest.raises(PiazzaSDKError):
            raise NotAuthenticatedError("no session")
