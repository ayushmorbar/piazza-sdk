"""Network class for Piazza SDK.

Provides the Network class that handles per-class operations:
feed retrieval, post management, user queries, and search.
"""

from __future__ import annotations

import asyncio
import mimetypes
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError as PydanticValidationError

from piazza_sdk.exceptions import (
    ContentError,
    FeedError,
    NotFoundError,
    PiazzaSDKError,
    UploadError,
    ValidationError,
)
from piazza_sdk.models.feed import Feed, FeedFilter, FeedItem, FolderFilter
from piazza_sdk.models.network import HallOfFameItem, Statistics
from piazza_sdk.models.post import Post, PublishingOptions
from piazza_sdk.models.user import UserPreferences

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager


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

    async def get_feed(self, limit: int = 50, offset: int = 0, **kwargs: Any) -> Feed:
        """Get the feed for this network.

        Args:
            limit: Maximum number of items to return.
            offset: Number of items to skip.
            **kwargs: Additional query parameters.

        Returns:
            Feed model containing feed items.
        """
        await self._ensure_session()
        try:
            raw = await self._rpc.get_my_feed(limit=limit, offset=offset, **kwargs)
            items = [FeedItem(**item) for item in raw.get("feed", [])]
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

    async def get_user_unread_feed(self, limit: int = 50, offset: int = 0) -> Feed:
        """Get unread posts for the current user.

        Args:
            limit: Maximum number of items to return.
            offset: Number of items to skip.

        Returns:
            Feed model with unread posts.
        """
        return await self.get_feed(limit=limit, offset=offset, updated=True)

    async def get_user_posted_feed(self, limit: int = 50, offset: int = 0) -> Feed:
        """Get posts authored by the current user.

        Args:
            limit: Maximum number of items to return.
            offset: Number of items to skip.

        Returns:
            Feed model with the user's posts.
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
        """
        kwargs = filter.to_kwargs()
        return await self.get_feed(limit=limit, offset=offset, **kwargs)

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
            raise ContentError(f"Failed to parse post {post_id}: {exc}") from exc

    async def create_post(
        self,
        title: str,
        content: str,
        post_type: str = "question",
        anonymous: bool = False,
        options: PublishingOptions | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Create a new post.

        Args:
            title: Post title/subject.
            content: Post content (HTML or plain text).
            post_type: Type of post (question, note, poll).
            anonymous: Whether to post anonymously.
            options: Publishing options (bypass email, silent update, anonymity).

        Returns:
            Raw response data with new post ID.

        Raises:
            ValidationError: If title or content is empty.
        """
        if not title or not title.strip():
            raise ValidationError("title must be non-empty")
        if not content or not content.strip():
            raise ValidationError("content must be non-empty")
        if options is not None:
            kwargs.update(options.to_kwargs())
        return await self._rpc.content_create(
            title=title, content=content, type=post_type, anonymous=anonymous, **kwargs
        )

    async def create_followup(
        self,
        post: str | Post,
        content: str,
        anonymous: bool = False,
        options: PublishingOptions | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Add a follow-up to an existing post.

        Args:
            post: Post ID string or Post model.
            content: Follow-up content.
            anonymous: Whether to post anonymously.
            options: Publishing options (bypass email, silent update, anonymity).

        Returns:
            Raw response data.

        Raises:
            ValidationError: If content is empty.
        """
        if not content or not content.strip():
            raise ValidationError("content must be non-empty")
        post_id = post if isinstance(post, str) else post.id
        if options is not None:
            kwargs.update(options.to_kwargs())
        return await self._rpc.content_create(
            cid=post_id, content=content, anonymous=anonymous, **kwargs
        )

    async def resolve_post(self, post_id: str) -> dict[str, Any]:
        """Mark a post as resolved.

        Args:
            post_id: The post's unique identifier.

        Returns:
            Raw response data.

        Raises:
            ValidationError: If post_id is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        return await self._rpc.content_update(cid=post_id, status="resolved")

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
        if not query or not query.strip():
            raise ValidationError("query must be non-empty")
        await self._ensure_session()
        raw = await self._rpc.search(query, **kwargs)
        items = [FeedItem(**item) for item in raw.get("feed", [])]
        return Feed(feed=items, total=raw.get("total", len(items)))

    async def get_users(self) -> list[dict[str, Any]]:
        """Get all users in the network.

        Returns:
            List of user dictionaries.
        """
        await self._ensure_session()
        raw = await self._rpc.get_users()
        users: list[dict[str, Any]] = raw.get("users", []) if isinstance(raw, dict) else []
        return users

    async def get_statistics(self) -> Statistics:
        """Get network statistics.

        Returns:
            Statistics model with course metrics.
        """
        await self._ensure_session()
        raw = await self._rpc.get_stats()
        return Statistics(
            posts=raw.get("posts", 0),
            resolved=raw.get("resolved", 0),
            unresolved=raw.get("unresolved", 0),
            users=raw.get("users", 0),
            instructors=raw.get("instructors", 0),
            students=raw.get("students", 0),
            total_views=raw.get("total_views", 0),
            total_endorsements=raw.get("total_endorsements", 0),
        )

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
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        if not content or not content.strip():
            raise ValidationError("content must be non-empty")
        await self._ensure_session()
        try:
            await self._rpc.content_answer(post_id, content, instructor_answer)
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to answer post {post_id}: {exc}") from exc

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
        try:
            if as_instructor_badge:
                await self._rpc.add_badge(post_id)
            else:
                await self._rpc.content_upvote(post_id)
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to endorse post {post_id}: {exc}") from exc
        return await self.get_post(post_id)

    async def add_tag(self, post_id: str, tag: str) -> None:
        """Add a tag to a post.

        Args:
            post_id: The post's unique identifier.
            tag: Tag name to add.

        Raises:
            ValidationError: If post_id or tag is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        if not tag or not tag.strip():
            raise ValidationError("tag must be non-empty")
        await self._ensure_session()
        try:
            await self._rpc.content_add_tag(post_id, tag)
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to add tag to post {post_id}: {exc}") from exc

    async def remove_tag(self, post_id: str, tag: str) -> None:
        """Remove a tag from a post.

        Args:
            post_id: The post's unique identifier.
            tag: Tag name to remove.

        Raises:
            ValidationError: If post_id or tag is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        if not tag or not tag.strip():
            raise ValidationError("tag must be non-empty")
        await self._ensure_session()
        try:
            await self._rpc.content_remove_tag(post_id, tag)
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to remove tag from post {post_id}: {exc}") from exc

    async def delete_post(self, post_id: str) -> bool:
        """Delete a post.

        Args:
            post_id: The post's unique identifier.

        Returns:
            True if the post was successfully deleted.

        Raises:
            ValidationError: If post_id is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        await self._ensure_session()
        try:
            raw = await self._rpc.content_delete(post_id)
            return isinstance(raw, dict) and raw.get("result") == "success"
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to delete post {post_id}: {exc}") from exc

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

    async def get_instructor_stats(self) -> dict[str, Any]:
        """Get instructor-specific statistics for this network.

        Returns:
            Raw instructor stats dictionary.
        """
        await self._ensure_session()
        try:
            return await self._rpc.get_instructor_stats()
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to get instructor stats: {exc}") from exc

    async def get_online_users(self) -> list[dict[str, Any]]:
        """Get currently online users in this network.

        Returns:
            List of online user dictionaries.
        """
        await self._ensure_session()
        try:
            raw: dict[str, Any] = await self._rpc.get_online_users()
            users: list[dict[str, Any]] = raw.get("users", [])
            return users
        except (NotFoundError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to get online users: {exc}") from exc

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
        """
        feed = await self.get_feed(limit=limit)
        for item in feed.feed:
            post = await self.get_post(item.id)
            yield post
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

    async def get_folder_contents(self, folder_name: str) -> Feed:
        """Get all posts in a specific folder.

        Args:
            folder_name: Name of the folder to retrieve.

        Returns:
            Feed model containing posts in the folder.
        """
        folder_filter = FolderFilter(folder_name=folder_name)
        return await self.get_filtered_feed(folder_filter)

    async def get_preferences(self) -> UserPreferences:
        """Retrieve the current user's preferences for this network.

        Returns:
            UserPreferences model with the current settings.
        """
        await self._ensure_session()
        try:
            raw: dict[str, Any] = await self._rpc.get_user_preferences()
            return UserPreferences(**raw)
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise ContentError(f"Failed to get preferences: {exc}") from exc

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
        try:
            payload = prefs.model_dump(by_alias=True, exclude_unset=True)
            await self._rpc.update_user_preferences(payload)
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise ContentError(f"Failed to update preferences: {exc}") from exc

    async def get_hall_of_fame(self) -> list[HallOfFameItem]:
        """Get the Hall of Fame best answers for this network.

        Fetches the feed and extracts the ``result.hof.best_answer``
        array using defensive ``.get()`` chaining to prevent KeyError
        on missing or empty structures.

        Returns:
            List of HallOfFameItem models.
        """
        await self._ensure_session()
        try:
            raw: dict[str, Any] = await self._rpc.get_my_feed()
            hof_list: list[dict[str, Any]] = (
                raw.get("result", {}).get("hof", {}).get("best_answer", [])
            )
            return [HallOfFameItem(**item) for item in hof_list]
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise FeedError(f"Failed to retrieve hall of fame: {exc}") from exc

    async def mark_as_unread(self, post_id: str) -> bool:
        """Mark a post as unread for the current user.

        Args:
            post_id: The post's unique identifier.

        Returns:
            True if the operation succeeded.

        Raises:
            ValidationError: If post_id is empty.
        """
        if not post_id or not post_id.strip():
            raise ValidationError("post_id must be non-empty")
        await self._ensure_session()
        try:
            raw: dict[str, Any] = await self._rpc.mark_as_unread(post_id)
            return raw.get("result") == "success"
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise ContentError(f"Failed to mark post as unread: {exc}") from exc

    async def create_folder(self, folder_name: str) -> list[str]:
        """Create a new folder in this network.

        Args:
            folder_name: Name of the folder to create.

        Returns:
            Updated list of folder names after creation.

        Raises:
            ValidationError: If folder_name is empty.
        """
        if not folder_name or not folder_name.strip():
            raise ValidationError("folder_name must be non-empty")
        await self._ensure_session()
        try:
            raw: dict[str, Any] = await self._rpc.add_folder(folder_name)
            folders: list[str] = raw.get("folders", []) if isinstance(raw, dict) else []
            return folders
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise ContentError(f"Failed to create folder: {exc}") from exc

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
        """
        seen_ids: set[str] = set()
        while True:
            feed = await self.get_feed()
            for item in feed.feed:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    yield item
            await asyncio.sleep(poll_interval)

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
        try:
            raw: dict[str, Any] = await self._rpc.content_get_similar(post_id)
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
            raise ContentError(
                f"Failed to get similar posts for {post_id}: {exc}"
            ) from exc

    async def save_draft(
        self, subject: str, content: str, post_type: str = "question", **kwargs: Any
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
        if not subject or not subject.strip():
            raise ValidationError("subject must be non-empty")
        if not content or not content.strip():
            raise ValidationError("content must be non-empty")
        await self._ensure_session()
        try:
            result = await self._rpc.content_save_draft(
                subject=subject, content=content, post_type=post_type, **kwargs
            )
            draft_id = result.get("id")
            if not isinstance(draft_id, str) or not draft_id:
                raise ContentError(
                    "Piazza backend accepted the draft but failed to return an ID."
                )
            return draft_id
        except (ContentError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise ContentError(f"Failed to save draft: {exc}") from exc

    async def upload_asset(
        self, filename: str, file_data: bytes, content_type: str | None = None
    ) -> dict[str, Any]:
        """Upload a file asset to Piazza.

        Gets a pre-signed upload URL and uploads the file data to it.

        Args:
            filename: Name of the file to upload.
            file_data: Raw bytes of the file content.
            content_type: MIME type of the file. Auto-detected from filename
                if not provided; falls back to application/octet-stream.

        Returns:
            Dictionary with asset metadata (id, content_type, name, url).

        Raises:
            ValidationError: If filename or file_data is empty.
            UploadError: If the upload fails.
        """
        if not filename or not filename.strip():
            raise ValidationError("filename must be non-empty")
        if not file_data:
            raise ValidationError("file_data must not be empty")
        if content_type is None:
            guessed, _ = mimetypes.guess_type(filename)
            content_type = guessed or "application/octet-stream"
        await self._ensure_session()
        try:
            url_data = await self._rpc.asset_get_upload_url(filename)
            upload_url: str | None = url_data.get("url") or url_data.get("upload_url")
            if not upload_url:
                raise UploadError("No upload URL returned from API")
            http_client = self._rpc._client
            response = await http_client.put(
                upload_url,
                content=file_data,
                headers={"Content-Type": content_type},
            )
            response.raise_for_status()
            return url_data
        except (UploadError, PiazzaSDKError):
            raise
        except Exception as exc:
            raise UploadError(f"Failed to upload asset {filename}: {exc}") from exc
