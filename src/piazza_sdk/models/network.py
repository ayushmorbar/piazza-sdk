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


class Statistics(BaseModel):
    """Course network statistics.

    Attributes:
        posts: Total number of posts.
        resolved: Number of resolved questions.
        unresolved: Number of unresolved questions.
        users: Total users participating.
        instructors: Number of instructors.
        students: Number of students.
        total_views: Aggregate view count.
        total_endorsements: Aggregate endorsement count.
    """

    model_config = ConfigDict(slots=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    posts: int = Field(default=0, description="Total number of posts")
    resolved: int = Field(default=0, description="Number of resolved questions")
    unresolved: int = Field(default=0, description="Number of unresolved questions")
    users: int = Field(default=0, description="Total users participating")
    instructors: int = Field(default=0, description="Number of instructors")
    students: int = Field(default=0, description="Number of students")
    total_views: int = Field(default=0, description="Aggregate view count")
    total_endorsements: int = Field(default=0, description="Aggregate endorsement count")

    @property
    def resolution_rate(self) -> float:
        """Percentage of questions that are resolved."""
        total = self.resolved + self.unresolved
        return (self.resolved / total * 100) if total > 0 else 0.0


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
