"""Enumeration types for Piazza SDK models.

Defines StrEnum types that align with Piazza's internal API values
for posts, users, visibility, anonymity, and feed operations.
"""

from __future__ import annotations

from enum import StrEnum


class PostType(StrEnum):
    """Type of Piazza post."""

    NOTE = "note"
    QUESTION = "question"
    POLL = "poll"


class ChangeType(StrEnum):
    """Type of change in a post's change log."""

    CREATE = "create"
    FOLLOWUP = "followup"
    FEEDBACK = "feedback"
    INSTRUCTOR_ANSWER = "i_answer"
    STUDENT_ANSWER = "s_answer"


class Visibility(StrEnum):
    """Post visibility scope."""

    PUBLIC = "public"
    PRIVATE = "private"
    GROUP = "group"
    INSTRUCTORS_ONLY = "instructors_only"


class AnonymityLevel(StrEnum):
    """Anonymity level for post actions."""

    NO = "no"
    YES = "yes"
    FULL = "full"


class UserRole(StrEnum):
    """User role within a course network."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    TA = "ta"
    ADMIN = "admin"


class FeedSortOrder(StrEnum):
    """Sort order for feed results."""

    UPDATED = "updated"
    CREATED = "created"


class FeedItemType(StrEnum):
    """Type of item in a feed response."""

    NOTE = "note"
    QUESTION = "question"
    POLL = "poll"
    UNKNOWN = "unknown"


class FeedItemDefaultAnonymity(StrEnum):
    """Default anonymity setting for feed items."""

    NO = "no"
    YES = "yes"
    FULL = "full"
    UNKNOWN = "unknown"


class PostStatus(StrEnum):
    """Status of a post."""

    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPERSEDED = "superseded"


class NotificationType(StrEnum):
    """Type of notification."""

    FOLLOWUP = "followup"
    ANSWER = "answer"
    ENDORSEMENT = "endorsement"
    MENTION = "mention"


class FolderType(StrEnum):
    """Type of folder in the course."""

    INBOX = "inbox"
    OUTBOX = "outbox"
    STUDENT = "student"
    PINNED = "pinned"
    FOLDERS = "folders"


class SortField(StrEnum):
    """Field to sort results by."""

    UPDATED = "updated"
    CREATED = "created"
    ACTIVITY = "activity"


class ResponseFormat(StrEnum):
    """Expected response format."""

    JSON = "json"
    HTML = "html"
    TEXT = "text"
