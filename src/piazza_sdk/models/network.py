"""Network-related models for Piazza SDK."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


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
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

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
