"""HTTP RPC layer for Piazza SDK.

Provides the low-level RPC client that handles HTTP communication
with Piazza's internal API, including retry logic, rate limiting,
and error mapping.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import time
from typing import TYPE_CHECKING, Any, TypeVar

import httpx
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception, stop_after_attempt

from piazza_sdk.exceptions import (
    AuthenticationError,
    ContentError,
    FeedError,
    NetworkError,
    NotFoundError,
    PermissionError,
    PiazzaSDKError,
    RateLimitError,
    SearchError,
    StatisticsError,
    UploadError,
    UserError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from piazza_sdk.models.enums import PostType
    from piazza_sdk.ports.session import SessionManagerProtocol

# Keys that must never be overridden by caller-supplied kwargs.
_BLOCKED_KEYS = frozenset({"action", "method", "nid", "params"})

# HTTP statuses pre-emptively mapped before response parsing (transient failures).
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

# Retry policy defaults (overridable per-instance / via SessionConfig knobs).
_DEFAULT_MAX_ATTEMPTS = 3
_RETRY_BASE_DELAY_S = 1.0
_RETRY_MAX_WAIT_S = 10.0
_RATE_LIMIT_MAX_WAIT_S = 30.0


class _AuthRetryNeededError(Exception):
    """Raised inside the request body to trigger a retry after a token refresh."""


def _map_http_error(exc: httpx.HTTPStatusError) -> PiazzaSDKError:
    """Map an HTTP status error to an SDK exception.

    The ``status_code`` attribute is populated on every mapped error so the
    retry predicate can distinguish transient server errors (5xx) from
    permanent client errors (4xx).
    """
    status = exc.response.status_code
    if status == 401:
        err: PiazzaSDKError = AuthenticationError(f"Unauthorized: {status}")
    elif status == 403:
        err = PermissionError(f"Forbidden: {status}")
    elif status == 404:
        err = NotFoundError(f"Not found: {status}")
    elif status == 429:
        retry_after = exc.response.headers.get("Retry-After")
        retry_after_ms: int | None = None
        if retry_after:
            with contextlib.suppress(ValueError):
                raw = int(retry_after) * 1000
                retry_after_ms = max(0, min(raw, int(_RATE_LIMIT_MAX_WAIT_S * 1000)))
        err = RateLimitError(f"Rate limited: {status}", retry_after_ms=retry_after_ms)
    else:
        err = PiazzaSDKError(f"HTTP error {status}")
    err.status_code = status
    return err


def _is_retryable(exc: BaseException) -> bool:
    """Tenacity retry predicate.

    Retries transient transport failures (timeouts, connection resets —
    surfaced as ``NetworkError``), rate limits, the post-refresh sentinel,
    and 5xx-class HTTP errors. Client errors (4xx) propagate immediately.
    """
    if isinstance(exc, (_AuthRetryNeededError, NetworkError, RateLimitError)):
        return True
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and status >= 500


def _compute_retry_wait(retry_state: RetryCallState) -> float:
    """Exponential backoff that honors ``Retry-After`` for rate-limit responses."""
    outcome = retry_state.outcome
    outcome_exc = outcome.exception() if outcome is not None else None
    if isinstance(outcome_exc, RateLimitError) and outcome_exc.retry_after_ms:
        return min(float(outcome_exc.retry_after_ms) / 1000.0, _RATE_LIMIT_MAX_WAIT_S)
    delay = _RETRY_BASE_DELAY_S * (2 ** max(retry_state.attempt_number - 1, 0))
    # Non-cryptographic use: jitter only spaces out retries; no security sensitivity.
    jitter = random.uniform(0, _RETRY_BASE_DELAY_S)  # noqa: S311
    return float(min(delay + jitter, _RETRY_MAX_WAIT_S))


def _check_embedded_error(result: Any) -> None:
    """Inspect a successful response body for embedded error indicators.

    Some Piazza endpoints return HTTP 200 with an error payload in the body.
    This catches those cases and maps them to typed SDK exceptions.
    """
    if not isinstance(result, dict):
        return

    # Check for explicit error field
    patterns = ("not found", "does not exist", "cannot be found")

    for field in ("error", "status", "detail", "message"):
        val = result.get(field)
        if val and isinstance(val, str):
            lower = val.lower()
            if any(p in lower for p in patterns):
                logger.warning("Embedded error detected in field '%s': %s", field, val[:200])
                raise NotFoundError(f"Resource not found: {val[:200]}", response_body=result)


class RPC:
    """Low-level RPC client for Piazza's internal API.

    Handles HTTP requests with retry logic, error mapping, and
    response parsing.

    RPC holds a reference to the *session adapter* rather than copying
    the ``httpx.AsyncClient`` directly.  This ensures that after a
    session refresh (which replaces the underlying client), all RPC
    instances automatically use the new client without requiring
    callers to re-create them.
    """

    def __init__(  # noqa: PLR0913 - explicit config surface mirrors SessionConfig knobs
        self,
        session: SessionManagerProtocol | Any,
        base_url: str,
        network_id: str,
        *,
        on_auth_error: Callable[[], Any] | None = None,
        max_attempts: int | None = None,
        retry_base_delay: float | None = None,
        retry_sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        """Create an RPC client bound to a session adapter.

        Args:
            session: Object exposing ``client`` (typically
                :class:`~piazza_sdk.adapters.session.SessionStateManager`,
                which satisfies :class:`~piazza_sdk.ports.session.SessionManagerProtocol`).
            base_url: Base URL prepended to every endpoint.
            network_id: Piazza network (course) ID for this client.
            on_auth_error: Callback invoked on HTTP 401 before a single retry.
            max_attempts: Retry attempt budget. Defaults to 3.
            retry_base_delay: Base delay (seconds) for exponential backoff.
                Defaults to 1.0.
            retry_sleep: Sleep callable used between retries. Defaults to
                ``asyncio.sleep``; injectable for fast tests.
        """
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._nid = network_id
        self._on_auth_error = on_auth_error
        self._last_aid: str | None = None
        default_attempts: int | None = max_attempts
        self._max_attempts = (
            max(1, default_attempts) if default_attempts is not None else _DEFAULT_MAX_ATTEMPTS
        )
        self._retry_base_delay = (
            retry_base_delay if retry_base_delay is not None else _RETRY_BASE_DELAY_S
        )
        self._retry_sleep = retry_sleep

        self._last_request_time: float = 0.0
        config = getattr(session, "config", None)
        self._throttle_enabled: bool = getattr(config, "throttle_enabled", False)
        self._throttle_min_delay: float = getattr(config, "throttle_min_delay", 1.0)
        self._throttle_max_delay: float = getattr(config, "throttle_max_delay", 3.0)
        self._throttle_idle_timeout: float = getattr(config, "throttle_idle_timeout", 30.0)

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the current httpx client from the session adapter."""
        return self._session.client

    async def _throttle(self) -> None:
        """Insert a uniform-random delay between consecutive requests.

        The delay is skipped entirely when:
        * ``throttle_enabled`` is ``False`` (the default), or
        * the time since the last request exceeds ``throttle_idle_timeout``
          (user was idle / browsing casually).
        """
        if not self._throttle_enabled:
            return

        now = time.monotonic()
        elapsed = now - self._last_request_time

        # Idle reset: user was away long enough — no throttle needed.
        if elapsed >= self._throttle_idle_timeout:
            self._last_request_time = now
            return

        # Non-cryptographic use: randomizes pacing between requests; no security sensitivity.
        delay = random.uniform(self._throttle_min_delay, self._throttle_max_delay)  # noqa: S311
        remaining = delay - elapsed
        if remaining > 0:
            logger.debug(
                "Throttling for %.2fs (elapsed %.2fs, range [%.2f, %.2f])",
                remaining,
                elapsed,
                self._throttle_min_delay,
                self._throttle_max_delay,
            )
            await asyncio.sleep(remaining)

        self._last_request_time = time.monotonic()

    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Make an HTTP request with retry and error handling.

        Retries (with exponential backoff honoring ``Retry-After``):
        - Connection and timeout errors
        - HTTP 429 rate limits
        - HTTP 5xx server errors
        - HTTP 401 after a single session-refresh attempt

        Client errors (other 4xx) propagate immediately as typed SDK exceptions.
        """
        await self._throttle()
        retryer = AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(self._max_attempts),
            wait=self._wait_strategy,
            sleep=self._retry_sleep if self._retry_sleep is not None else asyncio.sleep,
            reraise=True,
        )
        return await retryer(self._request_once, method, endpoint, **kwargs)

    def _wait_strategy(self, retry_state: RetryCallState) -> float:
        """Per-instance exponential backoff honoring the configured base delay."""
        outcome = retry_state.outcome
        exc = outcome.exception() if outcome is not None else None
        if isinstance(exc, RateLimitError) and exc.retry_after_ms:
            return min(float(exc.retry_after_ms) / 1000.0, _RATE_LIMIT_MAX_WAIT_S)
        delay = self._retry_base_delay * (2 ** max(retry_state.attempt_number - 1, 0))
        return float(min(delay, _RETRY_MAX_WAIT_S))

    async def _request_once(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Execute a single HTTP request attempt with error mapping."""
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        logger.debug("RPC %s %s", method, url)
        try:
            response = await self.client.request(method, url, **kwargs)
            logger.debug(
                "RPC %s %s -> %d (%.1fms)",
                method,
                url,
                response.status_code,
                response.elapsed.total_seconds() * 1000,
            )
            # Map transient statuses before JSON parsing (error bodies may not be JSON)
            if response.status_code in _RETRYABLE_STATUS:
                exc = httpx.HTTPStatusError(
                    f"{response.status_code}", request=response.request, response=response
                )
                raise _map_http_error(exc) from exc
            response.raise_for_status()
            data = response.json()
            # Track the aid concurrency token from every response
            if isinstance(data, dict) and "aid" in data:
                self._last_aid = data["aid"]
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401 and self._on_auth_error is not None:
                logger.info("RPC %s %s 401 – refreshing session", method, url)
                await self._on_auth_error()
                raise _AuthRetryNeededError(method, url) from exc
            logger.warning("RPC %s %s failed: %d", method, url, exc.response.status_code)
            raise _map_http_error(exc) from exc
        except httpx.TimeoutException as exc:
            logger.warning("RPC %s %s timed out: %s", method, url, exc)
            raise NetworkError(f"Request timed out: {exc}") from exc
        except httpx.ConnectError as exc:
            logger.warning("RPC %s %s connection failed: %s", method, url, exc)
            raise NetworkError(f"Connection failed: {exc}") from exc
        except PiazzaSDKError:
            raise
        except Exception as exc:
            logger.warning("RPC %s %s unexpected error: %s", method, url, exc)
            raise PiazzaSDKError(f"Unexpected error: {exc}") from exc

    async def call(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        error_cls: type[PiazzaSDKError] = PiazzaSDKError,
        error_msg: str = "RPC call failed",
        method: str = "POST",
    ) -> Any:
        """Execute an RPC request and return the unwrapped JSON-RPC result as-is.

        Unlike :meth:`_safe_call`, this preserves *list-shaped* results
        (e.g. ``user/api/get_user_classes`` returns a bare list) instead of
        coercing them to ``{}``.

        Args:
            endpoint: API endpoint path (forwarded to ``_request``).
            payload: JSON payload for the request.
            error_cls: Exception class for embedded JSON-RPC errors.
            error_msg: Message prefix for the raised exception.
            method: HTTP method (default ``"POST"``).

        Returns:
            The unwrapped ``result`` value (dict, list, scalar) or the raw
            body when no envelope is present.

        Example:
            ```python
            # Example for call
            res = await call(endpoint='...', payload='...')
            ```
        """
        raw = await self._request(method, endpoint, json=payload)
        if not isinstance(raw, dict):
            return raw
        # JSON-RPC envelope: {"result": ..., "error": ..., "aid": ...}
        if "result" in raw:
            rpc_error = raw.get("error")
            if rpc_error is not None:
                _check_embedded_error(raw)
                raise error_cls(f"{error_msg}: {rpc_error}")
            _check_embedded_error(raw["result"])
            return raw["result"]
        _check_embedded_error(raw)
        return raw

    async def _safe_call(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        error_cls: type[PiazzaSDKError] = PiazzaSDKError,
        error_msg: str = "RPC call failed",
        method: str = "POST",
    ) -> dict[str, Any]:
        """Execute an RPC request expecting a dict-shaped result.

        Wraps ``_request`` with two behaviors:

        1. Unwraps the JSON-RPC ``{result, error, aid}`` envelope so callers
           receive only the ``result`` payload.
        2. Coerces non-dict results to ``{}`` (use :meth:`call` when a list
           or scalar result is expected).

        Typed SDK exceptions raised by the transport (e.g.
        :class:`RateLimitError`, :class:`NetworkError`,
        :class:`AuthenticationError`) propagate **unchanged** so callers keep
        access to attributes like ``retry_after_ms`` and ``status_code``.

        Args:
            endpoint: API endpoint path (forwarded to ``_request``).
            payload: JSON payload for the request.
            error_cls: Exception class to wrap *unexpected* (non-SDK) errors with.
            error_msg: Message prefix for wrapped exceptions.
            method: HTTP method (default ``"POST"``).

        Returns:
            The unwrapped ``result`` dict, or ``{}`` on empty/non-dict.
        """
        try:
            result = await self.call(
                endpoint, payload, error_cls=error_cls, error_msg=error_msg, method=method
            )
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise error_cls(f"{error_msg}: {exc}") from exc

    async def content_get(self, post_id: str) -> dict[str, Any]:
        """Get full content for a post.
        Example:
            ```python
            # Example for content_get
            res = await content_get(post_id='...')
            ```
        """
        payload = {"method": "content.get", "params": {"nid": self._nid, "cid": post_id}}
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to get content for post {post_id}",
        )

    async def get_my_feed(self, **kwargs: Any) -> dict[str, Any]:
        """Get the user's feed.
        Example:
            ```python
            # Example for get_my_feed
            res = await get_my_feed()
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {"method": "network.get_my_feed", "params": {**kwargs, "nid": self._nid}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=FeedError, error_msg="Failed to get feed"
        )

    async def content_create(self, **kwargs: Any) -> dict[str, Any]:
        """Create new content (post or follow-up).
        Example:
            ```python
            # Example for content_create
            res = await content_create()
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "content.create",
            "params": {**kwargs, "nid": self._nid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to create content"
        )

    async def content_update(self, **kwargs: Any) -> dict[str, Any]:
        """Update existing content.
        Example:
            ```python
            # Example for content_update
            res = await content_update()
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "content.update",
            "params": {**kwargs, "nid": self._nid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to update content"
        )

    async def content_mark_resolved(self, post_id: str, resolved: bool = True) -> dict[str, Any]:
        """Mark a post as resolved or unresolved using content.mark_resolved.

        Warning:
            This endpoint is for **follow-up/comment resolution only**.
            For post-level status changes, use :meth:`content_update` with
            ``status="resolved"`` or ``status="active"`` instead — the
            dedicated ``content.mark_resolved`` can return *Invalid content*
            on some live API payloads.

        Args:
            post_id: The comment/follow-up ID to mark resolved.
            resolved: ``True`` to mark resolved, ``False`` to unresolve.

        Returns:
            Raw API response dict.

        Raises:
            ContentError: If the API call fails.

        Example:
            ```python
            from piazza_sdk.adapters.http import RPC

            async def resolve_comment(rpc: RPC, comment_id: str) -> dict:
                \"\"\"Resolve a follow-up comment on a post.\"\"\"
                return await rpc.content_mark_resolved(comment_id, resolved=True)
            ```
        """
        payload = {
            "method": "content.mark_resolved",
            "params": {
                "nid": self._nid,
                "cid": post_id,
                "resolved": resolved,
                "aid": self._last_aid,
            },
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to resolve post {post_id}",
        )

    async def content_duplicate(
        self, duplicate_id: str, master_id: str, message: str = ""
    ) -> dict[str, Any]:
        """Mark a post as a duplicate of another post.
        Example:
            ```python
            # Example for content_duplicate
            res = await content_duplicate(duplicate_id='...', master_id='...', message='...')
            ```
        """
        payload = {
            "method": "content.duplicate",
            "params": {
                "nid": self._nid,
                "cid_dupe": duplicate_id,
                "cid_to": master_id,
                "msg": message,
                "aid": self._last_aid,
            },
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to mark post {duplicate_id} as duplicate of {master_id}",
        )

    async def content_resolve(self, post_id: str) -> dict[str, Any]:
        """Mark a post as resolved via content.mark_resolved.

        Convenience wrapper around :meth:`content_mark_resolved` with
        ``resolved=True``.

        Warning:
            For post-level status changes, prefer :meth:`content_update`
            with ``status="resolved"`` which is more reliable on the live API.
            This RPC method can return *Invalid content* on certain payloads.

        Args:
            post_id: The post/comment ID to resolve.

        Returns:
            Raw API response dict.

        Raises:
            ContentError: If the API call fails.

        Example:
            ```python
            from piazza_sdk.adapters.http import RPC

            async def quick_resolve(rpc: RPC, post_id: str) -> dict:
                \"\"\"Resolve a post using the legacy RPC endpoint.\"\"\"
                return await rpc.content_resolve(post_id)
            ```
        """
        payload = {
            "method": "content.mark_resolved",
            "params": {"nid": self._nid, "cid": post_id, "resolved": True, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to resolve post {post_id}",
        )

    async def content_delete(self, post_id: str) -> dict[str, Any]:
        """Delete a post.
        Example:
            ```python
            # Example for content_delete
            res = await content_delete(post_id='...')
            ```
        """
        payload = {
            "method": "content.delete",
            "params": {"nid": self._nid, "cid": post_id, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to delete post {post_id}",
        )

    async def get_users(self) -> dict[str, Any]:
        """Get all users in the network.

        Uses network.get_all_users (network.get_users requires specific ids).

        Example:
            ```python
            # Example for get_users
            res = await get_users()
            ```
        """
        payload = {"method": "network.get_all_users", "params": {"nid": self._nid}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=UserError, error_msg="Failed to get users"
        )

    async def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search posts by query.
        Example:
            ```python
            # Example for search
            res = await search(query='...')
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "network.search",
            "params": {**kwargs, "nid": self._nid, "query": query},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=SearchError, error_msg="Failed to search"
        )

    async def get_stats(self) -> dict[str, Any]:
        """Get network statistics.

        Uses /main/api instead of /logic/api (confirmed from reference codebase).

        Example:
            ```python
            # Example for get_stats
            res = await get_stats()
            ```
        """
        payload = {"method": "network.get_stats", "params": {"nid": self._nid}}
        return await self._safe_call(
            "/main/api", payload, error_cls=StatisticsError, error_msg="Failed to get stats"
        )

    async def content_answer(
        self,
        post_id: str,
        content: str,
        instructor_answer: bool = False,
        *,
        revision: int = 1,
        anonymous: bool = False,
    ) -> dict[str, Any]:
        """Post an answer to a question.

        Matches Piazza's ``content.answer`` contract (verified against the
        reference implementation): student answers use type ``"s_answer"``
        and instructor answers use ``"i_answer"``.

        Args:
            post_id: The CID of the question to answer.
            content: Answer body (HTML or plain text).
            instructor_answer: Whether this is an official instructor answer.
            revision: Revision number; must exceed the current answer's
                history size when updating an existing answer.
            anonymous: Whether to post anonymously (students only).

        Example:
            ```python
            # Example for content_answer
            res = await content_answer(post_id='...', content='...', instructor_answer='...')
            ```
        """
        payload = {
            "method": "content.answer",
            "params": {
                "nid": self._nid,
                "cid": post_id,
                "content": content,
                "type": "i_answer" if instructor_answer else "s_answer",
                "anonymous": "stud" if anonymous else "no",
                "revision": revision,
                "aid": self._last_aid,
            },
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to answer post {post_id}",
        )

    async def content_pin(self, post_id: str) -> dict[str, Any]:
        """Pin a post using Piazza's dedicated ``content.pin`` method.

        Args:
            post_id: The CID of the post to pin.

        Example:
            ```python
            # Example for content_pin
            res = await content_pin(post_id='...')
            ```
        """
        payload = {
            "method": "content.pin",
            "params": {"nid": self._nid, "cid": post_id, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg=f"Failed to pin post {post_id}"
        )

    async def content_unpin(self, post_id: str) -> dict[str, Any]:
        """Unpin a post using Piazza's dedicated ``content.unpin`` method.

        Args:
            post_id: The CID of the post to unpin.

        Example:
            ```python
            # Example for content_unpin
            res = await content_unpin(post_id='...')
            ```
        """
        payload = {
            "method": "content.unpin",
            "params": {"nid": self._nid, "cid": post_id, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to unpin post {post_id}",
        )

    async def content_upvote(self, post_id: str) -> dict[str, Any]:
        """Upvote a post or answer.
        Example:
            ```python
            # Example for content_upvote
            res = await content_upvote(post_id='...')
            ```
        """
        payload = {
            "method": "content.add_feedback",
            "params": {"nid": self._nid, "cid": post_id, "type": "tag_good", "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to upvote post {post_id}",
        )

    async def content_add_tag(self, post_id: str, tag: str) -> dict[str, Any]:
        """Add a tag to a post.
        Example:
            ```python
            # Example for content_add_tag
            res = await content_add_tag(post_id='...', tag='...')
            ```
        """
        payload = {
            "method": "content.add_tag",
            "params": {"nid": self._nid, "cid": post_id, "tag": tag, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to add tag to post {post_id}",
        )

    async def content_remove_tag(self, post_id: str, tag: str) -> dict[str, Any]:
        """Remove a tag from a post.
        Example:
            ```python
            # Example for content_remove_tag
            res = await content_remove_tag(post_id='...', tag='...')
            ```
        """
        payload = {
            "method": "content.remove_tag",
            "params": {"nid": self._nid, "cid": post_id, "tag": tag, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to remove tag from post {post_id}",
        )

    async def get_instructor_stats(self) -> dict[str, Any]:
        """Get instructor-specific statistics.
        Example:
            ```python
            # Example for get_instructor_stats
            res = await get_instructor_stats()
            ```
        """
        payload = {"method": "network.get_instructor_stats", "params": {"nid": self._nid}}
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=StatisticsError,
            error_msg="Failed to get instructor stats",
        )

    async def get_online_users(self) -> dict[str, Any]:
        """Get currently online users.
        Example:
            ```python
            # Example for get_online_users
            res = await get_online_users()
            ```
        """
        payload = {"method": "network.get_online_users", "params": {"nid": self._nid}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=UserError, error_msg="Failed to get online users"
        )

    async def get_user_preferences(self) -> dict[str, Any]:
        """Get the current user's preferences for this network.

        Returns an empty dict only when the method genuinely does not exist
        for this network (``NotFoundError``). All other SDK errors —
        including authentication and rate-limit failures — propagate so
        they are not silently misread as "no preferences".

        Example:
            ```python
            # Example for get_user_preferences
            res = await get_user_preferences()
            ```
        """
        payload = {"method": "network.get_user_preferences", "params": {"nid": self._nid}}
        try:
            return await self._safe_call(
                "/logic/api",
                payload,
                error_cls=UserError,
                error_msg="Failed to get user preferences",
            )
        except NotFoundError:
            logger.info("network.get_user_preferences not available; returning empty prefs")
            return {}

    async def update_user_preferences(self, preferences: dict[str, Any]) -> None:
        """Update the current user's preferences for this network.

        Args:
            preferences: Dictionary of preference fields to update.

        Example:
            ```python
            # Example for update_user_preferences
            res = await update_user_preferences(preferences='...')
            ```
        """
        blocked = _BLOCKED_KEYS & preferences.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "network.update_user_preferences",
            "params": {**preferences, "nid": self._nid, "aid": self._last_aid},
        }
        try:
            await self._request("POST", "/logic/api", json=payload)
        except PiazzaSDKError:
            # Typed SDK errors propagate untouched so callers keep
            # attributes like status_code and retry_after_ms.
            raise
        except Exception as exc:
            raise UserError(f"Failed to update user preferences: {exc}") from exc

    async def user_status(self) -> dict[str, Any]:
        """Get the global user status (contains enrolled classes, etc.).
        Example:
            ```python
            # Example for user_status
            res = await user_status()
            ```
        """
        payload = {"method": "user.status", "params": {}}
        return await self._safe_call(
            "/main/api", payload, error_cls=UserError, error_msg="Failed to get user status"
        )

    async def mark_as_unread(self, post_id: str) -> dict[str, Any]:
        """Mark a post as unread for the current user.

        Args:
            post_id: The CID of the post to mark unread.

        Example:
            ```python
            # Example for mark_as_unread
            res = await mark_as_unread(post_id='...')
            ```
        """
        payload = {
            "method": "content.mark_unread",
            "params": {"nid": self._nid, "cid": post_id, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to mark post {post_id} as unread",
        )

    async def add_folder(self, folder_name: str) -> dict[str, Any]:
        """Add a new folder to the network.

        Args:
            folder_name: Name of the folder to create.

        Example:
            ```python
            # Example for add_folder
            res = await add_folder(folder_name='...')
            ```
        """
        payload = {
            "method": "network.add_folder",
            "params": {"nid": self._nid, "name": folder_name, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to create folder {folder_name!r}",
        )

    async def add_badge(self, post_id: str, badge_type: str = "good_answer") -> dict[str, Any]:
        """Add an instructor badge (e.g. green checkmark) to a post.

        Args:
            post_id: The CID of the post to badge.
            badge_type: Badge type string (default ``"good_answer"``).

        Example:
            ```python
            # Example for add_badge
            res = await add_badge(post_id='...', badge_type='...')
            ```
        """
        payload = {
            "method": "content.add_badge",
            "params": {"nid": self._nid, "cid": post_id, "type": badge_type, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to add badge to post {post_id}",
        )

    async def network_update(self, **kwargs: Any) -> dict[str, Any]:
        """Update network-level settings (e.g., office hours, general info).
        Example:
            ```python
            # Example for network_update
            res = await network_update()
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "network.update",
            "params": {**kwargs, "id": self._nid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=NetworkError,
            error_msg="Failed to update network settings",
        )

    async def asset_get_upload_url(self, filename: str) -> dict[str, Any]:
        """Get a pre-signed URL for uploading an asset.

        Args:
            filename: Name of the file to upload.

        Returns:
            Dictionary with upload URL and asset metadata.

        Example:
            ```python
            # Example for asset_get_upload_url
            res = await asset_get_upload_url(filename='...')
            ```
        """
        payload = {
            "method": "asset.get_upload_url",
            "params": {"nid": self._nid, "filename": filename, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=UploadError,
            error_msg=f"Failed to get upload URL for {filename}",
        )

    async def content_save_draft(
        self, subject: str, content: str, post_type: PostType | str = "question", **kwargs: Any
    ) -> dict[str, Any]:
        """Save a post as a draft.

        Args:
            subject: Post title/subject.
            content: Post content (HTML or plain text).
            post_type: Type of post (question, note, poll).

        Returns:
            Dictionary with the draft post data.

        Example:
            ```python
            # Example for content_save_draft
            res = await content_save_draft(subject='...', content='...', post_type='...')
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "content.save_draft",
            "params": {
                **kwargs,
                "nid": self._nid,
                "subject": subject,
                "content": content,
                "type": post_type,
                "has_stale_thread": True,
                "aid": self._last_aid,
            },
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to save draft"
        )

    async def network_save_draft(self, **kwargs: Any) -> Any:
        """Save a scheduling draft via ``network.save_draft``.

        Distinct from :meth:`content_save_draft` (the UI's per-post draft
        store): this network-level endpoint returns the created draft ID
        as a **bare string** result, which ``content.create`` accepts
        alongside ``config.schedule_later``/``schedule_later_time`` to
        queue a scheduled post.

        Args:
            **kwargs: Draft parameters (e.g. the ``draft`` structure).

        Returns:
            The draft ID (bare string) on success.

        Example:
            ```python
            # Example for network_save_draft
            res = await network_save_draft(**kwargs)
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "network.save_draft",
            "params": {**kwargs, "nid": self._nid, "aid": self._last_aid},
        }
        # ``call`` (not ``_safe_call``) — the endpoint returns the draft
        # ID as a *bare string* result which ``_safe_call`` would coerce
        # to ``{}``.
        return await self.call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to save draft"
        )

    async def content_get_similar(self, post_id: str, **kwargs: Any) -> dict[str, Any]:
        """Get similar posts for a given post.

        Args:
            post_id: The CID of the post to find similar content for.

        Returns:
            Dictionary with similar posts data.

        Example:
            ```python
            # Example for content_get_similar
            res = await content_get_similar(post_id='...')
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "content.get_similar",
            "params": {**kwargs, "cid": post_id, "nid": self._nid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to get similar posts for {post_id}",
        )

    async def get_user_profile(self) -> dict[str, Any]:
        """Get the authenticated user's profile via JSON-RPC.

        Returns:
            Dictionary with user profile data including name, email,
            school, roles, skills, and enrolled classes.

        Example:
            ```python
            # Example for get_user_profile
            res = await get_user_profile()
            ```
        """
        payload = {"method": "user_profile.get_profile", "params": {}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=UserError, error_msg="Failed to get user profile"
        )

    async def get_unread_message_count(self) -> int:
        """Get the count of unread messages (heartbeat endpoint).

        Returns:
            Integer count of unread direct messages.

        Example:
            ```python
            # Example for get_unread_message_count
            res = await get_unread_message_count()
            ```
        """
        payload = {"method": "memo.get_unread_message_count", "params": {}}
        # ``call`` (not ``_safe_call``) so scalar/list results are preserved.
        result = await self.call(
            "/logic/api", payload, error_cls=PiazzaSDKError, error_msg="Failed to get unread count"
        )
        if isinstance(result, dict):
            value: Any = result.get("count", result.get("unread_count", 0))
        elif isinstance(result, (int, float)) and not isinstance(result, bool):
            value = result
        else:
            value = 0
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise PiazzaSDKError(f"Unexpected unread-count payload: {result!r}") from exc

    async def get_class_profile(self) -> dict[str, Any]:
        """Get course-specific profile and behavioral settings.

        Distinct from ``user_profile.get_profile`` — this returns
        grading config, folder structure, anonymous posting rules,
        endorsement settings, and LTI integration hooks for the
        current network.

        Returns:
            Dictionary with class profile configuration.

        Example:
            ```python
            # Example for get_class_profile
            res = await get_class_profile()
            ```
        """
        payload = {"method": "class_profile.get_profile", "params": {"nid": self._nid}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to get class profile"
        )

    async def set_user_settings(self, settings: dict[str, Any]) -> dict[str, Any]:
        """Persist local UI state to the backend.

        Saves settings like collapsed folders, dark mode preference,
        and other UI state. Firing occasional updates helps the
        session appear human-like.

        Args:
            settings: Dictionary of UI settings to persist
                      (e.g. ``{"hw1_folder_collapsed": true}``).

        Returns:
            Response dictionary from the server.

        Example:
            ```python
            # Example for set_user_settings
            res = await set_user_settings(settings='...')
            ```
        """
        payload = {"method": "user.set_settings", "params": {"settings": settings}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to set user settings"
        )

    async def content_bookmark(self, cid: str) -> dict[str, Any]:
        payload = {
            "method": "content.bookmark",
            "params": {"nid": self._nid, "cid": cid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to bookmark"
        )

    async def content_unbookmark(self, cid: str) -> dict[str, Any]:
        payload = {
            "method": "content.unbookmark",
            "params": {"nid": self._nid, "cid": cid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to unbookmark"
        )

    async def content_mark_favorite(self, cid: str) -> dict[str, Any]:
        payload = {
            "method": "content.mark_favorite",
            "params": {"nid": self._nid, "cid": cid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to mark favorite"
        )

    async def content_mark_unfavorite(self, cid: str) -> dict[str, Any]:
        payload = {
            "method": "content.mark_unfavorite",
            "params": {"nid": self._nid, "cid": cid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to mark unfavorite"
        )

    async def content_view(self, cid: str) -> dict[str, Any]:
        payload = {
            "method": "content.view",
            "params": {"nid": self._nid, "cid": cid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to view content"
        )

    async def content_edit(self, cid: str, type: str, **kwargs: Any) -> dict[str, Any]:
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {
            "method": "content.edit",
            "params": {**kwargs, "nid": self._nid, "cid": cid, "type": type, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to edit content"
        )

    async def content_cancel_edit(self, nid: str | None = None) -> dict[str, Any]:
        payload = {
            "method": "content.cancel_edit",
            "params": {"nid": nid if nid is not None else self._nid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to cancel edit"
        )

    async def content_remove_feedback(self, cid: str, type: str) -> dict[str, Any]:
        payload = {
            "method": "content.remove_feedback",
            "params": {"nid": self._nid, "cid": cid, "type": type, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to remove feedback"
        )

    async def content_auto_save(
        self, cid: str, type: str, body: str, revision: int, editor: str
    ) -> dict[str, Any]:
        payload = {
            "method": "content.auto_save",
            "params": {
                "nid": self._nid,
                "cid": cid,
                "type": type,
                "body": body,
                "revision": revision,
                "editor": editor,
                "network_id": self._nid,
                "aid": self._last_aid,
            },
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to auto save"
        )

    async def network_del_item(self, cid: str) -> dict[str, Any]:
        payload = {
            "method": "network.del_item",
            "params": {"nid": self._nid, "cid": cid, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=NetworkError,
            error_msg="Failed to delete item from network",
        )

    async def network_filter_feed(
        self, sort: str = "updated_desc", unread: int = 1, hidden: str = "both"
    ) -> dict[str, Any]:
        payload = {
            "method": "network.filter_feed",
            "params": {"nid": self._nid, "sort": sort, "unread": unread, "hidden": hidden},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=NetworkError, error_msg="Failed to filter feed"
        )

    async def network_get_users(self, ids: list[str]) -> dict[str, Any]:
        payload = {
            "method": "network.get_users",
            "params": {"nid": self._nid, "ids": ids, "aid": self._last_aid},
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=NetworkError, error_msg="Failed to get specific users"
        )

    async def user_set(self, stat: str, val: Any) -> dict[str, Any]:
        payload = {"method": "user.set", "params": {"stat": stat, "val": val}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=UserError, error_msg="Failed to set user setting"
        )

    async def user_unset(self, stat: str) -> dict[str, Any]:
        payload = {"method": "user.unset", "params": {"stat": stat}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=UserError, error_msg="Failed to unset user setting"
        )

    async def user_update(self, **kwargs: Any) -> dict[str, Any]:
        """Update the global user record via ``user.update``.

        This is a *global* (non-network-scoped) endpoint: the payload is
        forwarded verbatim with no ``nid``/``aid`` injection, matching
        the reference wire contract ``{"email_prefs": {...}}``.

        Args:
            **kwargs: Fields of the user record to update (e.g.
                ``email_prefs`` mapping network ID -> preference dict).

        Returns:
            Raw API response dictionary.

        Example:
            ```python
            # Example for user_update
            res = await user_update(**kwargs)
            ```
        """
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {"method": "user.update", "params": kwargs}
        return await self._safe_call(
            "/logic/api", payload, error_cls=UserError, error_msg="Failed to update user"
        )

    async def company_event_get_my_events_info(self) -> dict[str, Any]:
        payload = {"method": "company_event.get_my_events_info", "params": {}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=PiazzaSDKError, error_msg="Failed to get events info"
        )

    async def generic_page_event(self, type: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"method": "generic.page_event", "params": {"type": type, **kwargs}}
        return await self._safe_call(
            "/logic/api", payload, error_cls=PiazzaSDKError, error_msg="Failed to send page event"
        )

    async def generic_sanitize_html(self, **kwargs: str) -> dict[str, Any]:
        payload = {"method": "generic.sanitize_html", "params": kwargs}
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to sanitize html"
        )

    async def memo_get_unread_message_count(self) -> dict[str, Any]:
        payload = {"method": "memo.get_unread_message_count", "params": {}}
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=UserError,
            error_msg="Failed to get unread message count",
        )
