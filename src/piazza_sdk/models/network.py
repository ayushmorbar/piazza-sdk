"""Network-related models for Piazza SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from piazza_sdk.models.enums import UserRole


class RolePermissions(BaseModel):
    """Permission flags for one role within a network.

    Mirrors the union of permission fields observed across the
    ``admin``/``instructor``/``professor``/``student``/``ta`` entries of
    ``user.status`` → ``networks[].config.roles``. Unknown fields are
    tolerated (server-fed payload); unknown *actions* queried via
    :meth:`NetworkInfo.can` resolve to ``False``.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    admin_roster: bool = Field(default=False, description="Can access the admin roster")
    can_post_anonymous_all: bool = Field(
        default=False, description="Can post anonymously to everyone"
    )
    can_post_anonymous_members: bool = Field(
        default=False, description="Can post anonymously to class members"
    )
    expert_answer_create: bool = Field(default=False, description="Can create instructor answers")
    expert_answer_edit: bool = Field(default=False, description="Can edit instructor answers")
    expert_answer_endorse: bool = Field(default=False, description="Can endorse instructor answers")
    followup_edit: bool = Field(default=False, description="Can edit follow-ups")
    manage_folders: bool = Field(default=False, description="Can manage folders")
    manage_group_info: bool = Field(default=False, description="Can manage group info")
    manage_groups: bool = Field(default=False, description="Can manage groups")
    manage_resources: bool = Field(default=False, description="Can manage course resources")
    member_answer_create: bool = Field(default=False, description="Can create student answers")
    member_answer_edit: bool = Field(default=False, description="Can edit student answers")
    member_answer_endorse: bool = Field(default=False, description="Can endorse student answers")
    member_roster: bool = Field(default=False, description="Can access the member roster")
    new_followup: bool = Field(default=False, description="Can create follow-ups")
    new_post: bool = Field(default=False, description="Can create posts")
    question_delete: bool = Field(default=False, description="Can delete questions")
    question_edit: bool = Field(default=False, description="Can edit questions")


class NetworkRoles(BaseModel):
    """Per-role permission matrix from ``config.roles``.

    Attributes:
        admin: Permissions for network admins, or None when absent.
        instructor: Permissions for instructors, or None when absent.
        professor: Permissions for professors, or None when absent.
        student: Permissions for students, or None when absent.
        ta: Permissions for TAs, or None when absent.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    admin: RolePermissions | None = None
    instructor: RolePermissions | None = None
    professor: RolePermissions | None = None
    student: RolePermissions | None = None
    ta: RolePermissions | None = None


class ClassSections(BaseModel):
    """Class section enrollment config from ``config.class_sections``."""

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    allow_enroll: int = Field(default=0, description="Whether self-enrollment is allowed")
    sections: list[str] = Field(default_factory=list, description="Section names")


class NetworkConfig(BaseModel):
    """Network-level configuration from ``user.status`` → ``networks[].config``.

    Server-fed model: unknown keys are ignored so upstream additions do
    not break parsing.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    roles: NetworkRoles | None = Field(default=None, description="Per-role permission matrix")
    class_sections: ClassSections | None = Field(
        default=None, description="Class section enrollment config"
    )
    default_posts_to_private: bool | None = Field(
        default=None, description="Whether new posts default to private visibility"
    )
    disable_folders: bool | None = Field(default=None, description="Whether folders are disabled")
    disable_student_polls: bool | None = Field(
        default=None, description="Whether student polls are disabled"
    )
    public_visibility_settings: dict[str, Any] | None = Field(
        default=None, description="Public visibility configuration"
    )


class NetworkInfo(BaseModel):
    """Information about a Piazza network (course).

    Attributes:
        id: Piazza network identifier (numeric string).
        nid: Network ID used in API URLs.
        name: Display name for the course.
        course_number: Course catalog number (e.g. "CS 101").
        course_title: Full course title.
        instructor: Primary instructor name.
        term: Academic term (e.g. "Fall").
        year: Academic year string.
        users: Number of users enrolled.
        posts: Number of posts in the network.
        folders: List of folder names available in the network.
        instructors: List of instructor names.
        status: Network status string (e.g. "active"), or None.
        school_ext: School extension slug used in resource URLs.
        short_number: Short course number used in resource URLs.
        anonymity: Anonymity policy string for the network.
        auto_join: Auto-join policy string for the network.
        config: Parsed network configuration incl. role permissions.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(default="", description="Piazza network identifier (numeric string)")
    nid: str = Field(default="", description="Network ID used in API URLs")
    name: str = Field(default="", description="Display name for the course")
    course_number: str = Field(default="", description="Course catalog number (e.g. CS 101)")
    course_title: str = Field(default="", description="Full course title")
    instructor: str = Field(default="", description="Primary instructor name")
    term: str = Field(default="", description="Academic term (e.g. Fall)")
    year: str = Field(default="", description="Academic year string")
    users: int = Field(default=0, description="Number of users enrolled")
    posts: int = Field(default=0, description="Number of posts in the network")
    folders: list[str] = Field(
        default_factory=list, description="Folder names available in the network"
    )
    instructors: list[str] = Field(default_factory=list, description="Instructor names")
    status: str | None = Field(default=None, description="Network status string (e.g. active)")
    school_ext: str = Field(default="", description="School extension slug for resource URLs")
    short_number: str = Field(default="", description="Short course number for resource URLs")
    anonymity: str = Field(default="", description="Anonymity policy string")
    auto_join: str = Field(default="", description="Auto-join policy string")
    auth: str = Field(
        default="",
        description=(
            "Share-link token from user.status — feed to "
            "SessionStateManager.demo_login() or append to a demo_login URL"
        ),
    )
    config: NetworkConfig | None = Field(
        default=None, description="Parsed network configuration with role permissions"
    )

    @property
    def demo_login_url(self) -> str:
        """Build the "Share Your Class" demo-login URL for this course.

        Returns an empty string when the share token is absent (e.g. the
        entry came from ``all_classes`` rather than ``user.status``).
        """
        if not self.auth or not self.nid:
            return ""
        return f"https://piazza.com/demo_login?nid={self.nid}&auth={self.auth}"

    @property
    def resources_url(self) -> str:
        """Build the web Resources page URL for this course.

        Mirrors the reference client's URL shape:
        ``https://piazza.com/{school_ext}/{term}/{short_number}/home``
        where *term* is lower-cased without spaces.

        Returns an empty string when the required slugs are missing
        (e.g. the entry came from ``all_classes`` rather than
        ``user.status``).
        """
        if not self.school_ext or not self.short_number:
            return ""
        term = self.term.lower().replace(" ", "")
        return f"https://piazza.com/{self.school_ext}/{term}/{self.short_number}/home"

    def can(self, role: UserRole | str, action: str) -> bool:
        """Check whether *role* is permitted *action* in this network.

        Pre-flight capability check backed by the parsed
        ``config.roles`` permission matrix. Returns ``False`` (never
        raises) when the matrix is absent, the role is unknown, or the
        action is outside the modeled permission set.

        Args:
            role: Role name (e.g. ``UserRole.STUDENT`` or "instructor").
            action: Permission flag name (e.g. ``"new_post"``).

        Returns:
            True when the permission flag is explicitly set for the role.
        """
        roles = self.config.roles if self.config is not None else None
        if roles is None:
            return False
        perms: RolePermissions | None = getattr(roles, str(role).lower(), None)
        if perms is None:
            return False
        return bool(getattr(perms, action, False))


class StatisticsStudents(BaseModel):
    """Student engagement statistics.

    Attributes:
        total: Total number of students.
        viewed: Number of students who viewed posts.
        viewed_answered: Number of students who viewed and answered.
        viewed_instructor_note: Number of students who viewed instructor notes.
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    total: int = Field(default=0, description="Total number of students")
    viewed: int = Field(default=0, description="Number of students who viewed posts")
    viewed_answered: int = Field(default=0, description="Students who viewed and answered")
    viewed_instructor_note: int = Field(
        default=0, description="Students who viewed instructor notes"
    )


class InstructorStats(BaseModel):
    """Instructor and course response statistics from network.get_instructor_stats.

    Attributes:
        total_posts: Total number of posts in the network.
        unanswered_questions_on_timer: Number of unanswered questions on timer.
        unanswered_questions: Number of unanswered questions.
        unanswered_questions_on_timer_due: Number of unanswered questions due on timer.
        total_contributions: Total contributions count.
        instructors_response: Total instructor responses count.
        response_time: Average response time (e.g. in minutes/hours).
        students_response: Total student responses count.
        unanswered_followups: Number of unanswered follow-up discussions.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    total_posts: int = Field(default=0, description="Total number of posts")
    unanswered_questions_on_timer: int = Field(
        default=0, description="Unanswered questions on timer"
    )
    unanswered_questions: int = Field(default=0, description="Unanswered questions count")
    unanswered_questions_on_timer_due: int = Field(
        default=0, description="Unanswered questions due on timer"
    )
    total_contributions: int = Field(default=0, description="Total contributions count")
    instructors_response: int = Field(default=0, description="Instructor responses count")
    response_time: int | float = Field(default=0, description="Average response time")
    students_response: int = Field(default=0, description="Student responses count")
    unanswered_followups: int = Field(default=0, description="Unanswered follow-ups count")


class StatisticsUser(BaseModel):
    """A single user entry from network statistics.

    Attributes:
        user_id: Piazza user ID.
        name: Display name.
        email: User email.
        days: Days active.
        posts: Number of posts.
        asks: Number of questions asked.
        answers: Number of answers given.
        views: Number of views.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    user_id: str = Field(default="", description="Piazza user ID")
    name: str = Field(default="", description="Display name")
    email: str = Field(default="", description="User email")
    lti_ids: list[str] = Field(default_factory=list, description="LTI identifiers")
    days: int = Field(default=0, description="Days active")
    posts: int = Field(default=0, description="Number of posts")
    asks: int = Field(default=0, description="Number of questions asked")
    answers: int = Field(default=0, description="Number of answers given")
    views: int = Field(default=0, description="Number of views")


class StatisticsTotals(BaseModel):
    """Aggregate totals from network statistics.

    Attributes:
        posts: Total posts.
        questions: Total questions.
        i_answers: Instructor answers.
        s_answers: Student answers.
        net_time: Net response time.
        anon_pool: Anonymous pool size.
        response_time: Average response time.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    posts: int = Field(default=0, description="Total posts")
    questions: int = Field(default=0, description="Total questions")
    i_answers: int | None = Field(default=None, description="Instructor answers")
    s_answers: int | None = Field(default=None, description="Student answers")
    net_time: int | None = Field(default=None, description="Net response time")
    anon_pool: int = Field(default=0, description="Anonymous pool size")
    response_time: float | None = Field(default=None, description="Average response time")


class StatisticsDaily(BaseModel):
    """Daily activity breakdown.

    Attributes:
        day: Date string (e.g. "06/24").
        users: Number of users that day.
        posts: Number of posts that day.
        questions: Number of questions that day.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    day: str = Field(default="", description="Date string")
    users: int | None = Field(default=None, description="Number of users that day")
    posts: int = Field(default=0, description="Number of posts that day")
    questions: int = Field(default=0, description="Number of questions that day")


class Statistics(BaseModel):
    """Course network statistics from /main/api network.get_stats.

    Attributes:
        daily: Daily activity breakdown.
        users: User statistics list.
        profs: Instructor statistics list.
        total: Aggregate totals.
        top_users: Top contributing users.
        top_askers: Top question askers.
        top_answerers: Top answer providers.
        top_listeners: Top listeners.
        top_good_q: Top good questions.
        top_good_a: Top good answers.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    daily: list[StatisticsDaily] = Field(
        default_factory=list, description="Daily activity breakdown"
    )
    users: list[StatisticsUser] = Field(default_factory=list, description="User statistics list")
    profs: list[StatisticsUser] = Field(
        default_factory=list, description="Instructor statistics list"
    )
    total: StatisticsTotals = Field(
        default_factory=StatisticsTotals, description="Aggregate totals"
    )
    top_users: list[StatisticsUser] = Field(
        default_factory=list, description="Top contributing users"
    )
    top_askers: list[StatisticsUser] = Field(
        default_factory=list, description="Top question askers"
    )
    top_answerers: list[StatisticsUser] = Field(
        default_factory=list, description="Top answer providers"
    )
    top_listeners: list[StatisticsUser] = Field(default_factory=list, description="Top listeners")
    top_good_q: list[StatisticsUser] = Field(default_factory=list, description="Top good questions")
    top_good_a: list[StatisticsUser] = Field(default_factory=list, description="Top good answers")


class HallOfFameItem(BaseModel):
    """A single entry from the network's Hall of Fame.

    Attributes:
        uid: User ID of the student.
        votes: Number of upvotes/endorsements on the best answer
            (serialized as ``nr`` in the API).
        response_time_seconds: Time-to-answer in seconds
            (serialized as ``time`` in the API).
        snippet: Text snippet of the best answer
            (serialized as ``text`` in the API).
        timestamp: Unix epoch timestamp of the answer
            (serialized as ``when`` in the API).
    """

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    uid: str | None = None
    votes: int | None = Field(default=None, alias="nr")
    response_time_seconds: int | None = Field(default=None, alias="time")
    snippet: str | None = Field(default=None, alias="text")
    timestamp: int | None = Field(default=None, alias="when")
