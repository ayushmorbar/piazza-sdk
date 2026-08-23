"""Domain logic for network-level operations (office hours, settings)."""

from typing import TYPE_CHECKING, Any

__all__ = ["update_course_description", "update_general_information", "update_office_hours"]

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager


async def update_office_hours(
    rpc: "RPC",
    *,
    session: "SessionStateManager | None" = None,
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
    """
    payload = {"office_hours": {staff_uid: {"time": time, "location": location}}}
    return await rpc.network_update(**payload)


async def update_general_information(
    rpc: "RPC", *, session: "SessionStateManager | None" = None, info: list[dict[str, str]]
) -> dict[str, Any]:
    """Update general information labels for the course.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        info: A list of dicts with 'label' and 'text' keys. Empty list clears it.

    Returns:
        The raw API response dictionary.
    """
    payload = {"general_information": info}
    return await rpc.network_update(**payload)


async def update_course_description(
    rpc: "RPC", *, session: "SessionStateManager | None" = None, description: str
) -> dict[str, Any]:
    """Update the course description.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        description: The new course description text.

    Returns:
        The raw API response dictionary.
    """
    payload = {"course_description": description}
    return await rpc.network_update(**payload)
