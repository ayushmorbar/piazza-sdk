"""Domain logic for network-level operations (office hours, settings)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from piazza_sdk.exceptions import NotFoundError, PiazzaSDKError
from piazza_sdk.models.network import ClassSections, NetworkConfig, NetworkInfo, NetworkRoles

__all__ = [
    "get_network_info",
    "parse_network_entry",
    "update_course_description",
    "update_general_information",
    "update_office_hours",
    "add_students",
    "remove_users",
]

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager


def parse_network_entry(entry: dict[str, Any]) -> NetworkInfo:
    """Parse one ``user.status`` → ``networks[]`` entry into :class:`NetworkInfo`.

    Explicit defensive mapping keeps the strict-ish model construction
    tolerant of missing keys. Unknown top-level keys are ignored by the
    model itself.

    Args:
        entry: Raw network dictionary from ``user.status``.

    Returns:
        Parsed NetworkInfo with embedded config/roles when present.
    """
    raw_config = entry.get("config")
    config: NetworkConfig | None = None
    if isinstance(raw_config, dict):
        raw_roles = raw_config.get("roles")
        roles: NetworkRoles | None = None
        if isinstance(raw_roles, dict):
            roles = NetworkRoles.model_validate(raw_roles)
        raw_sections = raw_config.get("class_sections")
        sections: ClassSections | None = (
            ClassSections.model_validate(raw_sections) if isinstance(raw_sections, dict) else None
        )
        config = NetworkConfig(
            roles=roles,
            class_sections=sections,
            default_posts_to_private=raw_config.get("default_posts_to_private"),
            disable_folders=raw_config.get("disable_folders"),
            public_visibility_settings=(
                raw_config.get("public_visibility_settings")
                if isinstance(raw_config.get("public_visibility_settings"), dict)
                else None
            ),
        )
    return NetworkInfo(
        id=str(entry.get("id", "")),
        nid=str(entry.get("id", "")),
        name=str(entry.get("name", "")),
        course_number=str(entry.get("course_number", "")),
        term=str(entry.get("term", "")),
        users=int(entry["user_count"]) if isinstance(entry.get("user_count"), int) else 0,
        folders=[f for f in entry.get("folders", []) if isinstance(f, str)],
        status=entry.get("status"),
        school_ext=str(entry.get("school_ext", "")),
        short_number=str(entry.get("short_number", "")),
        anonymity=str(entry.get("anonymity", "")) if entry.get("anonymity") is not None else "",
        auto_join=str(entry.get("auto_join", "")) if entry.get("auto_join") is not None else "",
        config=config,
    )


async def get_network_info(
    rpc: RPC, *, session: SessionStateManager | None = None, nid: str
) -> NetworkInfo:
    """Fetch and parse this network's info from ``user.status``.

    Scans ``result.networks[]`` for an entry whose ``id`` matches *nid*.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        nid: Network ID of the course to look up.

    Returns:
        Parsed NetworkInfo including the role permission matrix when
        present on the wire.

    Raises:
        NotFoundError: If the nid is absent from the user's networks.
        PiazzaSDKError: On unexpected errors.
    """
    try:
        status = await rpc.user_status()
        networks = status.get("networks", []) if isinstance(status, dict) else []
        for entry in networks:
            if isinstance(entry, dict) and str(entry.get("id")) == str(nid):
                return parse_network_entry(entry)
        raise NotFoundError(f"Network {nid} not found in user status")
    except NotFoundError:
        raise
    except Exception as exc:
        raise PiazzaSDKError(f"Failed to get network info: {exc}") from exc


async def update_office_hours(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    staff_uid: str,
    time: str,
    location: str,
) -> dict[str, Any]:
    """Update office hours for a specific staff member.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        staff_uid: The user ID of the staff member.
        time: Office hours time string.
        location: Office hours location string.

    Returns:
        The raw API response dictionary.

        Example:
            ```python
            # Example for update_office_hours
            res = await network.update_office_hours()
            ```
    """
    payload = {"office_hours": {staff_uid: {"time": time, "location": location}}}
    return await rpc.network_update(**payload)


async def update_general_information(
    rpc: RPC, *, session: SessionStateManager | None = None, info: list[dict[str, str]]
) -> dict[str, Any]:
    """Update general information labels for the course.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        info: A list of dicts with 'label' and 'text' keys. Empty list clears it.

    Returns:
        The raw API response dictionary.

        Example:
            ```python
            # Example for update_general_information
            res = await network.update_general_information()
            ```
    """
    payload = {"general_information": info}
    return await rpc.network_update(**payload)


async def update_course_description(
    rpc: RPC, *, session: SessionStateManager | None = None, description: str
) -> dict[str, Any]:
    """Update the course description.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        description: The new course description text.

    Returns:
        The raw API response dictionary.

        Example:
            ```python
            # Example for update_course_description
            res = await network.update_course_description()
            ```
    """
    payload = {"course_description": description}
    return await rpc.network_update(**payload)


async def add_students(
    rpc: RPC, *, session: SessionStateManager | None = None, emails: list[str]
) -> dict[str, Any]:
    """Enroll students into the course.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        emails: List of email addresses to enroll.

    Returns:
        The raw API response dictionary.

        Example:
            ```python
            # Example for add_students
            res = await network.add_students()
            ```
    """
    payload = {"from": "ClassSettingsPage", "add_students": emails}
    return await rpc.network_update(**payload)


async def remove_users(
    rpc: RPC, *, session: SessionStateManager | None = None, user_ids: list[str]
) -> dict[str, Any]:
    """Remove users from the course.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        user_ids: List of user IDs to remove.

    Returns:
        The raw API response dictionary.

        Example:
            ```python
            # Example for remove_users
            res = await network.remove_users()
            ```
    """
    payload = {"remove_users": user_ids}
    return await rpc.network_update(**payload)
