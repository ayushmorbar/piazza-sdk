"""HTTP RPC layer for Piazza SDK.

Provides the low-level RPC client that handles HTTP communication
with Piazza's internal API, including retry logic, rate limiting,
and error mapping.
"""

from __future__ import annotations

import logging
from typing import Any

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
        return RateLimitError(
            f"Rate limited: {status}",
            retry_after_ms=int(retry_after) * 1000 if retry_after else None,
        )
    return PiazzaSDKError(f"HTTP error {status}")


class RPC:
    """Low-level RPC client for Piazza's internal API.

    Handles HTTP requests with retry logic, error mapping, and
    response parsing.
    """

    def __init__(self, client: httpx.AsyncClient, base_url: str, network_id: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._nid = network_id

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _request(self, method: str, endpoint: str, **kwargs: Any) -> Any:
        """Make an HTTP request with retry and error handling."""
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
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
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

    async def content_get(self, post_id: str) -> dict[str, Any]:
        """Get full content for a post."""
        payload = {"action": "content.get", "cid": post_id, "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/content_get", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to get content for post {post_id}: {exc}") from exc

    async def get_my_feed(self, **kwargs: Any) -> dict[str, Any]:
        """Get the user's feed."""
        payload = {"action": "get_my_feed", "nid": self._nid, **kwargs}
        try:
            result = await self._request("POST", "/class/api/get_my_feed", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise FeedError(f"Failed to get feed: {exc}") from exc

    async def content_create(self, **kwargs: Any) -> dict[str, Any]:
        """Create new content (post or follow-up)."""
        payload = {"action": "content.create", "nid": self._nid, **kwargs}
        try:
            result = await self._request("POST", "/class/api/content_create", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to create content: {exc}") from exc

    async def content_update(self, **kwargs: Any) -> dict[str, Any]:
        """Update existing content."""
        payload = {"action": "content.update", "nid": self._nid, **kwargs}
        try:
            result = await self._request("POST", "/class/api/content_update", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to update content: {exc}") from exc

    async def content_delete(self, post_id: str) -> dict[str, Any]:
        """Delete a post."""
        payload = {"action": "content.delete", "cid": post_id, "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/content_delete", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to delete post {post_id}: {exc}") from exc

    async def get_users(self) -> dict[str, Any]:
        """Get users in the network."""
        payload = {"action": "get_users", "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/get_users", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise UserError(f"Failed to get users: {exc}") from exc

    async def search(self, query: str, **kwargs: Any) -> dict[str, Any]:
        """Search posts by query."""
        payload = {"action": "search", "nid": self._nid, "query": query, **kwargs}
        try:
            result = await self._request("POST", "/class/api/search", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise SearchError(f"Failed to search: {exc}") from exc

    async def get_stats(self) -> dict[str, Any]:
        """Get network statistics."""
        payload = {"action": "get_stats", "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/get_stats", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise StatisticsError(f"Failed to get stats: {exc}") from exc

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
        try:
            result = await self._request("POST", "/class/api/content_answer", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to answer post {post_id}: {exc}") from exc

    async def content_upvote(self, post_id: str) -> dict[str, Any]:
        """Upvote a post or answer."""
        payload = {"action": "content.upvote", "cid": post_id, "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/content_upvote", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to upvote post {post_id}: {exc}") from exc

    async def content_add_tag(self, post_id: str, tag: str) -> dict[str, Any]:
        """Add a tag to a post."""
        payload = {"action": "content.add_tag", "cid": post_id, "nid": self._nid, "tag": tag}
        try:
            result = await self._request("POST", "/class/api/content_add_tag", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to add tag to post {post_id}: {exc}") from exc

    async def content_remove_tag(self, post_id: str, tag: str) -> dict[str, Any]:
        """Remove a tag from a post."""
        payload = {"action": "content.remove_tag", "cid": post_id, "nid": self._nid, "tag": tag}
        try:
            result = await self._request("POST", "/class/api/content_remove_tag", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to remove tag from post {post_id}: {exc}") from exc

    async def get_instructor_stats(self) -> dict[str, Any]:
        """Get instructor-specific statistics."""
        payload = {"action": "get_instructor_stats", "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/get_instructor_stats", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise StatisticsError(f"Failed to get instructor stats: {exc}") from exc

    async def get_online_users(self) -> dict[str, Any]:
        """Get currently online users."""
        payload = {"action": "get_online_users", "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/get_online_users", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise UserError(f"Failed to get online users: {exc}") from exc

    async def get_user_preferences(self) -> dict[str, Any]:
        """Get the current user's preferences for this network."""
        payload = {"action": "get_user_preferences", "nid": self._nid}
        try:
            result = await self._request("POST", "/class/api/get_user_preferences", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise UserError(f"Failed to get user preferences: {exc}") from exc

    async def update_user_preferences(self, preferences: dict[str, Any]) -> None:
        """Update the current user's preferences for this network.

        Args:
            preferences: Dictionary of preference fields to update.
        """
        payload = {"action": "update_user_preferences", "nid": self._nid, **preferences}
        try:
            await self._request("POST", "/class/api/update_user_preferences", json=payload)
        except PiazzaSDKError as exc:
            raise UserError(f"Failed to update user preferences: {exc}") from exc

    async def mark_as_unread(self, post_id: str) -> dict[str, Any]:
        """Mark a post as unread for the current user.

        Args:
            post_id: The CID of the post to mark unread.
        """
        payload = {
            "method": "content.mark_unread",
            "params": {"nid": self._nid, "cid": post_id},
        }
        try:
            result = await self._request("POST", "/logic/api", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to mark post {post_id} as unread: {exc}") from exc

    async def add_folder(self, folder_name: str) -> dict[str, Any]:
        """Add a new folder to the network.

        Args:
            folder_name: Name of the folder to create.
        """
        payload = {
            "method": "network.add_folder",
            "params": {"nid": self._nid, "name": folder_name},
        }
        try:
            result = await self._request("POST", "/logic/api", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to create folder {folder_name!r}: {exc}") from exc

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
        try:
            result = await self._request("POST", "/logic/api", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to add badge to post {post_id}: {exc}") from exc

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
        try:
            result = await self._request("POST", "/logic/api", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise UploadError(f"Failed to get upload URL for {filename}: {exc}") from exc

    async def content_save_draft(
        self, subject: str, content: str, post_type: str = "question", **kwargs: Any
    ) -> dict[str, Any]:
        """Save a post as a draft.

        Args:
            subject: Post title/subject.
            content: Post content (HTML or plain text).
            post_type: Type of post (question, note, poll).

        Returns:
            Dictionary with the draft post data.
        """
        payload = {
            "method": "content.save_draft",
            "params": {
                "nid": self._nid,
                "subject": subject,
                "content": content,
                "type": post_type,
                "has_stale_thread": True,
                **kwargs,
            },
        }
        try:
            result = await self._request("POST", "/logic/api", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(f"Failed to save draft: {exc}") from exc

    async def content_get_similar(self, post_id: str, **kwargs: Any) -> dict[str, Any]:
        """Get similar posts for a given post.

        Args:
            post_id: The CID of the post to find similar content for.

        Returns:
            Dictionary with similar posts data.
        """
        payload = {
            "method": "content.get_similar",
            "params": {
                "cid": post_id,
                "nid": self._nid,
                **kwargs,
            },
        }
        try:
            result = await self._request("POST", "/logic/api", json=payload)
            return result if isinstance(result, dict) else {}
        except PiazzaSDKError as exc:
            raise ContentError(
                f"Failed to get similar posts for {post_id}: {exc}"
            ) from exc
