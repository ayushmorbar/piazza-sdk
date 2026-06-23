"""Search domain operations for Piazza SDK.

Provides standalone functions for content search.
"""

from __future__ import annotations

__all__ = ["search"]

from typing import TYPE_CHECKING, Any

from piazza_sdk.exceptions import PiazzaSDKError, SearchError, ValidationError
from piazza_sdk.models.feed import Feed, FeedItem

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager


async def search(
    rpc: RPC, *, session: SessionStateManager | None = None, query: str, **kwargs: Any
) -> Feed:
    """Search posts by query string.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        query: Search query.
        **kwargs: Additional search parameters.

    Returns:
        Feed model with matching posts.

    Raises:
        ValidationError: If query is empty.
        SearchError: If search execution or parsing fails.
        PiazzaSDKError: On unexpected errors.
    """
    if not query or not query.strip():
        raise ValidationError("query must be non-empty")
    try:
        raw = await rpc.search(query, **kwargs)
        items = [FeedItem(**item) for item in raw.get("feed", [])]
        return Feed(feed=items, total=raw.get("total", len(items)))
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise SearchError(f"Failed to search: {exc}") from exc
