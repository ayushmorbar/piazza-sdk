"""Feed-related models for Piazza SDK."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType, FeedSortOrder


class FeedItem(BaseModel):
    """A single item in a Piazza feed response.

    Represents a lightweight post reference suitable for list display.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    subject: str = ""
    type: FeedItemType | str = FeedItemType.UNKNOWN
    created: datetime | None = None
    updated: datetime | None = None
    default_anonymity: FeedItemDefaultAnonymity | str = FeedItemDefaultAnonymity.UNKNOWN
    uid: str = ""
    folder: str = ""
    no_answer: bool = False
    is_pinned: bool = Field(default=False, alias="pin")
    follows: bool = False
    viewed: bool = True
    reputation: int = 0
    badge: str = ""
    tags: list[str] = Field(default_factory=list)
    content_snippet: str | None = Field(default=None, alias="content_snipet")

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

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"updated": True}`` for the unread filter."""
        return {"updated": True}


class FollowingFilter(FeedFilter):
    """Filter feed to show only followed posts."""

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"following": True}`` for the following filter."""
        return {"following": True}


class FolderFilter(FeedFilter):
    """Filter feed to show posts from a specific folder.

    Attributes:
        folder_name: Name of the folder to filter by.
    """

    folder_name: str = ""

    def to_kwargs(self) -> dict[str, Any]:
        """Return ``{"folder": True, "filter_folder": name}`` parameters."""
        return {"folder": True, "filter_folder": self.folder_name}


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
            limit=self._limit if self._limit != 50 else 50,
            offset=self._offset if self._offset != 0 else 0,
        )
