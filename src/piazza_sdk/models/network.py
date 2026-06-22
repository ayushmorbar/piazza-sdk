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
    """

    id: str = ""
    nid: str = ""
    name: str = ""
    course_number: str = ""
    course_title: str = ""
    instructor: str = ""
    term: str = ""
    year: str = ""
    users: int = 0
    posts: int = 0
    folders: list[str] = Field(default_factory=list)
    instructors: list[str] = Field(default_factory=list)
    status: str | None = None


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

    posts: int = 0
    resolved: int = 0
    unresolved: int = 0
    users: int = 0
    instructors: int = 0
    students: int = 0
    total_views: int = 0
    total_endorsements: int = 0

    @property
    def resolution_rate(self) -> float:
        """Percentage of questions that are resolved."""
        total = self.resolved + self.unresolved
        return (self.resolved / total * 100) if total > 0 else 0.0


class HallOfFameItem(BaseModel):
    """A single entry from the network's Hall of Fame.

    Attributes:
        uid: User ID of the student.
        votes: Number of upvotes/endorsements on the best answer.
        response_time_seconds: Time-to-answer in seconds.
        snippet: Text snippet of the best answer.
        timestamp: Unix epoch timestamp of the answer.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    uid: str | None = None
    votes: int | None = Field(default=None, alias="nr")
    response_time_seconds: int | None = Field(default=None, alias="time")
    snippet: str | None = Field(default=None, alias="text")
    timestamp: int | None = Field(default=None, alias="when")
