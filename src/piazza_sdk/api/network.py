"""Network class for Piazza SDK.

Provides the Network class that handles per-class operations:
feed retrieval, post management, user queries, and search.

Implements the facade pattern: each method delegates to a
domain function that owns the business logic, while Network
manages session lifecycle and cross-cutting concerns.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from piazza_sdk.domain.feed import get_feed as _domain_get_feed
from piazza_sdk.domain.feed import get_similar_posts as _domain_get_similar_posts
from piazza_sdk.domain.posts import add_followup as _domain_add_followup
from piazza_sdk.domain.posts import add_tag as _domain_add_tag
from piazza_sdk.domain.posts import answer_post as _domain_answer_post
from piazza_sdk.domain.posts import create_folder as _domain_create_folder
from piazza_sdk.domain.posts import create_post as _domain_create_post
from piazza_sdk.domain.posts import delete_post as _domain_delete_post
from piazza_sdk.domain.posts import endorse as _domain_endorse
from piazza_sdk.domain.posts import mark_as_unread as _domain_mark_as_unread
from piazza_sdk.domain.posts import remove_tag as _domain_remove_tag
from piazza_sdk.domain.posts import resolve_post as _domain_resolve_post
from piazza_sdk.domain.posts import save_draft as _domain_save_draft
from piazza_sdk.domain.posts import upload_asset as _domain_upload_asset
from piazza_sdk.domain.preferences import get_preferences as _domain_get_preferences
from piazza_sdk.domain.preferences import update_preferences as _domain_update_preferences
from piazza_sdk.domain.search import search as _domain_search
from piazza_sdk.domain.statistics import get_statistics as _domain_get_statistics
from piazza_sdk.domain.users import get_all_users as _domain_get_all_users
from piazza_sdk.domain.users import get_instructor_stats as _domain_get_instructor_stats
from piazza_sdk.domain.users import get_online_users as _domain_get_online_users
from piazza_sdk.exceptions import FeedError, NotFoundError, PiazzaSDKError, ValidationError
from piazza_sdk.models.feed import Feed, FeedFilter, FeedItem, FolderFilter
from piazza_sdk.models.network import HallOfFameItem, Statistics
from piazza_sdk.models.post import AssetUploadResponse, Post, PostCreatedResponse, PublishingOptions

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager
    from piazza_sdk.models.enums import PostType
    from piazza_sdk.models.user import User, UserPreferences

_HOF_FIELDS = {"uid", "nr", "time", "text", "when"}


class Network:
    """Per-class operations for a Piazza network.

    Provides methods for feed, posts, users, search, and statistics.
    Instantiated via Piazza.network(nid).
    """

    def __init__(self, rpc: RPC, nid: str, session: SessionStateManager | None = None) -> None:
        self._rpc = rpc
        self._nid = nid
        self._session = session

    async def _ensure_session(self) -> None:
        """Refresh the session if expired."""
        if self._session is not None and self._session.needs_refresh:
            await self._session.refresh()

    # ── Feed ──────────────────────────────────────────────────────────

    async def get_feed(self, limit: int = 50, offset: int = 0, **kwargs: Any) -> Feed:
        """Get the feed for this network.

        Args:
            limit: Maximum number of items to return.
            offset: Number of items to skip.
            **kwargs: Additional query parameters.

        Returns:
            Feed model containing feed items.

        Raises:
            FeedError: If the API request fails or returns invalid data.
        """
        await self._ensure_session()
        return await _domain_get_feed(self._rpc, limit=limit, offset=offset, **kwargs)

    async def get_user_unread_feed(self, limit: int = 50, offset: int = 0) -> Feed:
        """Get unread posts for the current user.

        Args:
            limit: Maximum number of items to return.
            offset: Number of items to skip.

        Returns:
            Feed model with unread posts.

        Raises:
            FeedError: If the API request fails.
        """
        return await self.get_feed(limit=limit, offset=offset, updated=True)

    async def get_user_posted_feed(self, limit: int = 50, offset: int = 0) -> Feed:
        """Get posts authored by the current user.

        Args:
            limit: Maximum number of items to return.
            offset: Number of items to skip.

        Returns:
            Feed model with the user's posts.

        Raises:
            FeedError: If the API request fails.
        """
        return await self.get_feed(limit=limit, offset=offset, my_post=True)

    async def get_filtered_feed(self, filter: FeedFilter, limit: int = 50, offset: int = 0) -> Feed:
        """Get feed with a specific filter applied.

        Args:
            filter: FeedFilter instance (UnreadFilter, FollowingFilter, etc.).
            limit: Maximum number of items to return.
            offset: Number of items to skip.

        Returns:
            Filtered feed model.

        Raises:
            FeedError: If the API request fails.
        """
        kwargs = filter.to_kwargs()
        return await self.get_feed(limit=limit, offset=offset, **kwargs)

    async def get_similar_posts(self, post_id: str) -> list[FeedItem]:
        """Get posts similar to a given post.

        Args:
            post_id: The post's unique identifier.

        Returns:
            List of validated FeedItem objects. Items that fail validation
            are silently skipped.

        Raises:
            ValidationError: If post_id is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        await self._ensure_session()
        return await _domain_get_similar_posts(self._rpc, post_id=post_id)

    async def get_folder_contents(self, folder_name: str) -> Feed:
        """Get all posts in a specific folder.

        Args:
            folder_name: Name of the folder to retrieve.

        Returns:
            Feed model containing posts in the folder.

        Raises:
            FeedError: If the API request fails.
        """
        folder_filter = FolderFilter(folder_name=folder_name)
        return await self.get_filtered_feed(folder_filter)

    # ── Post operations ───────────────────────────────────────────────

    async def get_post(self, post_id: str) -> Post:
        """Get a full post by ID.

        Args:
            post_id: The post's unique identifier.

        Returns:
            Full Post model with all data.

        Raises:
            ValidationError: If post_id is empty.
            NotFoundError: If post does not exist.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        await self._ensure_session()
        try:
            raw = await self._rpc.content_get(post_id)
            if not raw:
                raise NotFoundError(f"Post not found: {post_id}")
            return Post(
                id=raw.get("id", post_id),
                title=raw.get("title", ""),
                subject=raw.get("subject", ""),
                type=raw.get("type", "note"),
                author=raw.get("author", ""),
                user_name=raw.get("user_name", raw.get("author", "")),
                created_at=raw.get("created_at"),
                updated_at=raw.get("updated_at"),
                nr=raw.get("nr", 0),
                raw=raw,
                tags=raw.get("tags", []),
                folder=raw.get("folder", ""),
                views=raw.get("views", 0),
                config=raw.get("config", {}),
                children=raw.get("children", []),
            )
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise PiazzaSDKError(f"Failed to parse post {post_id}: {exc}") from exc

    async def create_post(
        self,
        title: str,
        content: str,
        post_type: PostType | str = "question",
        anonymous: bool = False,
        options: PublishingOptions | None = None,
        **kwargs: Any,
    ) -> PostCreatedResponse:
        """Create a new post.

        Args:
            title: Post title/subject.
            content: Post content (HTML or plain text).
            post_type: Type of post (question, note, poll).
            anonymous: Whether to post anonymously.
            options: Publishing options (bypass email, silent update, anonymity).

        Returns:
            PostCreatedResponse with new post ID.

        Raises:
            ValidationError: If title or content is empty.
        """
        await self._ensure_session()
        return await _domain_create_post(
            self._rpc,
            title=title,
            content=content,
            post_type=post_type,
            anonymous=anonymous,
            options=options,
            **kwargs,
        )

    async def create_followup(
        self,
        post: str | Post,
        content: str,
        anonymous: bool = False,
        options: PublishingOptions | None = None,
        **kwargs: Any,
    ) -> PostCreatedResponse:
        """Add a follow-up to an existing post.

        Args:
            post: Post ID string or Post model.
            content: Follow-up content.
            anonymous: Whether to post anonymously.
            options: Publishing options (bypass email, silent update, anonymity).

        Returns:
            PostCreatedResponse with new follow-up ID.

        Raises:
            ValidationError: If content is empty.
        """
        post_id = post if isinstance(post, str) else post.id
        await self._ensure_session()
        return await _domain_add_followup(
            self._rpc,
            post_id=post_id,
            content=content,
            anonymous=anonymous,
            options=options,
            **kwargs,
        )

    async def resolve_post(self, post_id: str) -> bool:
        """Mark a post as resolved.

        Args:
            post_id: The post's unique identifier.

        Returns:
            True if the operation succeeded.

        Raises:
            ValidationError: If post_id is empty.
        """
        await self._ensure_session()
        return await _domain_resolve_post(self._rpc, post_id=post_id)

    async def answer_post(
        self, post_id: str, content: str, instructor_answer: bool = False
    ) -> None:
        """Post an answer to a question.

        Args:
            post_id: The post's unique identifier.
            content: Answer content (HTML or plain text).
            instructor_answer: Whether this is an official instructor answer.

        Raises:
            ValidationError: If post_id or content is empty.
        """
        await self._ensure_session()
        await _domain_answer_post(
            self._rpc, post_id=post_id, content=content, instructor_answer=instructor_answer
        )

    async def endorse_post(self, post_id: str, as_instructor_badge: bool = False) -> Post:
        """Upvote/endorse a post or answer, optionally as an instructor badge.

        Args:
            post_id: The post or answer's unique identifier.
            as_instructor_badge: If True, award an instructor badge instead of
                a simple upvote.

        Returns:
            Updated Post model after endorsement.

        Raises:
            ValidationError: If post_id is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        await self._ensure_session()
        await _domain_endorse(self._rpc, post_id=post_id, as_instructor_badge=as_instructor_badge)
        return await self.get_post(post_id)

    async def add_tag(self, post_id: str, tag: str) -> None:
        """Add a tag to a post.

        Args:
            post_id: The post's unique identifier.
            tag: Tag name to add.

        Raises:
            ValidationError: If post_id or tag is empty.
        """
        await self._ensure_session()
        await _domain_add_tag(self._rpc, post_id=post_id, tag=tag)

    async def remove_tag(self, post_id: str, tag: str) -> None:
        """Remove a tag from a post.

        Args:
            post_id: The post's unique identifier.
            tag: Tag name to remove.

        Raises:
            ValidationError: If post_id or tag is empty.
        """
        await self._ensure_session()
        await _domain_remove_tag(self._rpc, post_id=post_id, tag=tag)

    async def delete_post(self, post_id: str) -> bool:
        """Delete a post.

        Args:
            post_id: The post's unique identifier.

        Returns:
            True if the post was successfully deleted.

        Raises:
            ValidationError: If post_id is empty.
        """
        await self._ensure_session()
        return await _domain_delete_post(self._rpc, post_id=post_id)

    async def pin_post(self, post_id: str) -> Post:
        """Pin a post by adding the 'pin' tag.

        Args:
            post_id: The post's unique identifier.

        Returns:
            Updated Post model.

        Raises:
            ValidationError: If post_id is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        await self.add_tag(post_id, "pin")
        return await self.get_post(post_id)

    async def lock_post(self, post_id: str) -> Post:
        """Lock a post by adding the 'lock' tag.

        Args:
            post_id: The post's unique identifier.

        Returns:
            Updated Post model.

        Raises:
            ValidationError: If post_id is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        await self.add_tag(post_id, "lock")
        return await self.get_post(post_id)

    async def mark_as_unread(self, post_id: str) -> bool:
        """Mark a post as unread for the current user.

        Args:
            post_id: The post's unique identifier.

        Returns:
            True if the operation succeeded.

        Raises:
            ValidationError: If post_id is empty.
        """
        await self._ensure_session()
        return await _domain_mark_as_unread(self._rpc, post_id=post_id)

    async def create_folder(self, folder_name: str) -> list[str]:
        """Create a new folder in this network.

        Args:
            folder_name: Name of the folder to create.

        Returns:
            Updated list of folder names after creation.

        Raises:
            ValidationError: If folder_name is empty.
        """
        await self._ensure_session()
        return await _domain_create_folder(self._rpc, folder_name=folder_name)

    async def save_draft(
        self, subject: str, content: str, post_type: PostType | str = "question", **kwargs: Any
    ) -> str:
        """Save a post as a draft.

        Args:
            subject: Post title/subject.
            content: Post content (HTML or plain text).
            post_type: Type of post (question, note, poll).
            **kwargs: Additional parameters to pass to the API.

        Returns:
            The draft post ID.

        Raises:
            ValidationError: If subject or content is empty.
        """
        await self._ensure_session()
        return await _domain_save_draft(
            self._rpc, subject=subject, content=content, post_type=post_type, **kwargs
        )

    async def upload_asset(
        self, filename: str, file_data: bytes, content_type: str | None = None
    ) -> AssetUploadResponse:
        """Upload a file asset to Piazza.

        Gets a pre-signed upload URL and uploads the file data to it.

        Args:
            filename: Name of the file to upload.
            file_data: Raw bytes of the file content.
            content_type: MIME type of the file. Auto-detected from filename
                if not provided; falls back to application/octet-stream.

        Returns:
            AssetUploadResponse with asset ID and upload URL.

        Raises:
            ValidationError: If filename or file_data is empty.
            UploadError: If the upload fails.
        """
        await self._ensure_session()
        return await _domain_upload_asset(
            self._rpc, filename=filename, file_data=file_data, content_type=content_type
        )

    # ── Users ─────────────────────────────────────────────────────────

    async def get_users(self) -> list[User]:
        """Get all users in the network.

        Returns:
            List of User model instances.

        Raises:
            UserError: If the API request fails.
        """
        await self._ensure_session()
        return await _domain_get_all_users(self._rpc)

    async def get_instructor_stats(self) -> dict[str, Any]:
        """Get instructor-specific statistics for this network.

        Returns:
            Raw instructor stats dictionary.

        Raises:
            UserError: If the API request fails.
        """
        await self._ensure_session()
        return await _domain_get_instructor_stats(self._rpc)

    async def get_online_users(self) -> list[User]:
        """Get currently online users in the network.

        Returns:
            List of online User model instances.

        Raises:
            UserError: If the API request fails.
        """
        await self._ensure_session()
        return await _domain_get_online_users(self._rpc)

    # ── Search & Statistics ───────────────────────────────────────────

    async def search(self, query: str, **kwargs: Any) -> Feed:
        """Search posts by query string.

        Args:
            query: Search query.
            **kwargs: Additional search parameters.

        Returns:
            Feed model with matching posts.

        Raises:
            ValidationError: If query is empty.
        """
        await self._ensure_session()
        return await _domain_search(self._rpc, query=query, **kwargs)

    async def get_statistics(self) -> Statistics:
        """Get network statistics.

        Returns:
            Statistics model with course metrics.

        Raises:
            StatisticsError: If the API request fails.
        """
        await self._ensure_session()
        return await _domain_get_statistics(self._rpc)

    # ── Preferences ───────────────────────────────────────────────────

    async def get_preferences(self) -> UserPreferences:
        """Retrieve the current user's preferences for this network.

        Returns:
            UserPreferences model with the current settings.

        Raises:
            ContentError: If the API request fails.
        """
        await self._ensure_session()
        return await _domain_get_preferences(self._rpc)

    async def update_preferences(self, prefs: UserPreferences) -> None:
        """Update the current user's preferences for this network.

        Uses ``exclude_unset=True`` to only transmit explicitly set fields,
        preventing a partial-update wipe of unset preferences.

        Args:
            prefs: UserPreferences with the fields to update.

        Raises:
            ContentError: If the API call fails.
        """
        await self._ensure_session()
        await _domain_update_preferences(self._rpc, prefs=prefs)

    # ── Hall of Fame ──────────────────────────────────────────────────

    async def get_hall_of_fame(self) -> list[HallOfFameItem]:
        """Get the Hall of Fame best answers for this network.

        Fetches the feed and extracts the ``result.hof.best_answer``
        array using defensive ``.get()`` chaining to prevent KeyError
        on missing or empty structures.

        Returns:
            List of HallOfFameItem models.

        Raises:
            FeedError: If the API request fails or response parsing errors.
        """
        await self._ensure_session()
        try:
            raw: dict[str, Any] = await self._rpc.get_my_feed()
            hof_list: list[dict[str, Any]] = (
                raw.get("result", {}).get("hof", {}).get("best_answer", [])
            )
            return [
                HallOfFameItem(**{k: v for k, v in item.items() if k in _HOF_FIELDS})
                for item in hof_list
            ]
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise FeedError(f"Failed to retrieve hall of fame: {exc}") from exc

    # ── Async iterators ───────────────────────────────────────────────

    async def iter_all_posts(
        self, limit: int = 100, delay_seconds: float = 1.0
    ) -> AsyncGenerator[Post, None]:
        """Iterate over all posts in the network.

        Fetches the feed in batches and yields full Post objects.
        Includes a configurable delay between requests to avoid rate limiting.

        Args:
            limit: Maximum number of posts to iterate over.
            delay_seconds: Seconds to wait between post fetches.

        Yields:
            Post objects from the feed.

        Raises:
            FeedError: If the feed API request fails.
            NotFoundError: If a post referenced by the feed cannot be found.
        """
        feed = await self.get_feed(limit=limit)
        for item in feed.feed:
            post = await self.get_post(item.id)
            yield post
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

    async def listen_for_events(
        self, poll_interval: float = 30.0
    ) -> AsyncGenerator[FeedItem, None]:
        """Poll the feed for new events in an async generator loop.

        Calls ``get_feed()`` every ``poll_interval`` seconds and yields
        any ``FeedItem`` objects not previously seen.  This replaces the
        CometD/Bayeux real-time stream with a reliable polling strategy
        over the existing ``get_feed()`` RPC path.

        Usage::

            async for event in network.listen_for_events(poll_interval=15):
                print(event.subject)

        Args:
            poll_interval: Seconds between feed polls.

        Yields:
            New FeedItem objects since the last poll.

        Raises:
            FeedError: If the feed API request fails during polling.
        """
        seen_ids: set[str] = set()
        while True:
            feed = await self.get_feed()
            for item in feed.feed:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    yield item
            await asyncio.sleep(poll_interval)
