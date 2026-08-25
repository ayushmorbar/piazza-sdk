"""Post-related models for Piazza SDK.

Covers the full post lifecycle: posts, follow-ups, answers, endorsements,
and change log entries.
"""

from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

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
        tag: Endorsement tag (e.g. ``"good"``, ``"great"``).
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    role: str = Field(default="", description="Endorser's role (e.g. student, instructor)")
    name: str = Field(default="", description="Endorser display name")
    endorser: dict[str, Any] | None = Field(
        default=None, description="Endorser user info (id, name, photo, role, etc.)"
    )
    admin: bool = Field(default=False, description="Whether the endorser is a network admin")
    photo: str | None = Field(default=None, description="Endorser photo path, if available")
    id: str = Field(default="", description="Endorsement record identifier")
    photo_url: str | None = Field(default=None, description="Full URL to the endorser's photo")
    published: bool = Field(default=False, description="Whether the endorsement is published")
    us: bool = Field(default=False, description="Whether the endorser is a course staff member")
    facebook_id: str | None = Field(
        default=None, description="Facebook ID of the endorser, if linked"
    )
    tag: str | None = Field(default=None, description="Endorsement tag (e.g. good, great)")


class ChangeLogEntry(BaseModel):
    """An entry in a post's change log.

    Attributes:
        id: Unique identifier for this change log entry.
        anon: Anonymity level of the change author.
        uid: User ID of the person who made the change.
        data: Free-form data associated with the change.
        to: Target value after the change, if applicable.
        v: Visibility of the change record.
        type: Type of change (create, update, endorse, etc.).
        when: Timestamp when the change occurred (string or epoch ms).
        cid: Child element ID the change relates to, if any.
        edited: Whether this entry represents an edit.
    """

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Unique identifier for this change log entry")
    anon: AnonymityLevel = Field(
        default=AnonymityLevel.NO, description="Anonymity level of the change author"
    )
    uid: str = Field(default="", alias="u", description="User ID of the person who made the change")
    data: str | None = Field(default=None, description="Free-form data associated with the change")
    to: str | None = Field(default=None, description="Target value after the change, if applicable")
    v: Visibility = Field(default=Visibility.PUBLIC, description="Visibility of the change record")
    type: ChangeType = Field(
        default=ChangeType.CREATE,
        alias="n",
        description="Type of change (create, update, endorse, etc.)",
    )
    when: str | None = Field(
        default=None, alias="t", description="Timestamp when the change occurred"
    )
    cid: str = Field(default="", description="Child element ID the change relates to, if any")
    edited: bool = Field(default=False, description="Whether this entry represents an edit")


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

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

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

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Unique identifier for this follow-up")
    uid: str = Field(default="", alias="u", description="Author's user ID")
    subject: str = Field(default="", description="Follow-up subject line")
    content: str = Field(default="", description="Follow-up body content (HTML)")
    created: datetime | None = Field(
        default=None, description="Timestamp when the follow-up was posted"
    )
    updated: datetime | None = Field(
        default=None, description="Timestamp when the follow-up was last edited"
    )
    anon: AnonymityLevel = Field(
        default=AnonymityLevel.NO, description="Anonymity level of the author"
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
        role: Author role(s).
        instructor: Whether authored by an instructor.
        endorsers: List of users who endorsed this element.
        uid_unique: Unique registration identifier for the user.
    """

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Unique identifier for this child element")
    type: str = Field(default="", description="Element type (e.g. followup, answer)")
    subject: str = Field(default="", description="Child subject line")
    content: str = Field(default="", description="Child body content (HTML)")
    uid: str = Field(default="", alias="u", description="Author's user ID")
    created: datetime | None = Field(
        default=None, description="Timestamp when the child was posted"
    )
    updated: datetime | None = Field(
        default=None, description="Timestamp when the child was last edited"
    )
    anon: AnonymityLevel = Field(
        default=AnonymityLevel.NO, description="Anonymity level of the author"
    )
    no_answer: bool = Field(default=False, description="Whether this follow-up has no answer yet")
    followed: bool = Field(
        default=False, description="Whether the current user is following this element"
    )
    role: list[str] = Field(default_factory=list, description="Author role(s)")
    instructor: bool | None = Field(default=None, description="Whether authored by an instructor")
    endorsers: list[dict[str, Any]] | None = Field(
        default=None, description="List of users who endorsed this element"
    )
    uid_unique: str | None = Field(
        default=None, description="Unique registration identifier for the user"
    )
    is_tag_endorse: bool = Field(
        default=False, description="Whether current user endorsed this answer"
    )
    tag_endorse: list[dict[str, Any]] = Field(
        default_factory=list, description="List of users who endorsed this answer"
    )
    tag_endorse_arr: list[str] = Field(
        default_factory=list, description="List of user IDs who endorsed this answer"
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

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Unique identifier for this answer")
    uid: str = Field(default="", description="Author's user ID")
    content: str = Field(default="", description="Answer body content (HTML)")
    created: datetime | None = Field(
        default=None, description="Timestamp when the answer was posted"
    )
    updated: datetime | None = Field(
        default=None, description="Timestamp when the answer was last edited"
    )
    votes: int = Field(default=0, description="Number of votes/endorsements on this answer")
    endorsements: list[Endorsement] = Field(
        default_factory=list, description="List of endorsement records"
    )
    is_instructor_answer: bool = Field(
        default=False, description="Whether the author is an instructor"
    )
    is_student_answer: bool = Field(default=False, description="Whether the author is a student")
    rated: bool = Field(default=False, description="Whether the current user has rated this answer")
    folder: str = Field(default="", description="Folder assignment for this answer")


class StudentInfo(BaseModel):
    """Student-specific information attached to a post.

    Attributes:
        uid: Student's user ID.
        name: Student display name.
        email: Student email address.
        role: Student role string.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

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
            "options[bypass_email]": int(self.bypass_email),
            "options[no_up_notify]": int(self.silent_update),
            "options[anonymous]": self.anonymity,
        }


class PostConfig(BaseModel):
    """Post configuration settings.

    Attributes:
        editor: Editor type used for this post (e.g., ``"rich_text"``).
        has_emails_sent: Whether notification emails have been sent for this post.
        is_default: Whether this post uses default configuration.
        schedule_later_time: Scheduled time for later posting, if any.
        allow_anon: Whether anonymous posting is allowed.
        schedule_later: Whether the post is scheduled for later.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    editor: str = Field(default="rich_text", description="Editor type for this post")
    has_emails_sent: bool = Field(default=False, description="Whether emails have been sent")
    is_default: bool = Field(default=True, description="Whether this is default config")
    schedule_later_time: str | None = Field(default=None, description="Scheduled post time")
    allow_anon: bool = Field(default=False, description="Whether anonymous posting is allowed")
    schedule_later: bool = Field(default=False, description="Whether post is scheduled for later")


class Post(BaseModel):
    """A Piazza post with full lifecycle data.

    Supports dot-notation access for all fields. Fields map directly
    from Piazza's internal JSON API structure.

    Attributes:
        id: Unique post identifier (e.g. ``"j5yj4g5d4p2qg3"``).
        nr: Numeric post number within the network (e.g. 42).
        type: Post type (question, note, poll).
        title: Post title/subject line.
        subject: Alternative subject text (alias for title in some contexts).
        author: Author's email or user identifier.
        uid: Author's user ID.
        email: Author's email address.
        created: Timestamp when the post was created (ISO string).
        updated: Timestamp of the last update (ISO string).
        bucket: Folder/topic bucket name.
        folders: List of folder names the post belongs to.
        tags: List of user-defined tags.
        status: Post lifecycle status (active, resolved, closed, etc.).
        views: Total view count.
        unique_views: Unique viewer count (None if not available).
        default_anonymity: Whether the post is anonymous by default.
        is_mine: Whether the current user authored this post.
        no_answer: Whether no answer has been accepted.
        followed: Whether the current user is following this post.
        config: Post configuration (editor, emails, schedule).
        config_data: Additional config data from the API.
        question_stats: Question statistics from the API.
        book: Whether the post is bookmarked.
        users: User info dict from the API.
        raw: Raw API response dict for advanced use cases.
        students: Student participant info.
        followups: Follow-up questions/comments on this post.
        answers: Answer posts on this post.
        change_log: Edit history entries.
        endorsements: Endorsement/upvote records.
        children: Child items (answers, follow-ups, comments).
        user_name: Display name of the author.
        visibility: Access level (public, instructors, group).
        revisions: Full revision history.
    """

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(description="Unique post identifier (e.g. j5yj4g5d4p2qg3)")
    nr: int = Field(default=0, description="Numeric post number within the network")
    type: PostType = Field(default=PostType.NOTE, description="Post type (question, note, poll)")
    title: str = Field(default="", description="Post title/subject line")
    subject: str = Field(default="", description="Alternative subject text")
    author: str = Field(default="", description="Author's email or user identifier")
    uid: str = Field(default="", description="Author's user ID")
    email: str = Field(default="", description="Author's email address")
    created: datetime | None = Field(
        default=None, description="Timestamp when the post was created"
    )
    updated: datetime | None = Field(default=None, description="Timestamp of the last update")
    bucket: str = Field(default="", description="Folder/topic bucket name")
    folders: list[str] = Field(default_factory=list, description="Folder names the post belongs to")
    tags: list[str] = Field(default_factory=list, description="List of user-defined tags")
    status: PostStatus = Field(default=PostStatus.ACTIVE, description="Post lifecycle status")
    views: int = Field(default=0, description="Total view count")
    unique_views: int | None = Field(default=None, description="Unique viewer count")
    default_anonymity: str | bool = Field(
        default=False, description="Whether the post is anonymous by default"
    )
    is_mine: bool = Field(default=False, description="Whether the current user authored this post")
    no_answer: bool = Field(default=False, description="Whether no answer has been accepted")
    followed: bool = Field(
        default=False, description="Whether the current user is following this post"
    )
    config: PostConfig = Field(
        default_factory=PostConfig, description="Post configuration (editor, emails, schedule)"
    )
    config_data: dict[str, Any] = Field(
        default_factory=dict, description="Additional config data from the API"
    )
    question_stats: dict[str, Any] = Field(
        default_factory=dict, description="Question statistics from the API"
    )
    book: bool = Field(default=False, description="Whether the post is bookmarked")
    users: dict[str, Any] = Field(default_factory=dict, description="User info dict from the API")
    raw: dict[str, Any] = Field(
        default_factory=dict, description="Raw API response dict for advanced use cases"
    )
    students: list[StudentInfo] = Field(
        default_factory=list, description="Student participant info"
    )
    followups: list[FollowUp] = Field(
        default_factory=list, description="Follow-up questions/comments on this post"
    )
    answers: list[Answer] = Field(default_factory=list, description="Answer posts on this post")
    change_log: list[ChangeLogEntry] = Field(
        default_factory=list, alias="log", description="Edit history entries"
    )
    endorsements: list[Endorsement] = Field(
        default_factory=list, description="Endorsement/upvote records"
    )
    children: list[Child] = Field(
        default_factory=list, description="Child items (answers, follow-ups, comments)"
    )
    user_name: str = Field(default="", description="Display name of the author")
    visibility: Visibility = Field(
        default=Visibility.PUBLIC, description="Access level (public, instructors, group)"
    )
    revisions: list[PostRevision] = Field(default_factory=list, description="Full revision history")
    enhanced: dict[str, Any] | None = Field(default=None, description="Enhanced content data")
    bumped: bool = Field(default=False, description="Whether the post has been bumped")
    bm_type: str | None = Field(default=None, description="Bookmark type")
    bm_visible: bool | None = Field(default=None, description="Bookmark visibility")
    request_instructor_response: bool = Field(
        default=False, description="Whether instructor response is requested"
    )
    request_all_instructor_response: bool = Field(
        default=False, description="Whether all instructors are requested to respond"
    )
    clobber: str | None = Field(default=None, description="Clobber state")
    user_endorse: dict[str, Any] | None = Field(default=None, description="User endorsement data")
    tag: str | None = Field(default=None, description="Post tag")

    @model_validator(mode="after")
    def _auto_number_revisions(self) -> Post:
        """Auto-increment revision numbers from list index.

        The Piazza wire format does not include a ``revision`` field in
        ``history`` entries.  When all revisions carry the default value
        (0), assign sequential 1-based numbers matching the chronological
        order returned by the API.
        """
        if self.revisions and all(r.revision == 0 for r in self.revisions):
            for idx, rev in enumerate(self.revisions, start=1):
                rev.revision = idx
        return self

    # Backward compat: expose first folder as scalar property
    @property
    def folder(self) -> str:
        """First folder name (backward compat). Use ``folders`` for the full list."""
        return self.folders[0] if self.folders else ""

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

    @property
    def is_upvoted(self) -> bool:
        """Whether the current user has upvoted this post.

        Checks the ``is_tag_good`` field from the live API response.

        Example:
            ```python
            from piazza_sdk.models.post import Post

            # After fetching a post from the network:
            post = await network.get_post("cl7k3x2f5")

            if post.is_upvoted:
                print(f"You have upvoted '{post.title}'")
            else:
                print("You have not upvoted this post yet")
            ```
        """
        return bool(self.raw.get("is_tag_good"))

    def normalized(self) -> Post:
        """Return a new Post with HTML content normalized to Markdown.

        Performs on-demand normalization of all text content fields:
        ``title``, ``subject``, and content within ``children``,
        ``answers``, and ``followups``.

        The original Post instance is unchanged; the method returns a
        new instance with normalized strings.

        Returns:
            New Post instance with Markdown-normalized content.
        """
        from piazza_sdk.utils.normalization import normalize_content  # noqa: PLC0415

        def _norm(s: str) -> str:
            return normalize_content(s) if s else s

        return Post(
            id=self.id,
            nr=self.nr,
            type=self.type,
            title=_norm(self.title),
            subject=_norm(self.subject),
            author=self.author,
            uid=self.uid,
            email=self.email,
            created=self.created,
            updated=self.updated,
            bucket=self.bucket,
            folders=self.folders,
            tags=self.tags,
            status=self.status,
            views=self.views,
            unique_views=self.unique_views,
            default_anonymity=self.default_anonymity,
            is_mine=self.is_mine,
            no_answer=self.no_answer,
            followed=self.followed,
            config=self.config,
            config_data=self.config_data,
            question_stats=self.question_stats,
            book=self.book,
            users=self.users,
            raw=self.raw,
            students=self.students,
            followups=[
                FollowUp(
                    id=f.id,
                    u=f.uid,
                    subject=_norm(f.subject),
                    content=_norm(f.content),
                    created=f.created,
                    updated=f.updated,
                    anon=f.anon,
                )
                for f in self.followups
            ],
            answers=[
                Answer(
                    id=a.id,
                    uid=a.uid,
                    content=_norm(a.content),
                    created=a.created,
                    updated=a.updated,
                    votes=a.votes,
                    endorsements=a.endorsements,
                    is_instructor_answer=a.is_instructor_answer,
                    is_student_answer=a.is_student_answer,
                    rated=a.rated,
                    folder=a.folder,
                )
                for a in self.answers
            ],
            log=self.change_log,
            endorsements=self.endorsements,
            children=[
                Child(
                    id=c.id,
                    type=c.type,
                    subject=_norm(c.subject),
                    content=_norm(c.content),
                    u=c.uid,
                    created=c.created,
                    updated=c.updated,
                    anon=c.anon,
                    no_answer=c.no_answer,
                    followed=c.followed,
                    role=c.role,
                    instructor=c.instructor,
                    endorsers=c.endorsers,
                    uid_unique=c.uid_unique,
                )
                for c in self.children
            ],
            user_name=self.user_name,
            visibility=self.visibility,
            revisions=[
                PostRevision(
                    revision=r.revision,
                    subject=_norm(r.subject),
                    content=_norm(r.content),
                    uid=r.uid,
                    created=r.created,
                )
                for r in self.revisions
            ],
            enhanced=self.enhanced,
            bumped=self.bumped,
            bm_type=self.bm_type,
            bm_visible=self.bm_visible,
            request_instructor_response=self.request_instructor_response,
            request_all_instructor_response=self.request_all_instructor_response,
            clobber=self.clobber,
            user_endorse=self.user_endorse,
            tag=self.tag,
        )


class PostCreatedResponse(BaseModel):
    """Response from creating a new post or follow-up.

    Attributes:
        id: The ID assigned to the newly created post or follow-up.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]
    id: str = Field(description="New post or follow-up ID")


class AssetUploadResponse(BaseModel):
    """Response from uploading a file asset.

    Attributes:
        id: The asset's unique identifier.
        url: The pre-signed upload URL (if available).
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]
    id: str = Field(description="Asset identifier")
    url: str | None = Field(default=None, description="Pre-signed upload URL")
