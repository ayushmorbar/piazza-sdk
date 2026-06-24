"""Enumeration types for Piazza SDK models.

Defines StrEnum types that align with Piazza's internal API values
for posts, users, visibility, anonymity, and feed operations.
"""

from __future__ import annotations

from enum import StrEnum


class PostType(StrEnum):
    """Type of Piazza post."""

    NOTE = "note"  # Informational post (no answers expected)
    QUESTION = "question"  # Question post (supports answers/endorsements)
    POLL = "poll"  # Poll with multiple-choice options


class ChangeType(StrEnum):
    """Type of change in a post's change log."""

    CREATE = "create"  # Post was created
    FOLLOWUP = "followup"  # Follow-up was added
    FEEDBACK = "feedback"  # Feedback was given
    INSTRUCTOR_ANSWER = "i_answer"  # Instructor posted an answer
    STUDENT_ANSWER = "s_answer"  # Student posted an answer


class Visibility(StrEnum):
    """Post visibility scope."""

    PUBLIC = "public"  # Visible to all students
    PRIVATE = "private"  # Visible only to instructors
    GROUP = "group"  # Visible to a specific group
    INSTRUCTORS_ONLY = "instructors_only"  # Visible to instructors only


class AnonymityLevel(StrEnum):
    """Anonymity level for post actions."""

    NO = "no"  # No anonymity (author shown)
    YES = "yes"  # Anonymous to students (shown to instructors)
    FULL = "full"  # Fully anonymous (instructors see only after resolution)


class UserRole(StrEnum):
    """User role within a course network."""

    STUDENT = "student"  # Student enrolled in the course
    INSTRUCTOR = "instructor"  # Course instructor
    TA = "ta"  # Teaching assistant
    ADMIN = "admin"  # Network administrator


class FeedSortOrder(StrEnum):
    """Feed sort order as sent to the Piazza API."""

    UPDATED = "updated"  # Sort by most recently updated (newest first)
    CREATED = "created"  # Sort by creation time


class FeedItemType(StrEnum):
    """Type of item in a feed response."""

    NOTE = "note"  # Informational post
    QUESTION = "question"  # Question post
    POLL = "poll"  # Poll post
    UNKNOWN = "unknown"  # Unknown/unrecognized type


class FeedItemDefaultAnonymity(StrEnum):
    """Default anonymity setting for feed items."""

    NO = "no"  # No anonymity (author shown)
    YES = "yes"  # Anonymous to students (shown to instructors)
    FULL = "full"  # Fully anonymous (shown after resolution)
    UNKNOWN = "unknown"  # Unknown/unrecognized setting


class PostStatus(StrEnum):
    """Status of a post."""

    ACTIVE = "active"  # Post is open for answers
    RESOLVED = "resolved"  # Post has been resolved
    SUPERSEDED = "superseded"  # Post replaced by another


class NotificationType(StrEnum):
    """Type of notification."""

    FOLLOWUP = "followup"  # New follow-up posted
    ANSWER = "answer"  # New answer posted
    ENDORSEMENT = "endorsement"  # Answer endorsed
    MENTION = "mention"  # User mentioned in post


class FolderType(StrEnum):
    """Type of folder in the course."""

    INBOX = "inbox"  # Posts directed at the user
    OUTBOX = "outbox"  # Posts authored by the user
    STUDENT = "student"  # Student-created posts
    PINNED = "pinned"  # Pinned/important posts
    FOLDERS = "folders"  # Custom folder listing


class SortField(StrEnum):
    """Field to sort results by."""

    UPDATED = "updated"  # Sort by last update time
    CREATED = "created"  # Sort by creation time
    ACTIVITY = "activity"  # Sort by overall activity level


class ResponseFormat(StrEnum):
    """Expected response format."""

    JSON = "json"  # JSON response
    HTML = "html"  # HTML-formatted response
    TEXT = "text"  # Plain text response
