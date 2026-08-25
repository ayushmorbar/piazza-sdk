"""User model for Piazza SDK."""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class User(BaseModel):
    """User information.

    Attributes:
        id: User identifier.
        name: User's display name.
        email: User's email address.
        role: User's roles (student, instructor, ta, admin).
        is_instructor: Whether user is an instructor.
        is_student: Whether user is an student.
        is_ta: Whether user is a teaching assistant.
        is_admin: Whether user is an admin.
        class_roles: Mapping of network ID to role string for this user.
        endorsement_given: Number of endorsements given.
        photo_url: Profile photo URL.
        photo: Photo data.
        schools: List of school names.
        all_classes: List of all enrolled classes.
        contact: Contact information.
        links: User profile links.
        profile_settings: Profile display settings.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    id: str = Field(
        validation_alias=AliasChoices("id", "user_id"), description="Unique user identifier"
    )
    name: str = Field(default="", description="User's display name")
    email: str = Field(default="", description="User's email address")
    role: list[str] = Field(default_factory=list, description="User's roles")
    is_instructor: bool = Field(default=False, description="Whether user is an instructor")
    is_student: bool = Field(default=True, description="Whether user is a student")
    is_ta: bool = Field(default=False, description="Whether user is a teaching assistant")
    is_admin: bool = Field(default=False, description="Whether user is an admin")
    class_roles: dict[str, str] = Field(
        default_factory=dict, description="Mapping of network ID to role string"
    )
    endorsement_given: int | None = Field(default=None, description="Number of endorsements given")
    photo_url: str | None = Field(default=None, description="Profile photo URL")
    photo: dict[str, Any] | None = Field(default=None, description="Photo data")
    schools: list[str] = Field(default_factory=list, description="List of school names")
    all_classes: list[dict[str, Any]] = Field(
        default_factory=list, description="List of all enrolled classes"
    )
    contact: dict[str, Any] | None = Field(default=None, description="Contact information")
    links: list[dict[str, Any]] = Field(default_factory=list, description="User profile links")
    profile_settings: dict[str, Any] | None = Field(
        default=None, description="Profile display settings"
    )
    academics: dict[str, Any] | None = Field(
        default=None, description="User's academic information"
    )
    last_update: str | None = Field(default=None, description="Timestamp of last profile update")
    school: str | None = Field(default=None, description="Primary school name")
    school_id: str | None = Field(default=None, description="Primary school identifier")
    tags: list[str] = Field(default_factory=list, description="User profile tags")

    def get_classes_by_role(self, role: str) -> list[str]:
        """Return network IDs where the user has the specified role.

        Args:
            role: Role string to filter by (e.g., "student", "instructor").

        Returns:
            List of network IDs matching the given role.
        """
        return [nid for nid, r in self.class_roles.items() if r == role]

    @field_validator("all_classes", mode="before")
    @classmethod
    def _parse_all_classes(cls, v: Any) -> list[dict[str, Any]]:
        """Safely convert a dict of classes to a list of dicts."""
        if isinstance(v, dict):
            entries = []
            for nid, value in v.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("nid", nid)
                    entries.append(item)
            return entries
        if isinstance(v, list):
            return [item for item in v if isinstance(item, dict)]
        return []


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

    model_config = ConfigDict(slots=True, populate_by_name=True, extra="forbid")  # type: ignore[typeddict-unknown-key]

    digest_frequency: str = Field(
        default="daily", description="Email digest frequency (real_time, daily, weekly, never)"
    )
    digest_hour: int = Field(
        default=9, ge=0, le=23, description="Hour of day (0-23) to send digest emails"
    )
    email_new_post: bool = Field(default=True, description="Email on new posts")
    email_new_followup: bool = Field(default=True, description="Email on new follow-ups")
    email_new_answer: bool = Field(default=True, description="Email on new answers")
    email_new_comment: bool = Field(default=False, description="Email on new comments")
    push_new_post: bool = Field(default=True, description="Push-notify on new posts")
    push_new_followup: bool = Field(default=True, description="Push-notify on new follow-ups")
    push_new_answer: bool = Field(default=True, description="Push-notify on new answers")
    show_student_names: bool = Field(default=True, description="Show student names publicly")


class EmailPrefEntry(BaseModel):
    """Per-network email notification settings from ``user.status``.

    Mirrors the wire shape of ``result.config.email_prefs[nid]``. All
    fields are optional so callers can build *partial* entries for
    read-modify-write merges; the domain layer serializes with
    ``exclude_unset`` semantics against the raw payload to avoid
    wiping unspecified flags.

    Attributes:
        auto_follow: Auto-follow setting (string or null on the wire).
        new: Notification mode for new posts
            (e.g. ``"instantly"``, ``"daily"``, ``"no-emails"``).
        updates: Notification mode for updates to existing content.
        no_events: Whether event notifications are suppressed.
        throttle: Email throttling value.
    """

    model_config = ConfigDict(slots=True, extra="ignore")  # type: ignore[typeddict-unknown-key]

    auto_follow: str | bool | None = Field(
        default=None, description="Auto-follow setting (observed as bool or string on the wire)"
    )
    new: str | None = Field(
        default=None,
        description='Notification mode for new posts ("instantly", "daily", "no-emails", ...)',
    )
    updates: str | None = Field(default=None, description="Notification mode for updates")
    no_events: bool | None = Field(default=None, description="Whether event emails are off")
    throttle: int | None = Field(default=None, description="Email throttling value")
