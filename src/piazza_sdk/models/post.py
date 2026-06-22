"""Post-related models for Piazza SDK.

Covers the full post lifecycle: posts, follow-ups, answers, endorsements,
and change log entries.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from piazza_sdk.models.enums import AnonymityLevel, ChangeType, PostStatus, PostType, Visibility


class Endorsement(BaseModel):
    """An endorsement (upvote) on a post or answer.

    Attributes:
        role: Endorser's role string (e.g. "student", "instructor").
        name: Endorser display name.
        endorser: Endorser user ID, or ``None`` if anonymous.
        admin: Whether the endorser is a network admin.
        photo: Endorser photo path, if available.
        id: Endorsement record identifier.
        photo_url: Full URL to the endorser's photo.
        published: Whether the endorsement is published.
        us: Whether the endorser is a course staff member.
        facebook_id: Facebook ID of the endorser, if linked.
    """

    role: str = ""
    name: str = ""
    endorser: str | None = None
    admin: bool = False
    photo: str | None = None
    id: str = ""
    photo_url: str | None = None
    published: bool = False
    us: bool = False
    facebook_id: str | None = None


class ChangeLogEntry(BaseModel):
    """An entry in a post's change log.

    Attributes:
        anon: Anonymity level of the change author.
        uid: User ID of the person who made the change.
        data: Free-form data associated with the change.
        to: Target value after the change, if applicable.
        v: Visibility of the change record.
        type: Type of change (create, update, endorse, etc.).
        when: Timestamp when the change occurred.
        cid: Child element ID the change relates to, if any.
    """

    anon: AnonymityLevel = AnonymityLevel.NO
    uid: str = ""
    data: str | None = None
    to: str | None = None
    v: Visibility = Visibility.PUBLIC
    type: ChangeType = ChangeType.CREATE
    when: datetime | None = None
    cid: str = ""


class PostRevision(BaseModel):
    """A historical revision of a post's content.

    Represents a snapshot of a post's subject and content at a specific
    point in time.  Revisions are extracted from the ``raw`` payload
    returned by ``content.get``.

    Attributes:
        revision: Sequential revision number.
        subject: Subject line at this revision.
        content: Body content at this revision (HTML).
        uid: User ID of the editor.
        created: Timestamp when this revision was created.
    """

    revision: int = 0
    subject: str = ""
    content: str = ""
    uid: str = ""
    created: datetime | None = None


class FollowUp(BaseModel):
    """A follow-up comment on a post.

    Attributes:
        id: Unique identifier for this follow-up.
        uid: Author's user ID.
        subject: Follow-up subject line.
        content: Follow-up body content (HTML).
        created: Timestamp when the follow-up was posted.
        updated: Timestamp when the follow-up was last edited.
        anon: Anonymity level of the author.
    """

    id: str = ""
    uid: str = ""
    subject: str = ""
    content: str = ""
    created: datetime | None = None
    updated: datetime | None = None
    anon: AnonymityLevel = AnonymityLevel.NO


class Child(BaseModel):
    """A child element (follow-up or answer) in a post's children list.

    Attributes:
        id: Unique identifier for this child element.
        type: Element type (e.g. ``"followup"``, ``"answer"``).
        subject: Child subject line.
        content: Child body content (HTML).
        uid: Author's user ID.
        created: Timestamp when the child was posted.
        updated: Timestamp when the child was last edited.
        anon: Anonymity level of the author.
        no_answer: Whether this follow-up has no answer yet.
        followed: Whether the current user is following this element.
    """

    id: str = ""
    type: str = ""
    subject: str = ""
    content: str = ""
    uid: str = ""
    created: datetime | None = None
    updated: datetime | None = None
    anon: AnonymityLevel = AnonymityLevel.NO
    no_answer: bool = False
    followed: bool = False


class Answer(BaseModel):
    """An answer to a question post.

    Attributes:
        id: Unique identifier for this answer.
        uid: Author's user ID.
        content: Answer body content (HTML).
        created: Timestamp when the answer was posted.
        updated: Timestamp when the answer was last edited.
        votes: Number of votes/endorsements on this answer.
        endorsements: List of endorsement records.
        is_instructor_answer: Whether the author is an instructor.
        is_student_answer: Whether the author is a student.
        rated: Whether the current user has rated this answer.
        folder: Folder assignment for this answer.
    """

    id: str = ""
    uid: str = ""
    content: str = ""
    created: datetime | None = None
    updated: datetime | None = None
    votes: int = 0
    endorsements: list[Endorsement] = Field(default_factory=list)
    is_instructor_answer: bool = False
    is_student_answer: bool = False
    rated: bool = False
    folder: str = ""


class StudentInfo(BaseModel):
    """Student-specific information attached to a post.

    Attributes:
        uid: Student's user ID.
        name: Student display name.
        email: Student email address.
        role: Student role string.
    """

    uid: str = ""
    name: str = ""
    email: str = ""
    role: str = ""


class PublishingOptions(BaseModel):
    """Options for post creation/publishing behavior."""

    model_config = ConfigDict(populate_by_name=True)

    bypass_email: bool = Field(default=False, serialization_alias="bypass_email")
    silent_update: bool = Field(default=False, serialization_alias="no_up_notify")
    anonymity: Literal["no", "stud", "all"] = "no"

    @field_serializer("bypass_email")
    def _bypass_email_int(self, v: bool) -> int:
        return int(v)

    @field_serializer("silent_update")
    def _silent_update_int(self, v: bool) -> int:
        return int(v)

    def to_kwargs(self) -> dict[str, Any]:
        """Convert to kwargs for RPC calls."""
        return {
            "options[bypass_email]": self.bypass_email,
            "options[no_up_notify]": self.silent_update,
            "options[anonymous]": self.anonymity,
        }


class PostConfig(BaseModel):
    """Post configuration settings.

    Attributes:
        name: Configuration name or label.
        instructor_note: Note from the instructor, if set.
        created: Timestamp when the configuration was created.
    """

    name: str = ""
    instructor_note: str = ""
    created: str = ""


class Post(BaseModel):
    """A Piazza post with full lifecycle data.

    Supports dot-notation access for all fields. Fields map directly
    from Piazza's internal JSON API structure.
    """

    id: str
    type: PostType = PostType.NOTE
    title: str = ""
    subject: str = ""
    author: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    nr: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    folder: str = ""
    status: PostStatus = PostStatus.ACTIVE
    views: int = 0
    unique_views: int | None = None
    students: list[StudentInfo] = Field(default_factory=list)
    followups: list[FollowUp] = Field(default_factory=list)
    answers: list[Answer] = Field(default_factory=list)
    change_log: list[ChangeLogEntry] = Field(default_factory=list)
    endorsements: list[Endorsement] = Field(default_factory=list)
    config: PostConfig = Field(default_factory=PostConfig)
    children: list[Child] = Field(default_factory=list)
    user_name: str = ""
    visibility: Visibility = Visibility.PUBLIC
    revisions: list[PostRevision] = Field(default_factory=list)

    @property
    def is_question(self) -> bool:
        """Check if post is a question."""
        return self.type == PostType.QUESTION

    @property
    def is_resolved(self) -> bool:
        """Check if post is resolved."""
        return self.status == PostStatus.RESOLVED

    @property
    def total_votes(self) -> int:
        """Total endorsement votes across all answers."""
        return sum(len(a.endorsements) for a in self.answers)

    @property
    def answer_count(self) -> int:
        """Number of answers on this post."""
        return len(self.answers)

    @property
    def followup_count(self) -> int:
        """Number of follow-ups on this post."""
        return len(self.followups)

    @property
    def student_answer(self) -> Child | None:
        """The first student answer child, if any."""
        return next((c for c in self.children if c.type == "s_answer"), None)

    @property
    def instructor_answer(self) -> Child | None:
        """The first instructor answer child, if any."""
        return next((c for c in self.children if c.type == "i_answer"), None)
