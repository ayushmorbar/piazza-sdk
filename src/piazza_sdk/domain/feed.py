"""Feed domain operations for Piazza SDK.

Provides standalone functions for feed retrieval and filtering.
"""

from __future__ import annotations

__all__ = ["get_feed", "get_similar_posts"]

import base64
import binascii
import json
import logging
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError as PydanticValidationError

from piazza_sdk.exceptions import FeedError, PiazzaSDKError
from piazza_sdk.models.feed import Feed, FeedItem

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager

logger = logging.getLogger(__name__)


def _decode_feed_response(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Decode feed response, handling Base64-encoded payloads.

    Piazza's ``network.get_my_feed`` may return the feed as a Base64-encoded
    JSON string for bandwidth optimization.  This function detects and decodes
    such responses, falling back to standard dict extraction.
    """
    feed = raw.get("feed", [])
    if isinstance(feed, str):
        try:
            decoded = base64.b64decode(feed).decode("utf-8")
            parsed = json.loads(decoded)
            if isinstance(parsed, dict):
                items = parsed.get("feed", [])
                return items if isinstance(items, list) else []
            if isinstance(parsed, list):
                return parsed
        except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("Base64 feed decode failed, treating as raw")
    if isinstance(feed, list):
        return feed
    return []


async def get_feed(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    limit: int = 50,
    offset: int = 0,
    **kwargs: Any,
) -> Feed:
    """Get the feed for the current network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        limit: Maximum number of feed items to return.
        offset: Number of feed items to skip.
        **kwargs: Additional filter parameters (folder, instructor_only, etc.).

    Returns:
        Feed model containing feed items and metadata.

    Raises:
        FeedError: If feed retrieval fails.
        PiazzaSDKError: On unexpected errors.
    """
    try:
        raw = await rpc.get_my_feed(limit=limit, offset=offset, **kwargs)
        feed_data = _decode_feed_response(raw)
        items = [FeedItem.model_validate(item) for item in feed_data]
        return Feed(
            feed=items,
            total=raw.get("total", len(items)),
            page=raw.get("page", 1),
            page_size=raw.get("page_size", limit),
        )
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise FeedError(f"Failed to retrieve feed: {exc}") from exc


async def get_similar_posts(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> list[FeedItem]:
    """Get posts similar to the specified post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post to find similar posts for.

    Returns:
        List of similar FeedItem objects. Items that fail validation
        are silently skipped.

    Raises:
        NotFoundError: If the specified post does not exist.
        PiazzaSDKError: On unexpected errors.
    """
    try:
        raw: dict[str, Any] = await rpc.content_get_similar(post_id)
        raw_items: list[dict[str, Any]] = raw.get("similar_posts", [])
        results: list[FeedItem] = []
        for item in raw_items:
            try:
                results.append(FeedItem.model_validate(item))
            except PydanticValidationError:
                continue
        return results
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise FeedError(f"Failed to get similar posts for {post_id}: {exc}") from exc
