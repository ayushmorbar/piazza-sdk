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

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    role: str = Field(default="", description="Endorser's role (e.g. student, instructor)")
    name: str = Field(default="", description="Endorser display name")
    endorser: str | None = Field(default=None, description="Endorser user ID, or None if anonymous")
    admin: bool = Field(default=False, description="Whether the endorser is a network admin")
    photo: str | None = Field(default=None, description="Endorser photo path, if available")
    id: str = Field(default="", description="Endorsement record identifier")
    photo_url: str | None = Field(default=None, description="Full URL to the endorser's photo")
    published: bool = Field(default=False, description="Whether the endorsement is published")
    us: bool = Field(default=False, description="Whether the endorser is a course staff member")
    facebook_id: str | None = Field(
        default=None, description="Facebook ID of the endorser, if linked"
    )


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

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    anon: AnonymityLevel = Field(
        default=AnonymityLevel.NO,
        description="Anonymity level of the change author",
    )
    uid: str = Field(default="", description="User ID of the person who made the change")
    data: str | None = Field(default=None, description="Free-form data associated with the change")
    to: str | None = Field(default=None, description="Target value after the change, if applicable")
    v: Visibility = Field(default=Visibility.PUBLIC, description="Visibility of the change record")
    type: ChangeType = Field(
        default=ChangeType.CREATE,
        description="Type of change (create, update, endorse, etc.)",
    )
    when: datetime | None = Field(default=None, description="Timestamp when the change occurred")
    cid: str = Field(default="", description="Child element ID the change relates to, if any")


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

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    revision: int = Field(default=0, description="Sequential revision number")
    subject: str = Field(default="", description="Subject line at this revision")
    content: str = Field(default="", description="Body content at this revision (HTML)")
    uid: str = Field(default="", description="User ID of the editor")
    created: datetime | None = Field(
        default=None, description="Timestamp when this revision was created"
    )


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

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Unique identifier for this follow-up")
    uid: str = Field(default="", description="Author's user ID")
    subject: str = Field(default="", description="Follow-up subject line")
    content: str = Field(default="", description="Follow-up body content (HTML)")
    created: datetime | None = Field(
        default=None, description="Timestamp when the follow-up was posted"
    )
    updated: datetime | None = Field(
        default=None,
        description="Timestamp when the follow-up was last edited",
    )
    anon: AnonymityLevel = Field(
        default=AnonymityLevel.NO,
        description="Anonymity level of the author",
    )


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

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Unique identifier for this child element")
    type: str = Field(default="", description="Element type (e.g. followup, answer)")
    subject: str = Field(default="", description="Child subject line")
    content: str = Field(default="", description="Child body content (HTML)")
    uid: str = Field(default="", description="Author's user ID")
    created: datetime | None = Field(
        default=None, description="Timestamp when the child was posted"
    )
    updated: datetime | None = Field(
        default=None,
        description="Timestamp when the child was last edited",
    )
    anon: AnonymityLevel = Field(
        default=AnonymityLevel.NO,
        description="Anonymity level of the author",
    )
    no_answer: bool = Field(
        default=False, description="Whether this follow-up has no answer yet"
    )
    followed: bool = Field(
        default=False,
        description="Whether the current user is following this element",
    )


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

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Unique identifier for this answer")
    uid: str = Field(default="", description="Author's user ID")
    content: str = Field(default="", description="Answer body content (HTML)")
    created: datetime | None = Field(
        default=None, description="Timestamp when the answer was posted"
    )
    updated: datetime | None = Field(
        default=None,
        description="Timestamp when the answer was last edited",
    )
    votes: int = Field(
        default=0, description="Number of votes/endorsements on this answer"
    )
    endorsements: list[Endorsement] = Field(
        default_factory=list, description="List of endorsement records"
    )
    is_instructor_answer: bool = Field(
        default=False, description="Whether the author is an instructor"
    )
    is_student_answer: bool = Field(
        default=False, description="Whether the author is a student"
    )
    rated: bool = Field(
        default=False,
        description="Whether the current user has rated this answer",
    )
    folder: str = Field(default="", description="Folder assignment for this answer")


class StudentInfo(BaseModel):
    """Student-specific information attached to a post.

    Attributes:
        uid: Student's user ID.
        name: Student display name.
        email: Student email address.
        role: Student role string.
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    uid: str = Field(default="", description="Student's user ID")
    name: str = Field(default="", description="Student display name")
    email: str = Field(default="", description="Student email address")
    role: str = Field(default="", description="Student role string")


class PublishingOptions(BaseModel):
    """Options for post creation/publishing behavior.

    Attributes:
        bypass_email: Skip sending email notifications for this post.
            Serialized as ``bypass_email`` in the API.
        silent_update: Skip "updated post" notifications.
            Serialized as ``no_up_notify`` in the API.
        anonymity: Anonymity level: ``"no"`` (real name), ``"stud"``
            (students anonymous), ``"all"`` (everyone anonymous).
    """

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    bypass_email: bool = Field(
        default=False,
        serialization_alias="bypass_email",
        description="Skip sending email notifications for this post",
    )
    silent_update: bool = Field(
        default=False,
        serialization_alias="no_up_notify",
        description="Skip updated-post notifications",
    )
    anonymity: Literal["no", "stud", "all"] = Field(
        default="no", description="Anonymity level: no, stud, or all"
    )

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

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    name: str = Field(default="", description="Configuration name or label")
    instructor_note: str = Field(default="", description="Note from the instructor, if set")
    created: str = Field(default="", description="Timestamp when the configuration was created")


class Post(BaseModel):
    """A Piazza post with full lifecycle data.

    Supports dot-notation access for all fields. Fields map directly
    from Piazza's internal JSON API structure.

    Attributes:
        id: Unique post identifier (e.g. ``"j5yj4g5d4p2qg3"``).
        type: Post type (question, note, poll).
        title: Post title/subject line.
        subject: Alternative subject text (alias for title in some contexts).
        author: Author's email or user identifier.
        created_at: Timestamp when the post was created.
        updated_at: Timestamp of the last update.
        nr: Numeric post number within the network (e.g. 42).
        raw: Raw API response dict for advanced use cases.
        tags: List of user-defined tags.
        folder: Folder name the post belongs to.
        status: Post lifecycle status (active, resolved, closed, etc.).
        views: Total view count.
        unique_views: Unique viewer count (None if not available).
        students: Student participant info.
        followups: Follow-up questions/comments on this post.
        answers: Answer posts on this post.
        change_log: Edit history entries.
        endorsements: Endorsement/upvote records.
        config: Post configuration (instructor-only, etc.).
        children: Child items (answers, follow-ups, comments).
        user_name: Display name of the author.
        visibility: Access level (public, instructors, group).
        revisions: Full revision history.
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    id: str = Field(description="Unique post identifier (e.g. j5yj4g5d4p2qg3)")
    type: PostType = Field(default=PostType.NOTE, description="Post type (question, note, poll)")
    title: str = Field(default="", description="Post title/subject line")
    subject: str = Field(default="", description="Alternative subject text")
    author: str = Field(default="", description="Author's email or user identifier")
    created_at: datetime | None = Field(
        default=None, description="Timestamp when the post was created"
    )
    updated_at: datetime | None = Field(
        default=None, description="Timestamp of the last update"
    )
    nr: int = Field(
        default=0, description="Numeric post number within the network"
    )
    raw: dict[str, Any] = Field(
        default_factory=dict,
        description="Raw API response dict for advanced use cases",
    )
    tags: list[str] = Field(
        default_factory=list, description="List of user-defined tags"
    )
    folder: str = Field(default="", description="Folder name the post belongs to")
    status: PostStatus = Field(
        default=PostStatus.ACTIVE, description="Post lifecycle status"
    )
    views: int = Field(default=0, description="Total view count")
    unique_views: int | None = Field(
        default=None, description="Unique viewer count"
    )
    students: list[StudentInfo] = Field(
        default_factory=list, description="Student participant info"
    )
    followups: list[FollowUp] = Field(
        default_factory=list,
        description="Follow-up questions/comments on this post",
    )
    answers: list[Answer] = Field(
        default_factory=list, description="Answer posts on this post"
    )
    change_log: list[ChangeLogEntry] = Field(
        default_factory=list, description="Edit history entries"
    )
    endorsements: list[Endorsement] = Field(
        default_factory=list, description="Endorsement/upvote records"
    )
    config: PostConfig = Field(
        default_factory=PostConfig,
        description="Post configuration (instructor-only, etc.)",
    )
    children: list[Child] = Field(
        default_factory=list,
        description="Child items (answers, follow-ups, comments)",
    )
    user_name: str = Field(default="", description="Display name of the author")
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        description="Access level (public, instructors, group)",
    )
    revisions: list[PostRevision] = Field(default_factory=list, description="Full revision history")

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


class PostCreatedResponse(BaseModel):
    """Response from creating a new post or follow-up.

    Attributes:
        id: The ID assigned to the newly created post or follow-up.
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]
    id: str = Field(description="New post or follow-up ID")


class AssetUploadResponse(BaseModel):
    """Response from uploading a file asset.

    Attributes:
        id: The asset's unique identifier.
        url: The pre-signed upload URL (if available).
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]
    id: str = Field(description="Asset identifier")
    url: str | None = Field(default=None, description="Pre-signed upload URL")
