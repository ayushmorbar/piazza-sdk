"""User model for Piazza SDK."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from piazza_sdk.models.enums import UserRole


class User(BaseModel):
    """User information.

    Attributes:
        id: User identifier.
        name: User's display name.
        email: User's email address.
        role: User's role (student, instructor, ta, admin).
        is_instructor: Whether user is an instructor.
        is_student: Whether user is a student.
        is_ta: Whether user is a teaching assistant.
        is_admin: Whether user is an admin.
        class_roles: Mapping of network ID to role string for this user.
    """

    id: str
    name: str = ""
    email: str = ""
    role: UserRole = UserRole.STUDENT
    is_instructor: bool = False
    is_student: bool = True
    is_ta: bool = False
    is_admin: bool = False
    class_roles: dict[str, str] = Field(default_factory=dict)

    def get_classes_by_role(self, role: str) -> list[str]:
        """Return network IDs where the user has the specified role.

        Args:
            role: Role string to filter by (e.g., "student", "instructor").

        Returns:
            List of network IDs matching the given role.
        """
        return [nid for nid, r in self.class_roles.items() if r == role]


class UserPreferences(BaseModel):
    """User notification and digest preferences.

    Models the user's configurable preferences for email digests,
    push notifications, and content display. Use
    ``Network.update_preferences()`` to persist changes.

    Usage::

        prefs = UserPreferences(digest_frequency="daily")
        await network.update_preferences(prefs)

    Attributes:
        digest_frequency: How often to send digest emails
            (``"real_time"``, ``"daily"``, ``"weekly"``, ``"never"``).
        digest_hour: Hour of day (0-23) to send digest emails.
        email_new_post: Whether to email on new posts.
        email_new_followup: Whether to email on new follow-ups.
        email_new_answer: Whether to email on new answers.
        email_new_comment: Whether to email on new comments.
        push_new_post: Whether to push-notify on new posts.
        push_new_followup: Whether to push-notify on new follow-ups.
        push_new_answer: Whether to push-notify on new answers.
        show_student_names: Whether to show student names publicly.
    """

    model_config = ConfigDict(populate_by_name=True)

    digest_frequency: str = "daily"
    digest_hour: int = 9
    email_new_post: bool = True
    email_new_followup: bool = True
    email_new_answer: bool = True
    email_new_comment: bool = False
    push_new_post: bool = True
    push_new_followup: bool = True
    push_new_answer: bool = True
    show_student_names: bool = True
