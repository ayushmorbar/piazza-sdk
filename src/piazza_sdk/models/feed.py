"""Feed-related models for Piazza SDK."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType, FeedSortOrder


class FeedItemStat(BaseModel):
    """Nested statistics for a feed item.

    Attributes:
        total: Total number of students who can see this post.
        unread: Number of students who haven't read this post.
        students: Number of students who have viewed this post.
        unresolved: Number of unresolved follow-ups.
        instructor_note: Whether this is an instructor note.
        my_returned: Whether the current user has a returned item.
        my_synthesis: Whether the current user has synthesis available.
        my_feedback: Whether the current user has feedback.
        my_replies: Number of replies to the current user.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    total: int = Field(default=0, description="Total students who can see this post")
    unread: int = Field(default=0, description="Students who haven't read this post")
    students: int = Field(default=0, description="Students who have viewed this post")
    unresolved: int = Field(default=0, description="Unresolved follow-ups")
    instructor_note: bool = Field(default=False, description="Whether this is an instructor note")
    my_returned: bool = Field(default=False, description="Whether current user has returned item")
    my_synthesis: bool = Field(default=False, description="Whether current user has synthesis")
    my_feedback: bool = Field(default=False, description="Whether current user has feedback")
    my_replies: int = Field(default=0, description="Number of replies to current user")


class FeedItem(BaseModel):
    """A single item in a Piazza feed response.

    Represents a lightweight post reference suitable for list display.

    Attributes:
        id: Unique post identifier.
        subject: Post title/subject line.
        type: Feed item type (question, note, poll, etc.).
        created: Timestamp when the post was created.
        updated: Timestamp of the last update.
        default_anonymity: Default anonymity setting for the post.
        uid: Author user ID.
        folder: Folder name the post belongs to.
        no_answer: Whether the post has no answers yet.
        is_pinned: Whether the post is pinned (serialized as ``pin``).
        follows: Whether the current user is following this post.
        viewed: Whether the current user has viewed this post.
        reputation: Author's reputation score.
        badge: Author's badge or role indicator.
        tag: Tag on the post (singular string).
        content_snippet: Short content preview (serialized as ``content_snipet``,
            note the misspelling in Piazza's API).
        stat: Nested statistics for this feed item.
    """

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(description="Unique post identifier")
    nid: str = Field(default="", description="Network ID")
    nr: int = Field(default=0, description="Numeric post number")
    subject: str = Field(default="", description="Post title/subject line")
    type: FeedItemType | str = Field(default=FeedItemType.UNKNOWN, description="Feed item type")
    status: str = Field(default="", description="Post status")
    created: datetime | None = Field(default=None, description="When the post was created")
    updated: datetime | None = Field(default=None, description="When the post was last updated")
    default_anonymity: FeedItemDefaultAnonymity | str = Field(
        default=FeedItemDefaultAnonymity.UNKNOWN, description="Default anonymity setting"
    )
    uid: str = Field(default="", alias="u", description="Author user ID")
    folder: str = Field(default="", alias="fol", description="Folder name (pipe-delimited)")
    folders: list[str] = Field(default_factory=list, description="Folder names")
    no_answer: bool = Field(default=False, description="Whether post has no answers")
    is_pinned: bool = Field(default=False, alias="pin", description="Whether post is pinned")
    bookmarked: bool = Field(default=False, alias="book", description="Whether post is bookmarked")
    follows: bool = Field(default=False, description="Whether current user is following")
    viewed: bool = Field(default=True, description="Whether current user has viewed")
    unique_views: int | None = Field(default=None, description="Unique view count")
    score: float = Field(default=0.0, description="Post score")
    reputation: int = Field(default=0, description="Author reputation score")
    badge: str = Field(default="", description="Author badge or role indicator")
    bucket_name: str = Field(default="", description="Bucket name (e.g. Pinned)")
    bucket_order: int = Field(default=0, description="Bucket ordering")
    tag: str | None = Field(default=None, description="Post tag (singular)")
    content_snippet: str | None = Field(
        default=None, alias="content_snipet", description="Short content preview"
    )
    d_bucket: str | None = Field(
        default=None, alias="d-bucket", description="Date bucket (e.g. Yesterday)"
    )
    feed_groups: list[dict[str, Any]] = Field(
        default_factory=list, description="Feed group categorization data"
    )
    gd: int | None = Field(default=None, description="Good question count")
    gd_a: int | None = Field(default=None, description="Good answer count")
    gd_f: int | None = Field(default=None, description="Good followup count")
    tag_endorse_prof: bool | None = Field(
        default=None, description="Whether endorsed by instructor"
    )
    tag_good_prof: bool | None = Field(default=None, description="Whether marked good by professor")
    is_new: bool = Field(default=False, description="Whether feed item is new")
    view_adjust: int | None = Field(default=None, description="View count adjustment token")
    log: list[dict[str, Any]] = Field(
        default_factory=list, alias="change_log", description="Change log entries"
    )
    stat: FeedItemStat | None = Field(default=None, description="Feed item statistics")
    folder_num: int = Field(default=0, description="Folder number")
    has_i: bool | None = Field(default=None, description="Whether post has instructor answer")
    has_s: bool | None = Field(default=None, description="Whether post has student answer")

    @property
    def is_question(self) -> bool:
        """Check if this feed item is a question."""
        return self.type == FeedItemType.QUESTION


class Feed(BaseModel):
    """A Piazza feed response containing a list of feed items.

    Attributes:
        feed: List of feed items.
        total: Total number of items available.
        page: Current page number.
        page_size: Number of items per page.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    feed: list[FeedItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class FeedFilter(BaseModel):
    """Base class for feed filtering.

    Subclass this to create specific filters (unread, following, folder, etc.).
    """

    def to_kwargs(self) -> dict[str, Any]:
        """Convert filter to API query parameters."""
        return {}


class UnreadFilter(FeedFilter):
    """Filter feed to show only unread posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"updated": True}`` for the unread filter."""
        return {"updated": True}


class FollowingFilter(FeedFilter):
    """Filter feed to show only followed posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"following": True}`` for the following filter."""
        return {"following": True}


class FolderFilter(FeedFilter):
    """Filter feed to show posts from a specific folder.

    Attributes:
        folder_name: Name of the folder to filter by.
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    folder_name: str = ""

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"folder": True, "filter_folder": name}`` parameters."""
        return {"folder": True, "filter_folder": self.folder_name}


class UnansweredFilter(FeedFilter):
    """Filter feed to show unanswered posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"unanswered": 1}`` for the unanswered filter."""
        return {"unanswered": 1}


class UnresolvedFilter(FeedFilter):
    """Filter feed to show unresolved posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"unresolved": 1}`` for the unresolved filter."""
        return {"unresolved": 1}


class HideGroupPostsFilter(FeedFilter):
    """Filter feed to hide group posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"hide_group_posts": 1}`` for the hide group posts filter."""
        return {"hide_group_posts": 1}


class InstructorsFilter(FeedFilter):
    """Filter feed to show instructor posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"instructors": 1}`` for the instructors filter."""
        return {"instructors": 1}


class MyPostsFilter(FeedFilter):
    """Filter feed to show the current user's posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"my_posts": 1}`` for the my posts filter."""
        return {"my_posts": 1}


class DueFilter(FeedFilter):
    """Filter feed to show due posts."""

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"due": 1}`` for the due filter."""
        return {"due": 1}


class SearchFilter(FeedFilter):
    """Search feed for posts matching a query.

    Attributes:
        query: Search query string.
        folder: Folder name to restrict the search to.
        tag: Tag to filter by.
        instructor: Instructor name to filter by.
        student: Student name to filter by.
        sort: Sort order string (``"relevance"``, ``"date"``, etc.).
        limit: Maximum number of results.
        offset: Number of results to skip.
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    query: str = ""
    folder: str = ""
    tag: str = ""
    instructor: str = ""
    student: str = ""
    sort: str = "relevance"
    limit: int = 50
    offset: int = 0

    def to_kwargs(self) -> dict[str, Any]:
        """Return API query parameters for this search filter."""
        params: dict[str, str | int | bool] = {"search": True}
        if self.query:
            params["search_query"] = self.query
        if self.folder:
            params["filter_folder"] = self.folder
        if self.tag:
            params["filter_tag"] = self.tag
        if self.instructor:
            params["filter_instructor"] = self.instructor
        if self.student:
            params["filter_student"] = self.student
        if self.sort:
            params["sort"] = self.sort
        if self.limit != 50:
            params["limit"] = self.limit
        if self.offset != 0:
            params["offset"] = self.offset
        return params


class SortFilter(FeedFilter):
    """Sort feed results.

    Attributes:
        order: Sort order (updated or created).
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    order: FeedSortOrder = FeedSortOrder.UPDATED

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"sort": order_value}`` parameters."""
        return {"sort": self.order.value}


class SearchBuilder:
    """Fluent query builder for Piazza search.

    Accumulates filter parameters and compiles down to a
    ``SearchFilter`` object.  Does not touch the network layer —
    call ``.execute()`` on the owning ``Network`` instance or
    use ``.compile()`` to get the underlying filter.

    Usage::

        from piazza_sdk.models.feed import SearchBuilder

        builder = (
            SearchBuilder()
            .with_query("homework 3")
            .in_folder("Homework")
            .limit(25)
        )
        filter_obj = builder.compile()  # -> SearchFilter
    """

    def __init__(self) -> None:
        self._query: str = ""
        self._folder: str | None = None
        self._limit: int = 50
        self._offset: int = 0

    def with_query(self, text: str) -> SearchBuilder:
        """Set the search query string.

        Args:
            text: The search query.

        Returns:
            self, for chaining.
        """
        self._query = text
        return self

    def in_folder(self, folder_name: str) -> SearchBuilder:
        """Restrict search to a specific folder.

        Args:
            folder_name: Name of the folder to search within.

        Returns:
            self, for chaining.
        """
        self._folder = folder_name
        return self

    def limit(self, count: int) -> SearchBuilder:
        """Set the maximum number of results.

        Args:
            count: Maximum items to return.

        Returns:
            self, for chaining.
        """
        self._limit = count
        return self

    def offset(self, count: int) -> SearchBuilder:
        """Set the number of items to skip.

        Args:
            count: Items to skip.

        Returns:
            self, for chaining.
        """
        self._offset = count
        return self

    def compile(self) -> SearchFilter:
        """Compile accumulated parameters into a ``SearchFilter``.

        Returns:
            A SearchFilter ready to pass to ``Network.get_filtered_feed()``.
        """
        return SearchFilter(
            query=self._query,
            folder=self._folder if self._folder is not None else "",
            limit=self._limit,
            offset=self._offset,
        )
