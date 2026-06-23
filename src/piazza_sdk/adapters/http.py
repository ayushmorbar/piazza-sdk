"""HTTP RPC layer for Piazza SDK.

Provides the low-level RPC client that handles HTTP communication
with Piazza's internal API, including retry logic, rate limiting,
and error mapping.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, Any, TypeVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

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
    from collections.abc import Callable

    from piazza_sdk.models.enums import PostType

# Keys that must never be overridden by caller-supplied kwargs.
_BLOCKED_KEYS = frozenset({"action", "method", "nid", "params"})


class _AuthRetryNeededError(Exception):
    """Raised inside _request to trigger a single retry after a token refresh."""


def _map_http_error(exc: httpx.HTTPStatusError) -> PiazzaSDKError:
    """Map an HTTP status error to an SDK exception."""
    status = exc.response.status_code
    if status == 401:
        return AuthenticationError(f"Unauthorized: {status}")
    if status == 403:
        return PermissionError(f"Forbidden: {status}")
    if status == 404:
        return NotFoundError(f"Not found: {status}")
    if status == 429:
        retry_after = exc.response.headers.get("Retry-After")
        retry_after_ms = None
        if retry_after:
            with contextlib.suppress(ValueError):
                raw = int(retry_after) * 1000
                retry_after_ms = max(0, min(raw, 30_000))
        return RateLimitError(f"Rate limited: {status}", retry_after_ms=retry_after_ms)
    return PiazzaSDKError(f"HTTP error {status}")


class RPC:
    """Low-level RPC client for Piazza's internal API.

    Handles HTTP requests with retry logic, error mapping, and
    response parsing.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        network_id: str,
        *,
        on_auth_error: Callable[[], Any] | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._nid = network_id
        self._on_auth_error = on_auth_error

    _RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

    @retry(
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, _AuthRetryNeededError)
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Make an HTTP request with retry and error handling.

        Retries on:
        - Connection and timeout errors (3 attempts)
        - HTTP 429 / 5xx status codes (mapped to retryable SDK exceptions)
        - HTTP 401 after a single session-refresh attempt
        """
        url = f"{self._base_url}/{endpoint.lstrip('/')}"
        logger.debug("RPC %s %s", method, url)
        try:
            response = await self._client.request(method, url, **kwargs)
            logger.debug(
                "RPC %s %s -> %d (%.1fms)",
                method,
                url,
                response.status_code,
                response.elapsed.total_seconds() * 1000,
            )
            # Let tenacity retry on transient server errors
            if response.status_code in self._RETRYABLE_STATUS:
                exc = httpx.HTTPStatusError(
                    f"{response.status_code}", request=response.request, response=response
                )
                raise _map_http_error(exc) from exc
            response.raise_for_status()
            return response.json()
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

    async def _safe_call(
        self,
        endpoint: str,
        payload: dict[str, Any],
        *,
        error_cls: type[PiazzaSDKError] = PiazzaSDKError,
        error_msg: str = "RPC call failed",
        method: str = "POST",
    ) -> dict[str, Any]:
        """Execute an RPC request with standardized error handling.

        Wraps ``_request`` with two behaviors that are otherwise copy-pasted
        across every public method:

        1. Converts non-dict JSON responses to ``{}`` (avoids silent data loss
           when Piazza returns a list or scalar).
        2. Re-raises any ``PiazzaSDKError`` subclass as *error_cls* with a
           human-readable *error_msg*.

        Args:
            endpoint: API endpoint path (forwarded to ``_request``).
            payload: JSON payload for the request.
            error_cls: Exception class to wrap errors with.
            error_msg: Message prefix for the wrapped exception.
            method: HTTP method (default ``"POST"``).

        Returns:
            Response dict or ``{}`` if the response is not a dict.
        """
        try:
            result = await self._request(method, endpoint, json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise error_cls(f"{error_msg}: {exc}") from exc

    async def content_get(self, post_id: str) -> dict[str, Any]:
        """Get full content for a post."""
        payload = {"action": "content.get", "cid": post_id, "nid": self._nid}
        return await self._safe_call(
            "/class/api/content_get",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to get content for post {post_id}",
        )

    async def get_my_feed(self, **kwargs: Any) -> dict[str, Any]:
        """Get the user's feed."""
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {**kwargs, "action": "get_my_feed", "nid": self._nid}
        return await self._safe_call(
            "/class/api/get_my_feed", payload, error_cls=FeedError, error_msg="Failed to get feed"
        )

    async def content_create(self, **kwargs: Any) -> dict[str, Any]:
        """Create new content (post or follow-up)."""
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {**kwargs, "action": "content.create", "nid": self._nid}
        return await self._safe_call(
            "/class/api/content_create",
            payload,
            error_cls=ContentError,
            error_msg="Failed to create content",
        )

    async def content_update(self, **kwargs: Any) -> dict[str, Any]:
        """Update existing content."""
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {**kwargs, "action": "content.update", "nid": self._nid}
        return await self._safe_call(
            "/class/api/content_update",
            payload,
            error_cls=ContentError,
            error_msg="Failed to update content",
        )

    async def content_delete(self, post_id: str) -> dict[str, Any]:
        """Delete a post."""
        payload = {"action": "content.delete", "cid": post_id, "nid": self._nid}
        return await self._safe_call(
            "/class/api/content_delete",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to delete post {post_id}",
        )

    async def get_users(self) -> dict[str, Any]:
        """Get users in the network."""
        payload = {"action": "get_users", "nid": self._nid}
        return await self._safe_call(
            "/class/api/get_users", payload, error_cls=UserError, error_msg="Failed to get users"
        )

    async def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search posts by query."""
        blocked = _BLOCKED_KEYS & kwargs.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {**kwargs, "action": "search", "nid": self._nid, "query": query}
        return await self._safe_call(
            "/class/api/search", payload, error_cls=SearchError, error_msg="Failed to search"
        )

    async def get_stats(self) -> dict[str, Any]:
        """Get network statistics."""
        payload = {"action": "get_stats", "nid": self._nid}
        return await self._safe_call(
            "/class/api/get_stats",
            payload,
            error_cls=StatisticsError,
            error_msg="Failed to get stats",
        )

    async def content_answer(
        self, post_id: str, content: str, instructor_answer: bool = False
    ) -> dict[str, Any]:
        """Post an answer to a question."""
        payload = {
            "action": "content.answer",
            "cid": post_id,
            "nid": self._nid,
            "content": content,
            "instructor_answer": instructor_answer,
        }
        return await self._safe_call(
            "/class/api/content_answer",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to answer post {post_id}",
        )

    async def content_upvote(self, post_id: str) -> dict[str, Any]:
        """Upvote a post or answer."""
        payload = {"action": "content.upvote", "cid": post_id, "nid": self._nid}
        return await self._safe_call(
            "/class/api/content_upvote",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to upvote post {post_id}",
        )

    async def content_add_tag(self, post_id: str, tag: str) -> dict[str, Any]:
        """Add a tag to a post."""
        payload = {"action": "content.add_tag", "cid": post_id, "nid": self._nid, "tag": tag}
        return await self._safe_call(
            "/class/api/content_add_tag",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to add tag to post {post_id}",
        )

    async def content_remove_tag(self, post_id: str, tag: str) -> dict[str, Any]:
        """Remove a tag from a post."""
        payload = {"action": "content.remove_tag", "cid": post_id, "nid": self._nid, "tag": tag}
        return await self._safe_call(
            "/class/api/content_remove_tag",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to remove tag from post {post_id}",
        )

    async def get_instructor_stats(self) -> dict[str, Any]:
        """Get instructor-specific statistics."""
        payload = {"action": "get_instructor_stats", "nid": self._nid}
        return await self._safe_call(
            "/class/api/get_instructor_stats",
            payload,
            error_cls=StatisticsError,
            error_msg="Failed to get instructor stats",
        )

    async def get_online_users(self) -> dict[str, Any]:
        """Get currently online users."""
        payload = {"action": "get_online_users", "nid": self._nid}
        return await self._safe_call(
            "/class/api/get_online_users",
            payload,
            error_cls=UserError,
            error_msg="Failed to get online users",
        )

    async def get_user_preferences(self) -> dict[str, Any]:
        """Get the current user's preferences for this network."""
        payload = {"action": "get_user_preferences", "nid": self._nid}
        return await self._safe_call(
            "/class/api/get_user_preferences",
            payload,
            error_cls=UserError,
            error_msg="Failed to get user preferences",
        )

    async def update_user_preferences(self, preferences: dict[str, Any]) -> None:
        """Update the current user's preferences for this network.

        Args:
            preferences: Dictionary of preference fields to update.
        """
        blocked = _BLOCKED_KEYS & preferences.keys()
        if blocked:
            raise PiazzaSDKError(f"Reserved keys cannot be overridden: {blocked}")
        payload = {**preferences, "action": "update_user_preferences", "nid": self._nid}
        try:
            await self._request("POST", "/class/api/update_user_preferences", json=payload)
        except PiazzaSDKError as exc:
            raise UserError(f"Failed to update user preferences: {exc}") from exc

    async def mark_as_unread(self, post_id: str) -> dict[str, Any]:
        """Mark a post as unread for the current user.

        Args:
            post_id: The CID of the post to mark unread.
        """
        payload = {"method": "content.mark_unread", "params": {"nid": self._nid, "cid": post_id}}
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
        """
        payload = {
            "method": "network.add_folder",
            "params": {"nid": self._nid, "name": folder_name},
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
        """
        payload = {
            "method": "content.add_badge",
            "params": {"nid": self._nid, "cid": post_id, "type": badge_type},
        }
        return await self._safe_call(
            "/logic/api",
            payload,
            error_cls=ContentError,
            error_msg=f"Failed to add badge to post {post_id}",
        )

    async def asset_get_upload_url(self, filename: str) -> dict[str, Any]:
        """Get a pre-signed URL for uploading an asset.

        Args:
            filename: Name of the file to upload.

        Returns:
            Dictionary with upload URL and asset metadata.
        """
        payload = {
            "method": "asset.get_upload_url",
            "params": {"nid": self._nid, "filename": filename},
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
            },
        }
        return await self._safe_call(
            "/logic/api", payload, error_cls=ContentError, error_msg="Failed to save draft"
        )

    async def content_get_similar(self, post_id: str, **kwargs: Any) -> dict[str, Any]:
        """Get similar posts for a given post.

        Args:
            post_id: The CID of the post to find similar content for.

        Returns:
            Dictionary with similar posts data.
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
