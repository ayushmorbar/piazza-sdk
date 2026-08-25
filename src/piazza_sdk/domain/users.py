"""User domain operations for Piazza SDK.

Provides standalone functions for user retrieval and instructor statistics.
"""

from __future__ import annotations

__all__ = [
    "get_all_users",
    "get_instructor_stats",
    "get_online_users",
    "get_user_status",
    "set_user_setting",
    "unset_user_setting",
]

from typing import TYPE_CHECKING, Any

from piazza_sdk.exceptions import NotFoundError, PiazzaSDKError, UserError
from piazza_sdk.models.user import User

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager
    from piazza_sdk.models.enums import UserStatKey


async def get_all_users(rpc: RPC, *, session: SessionStateManager | None = None) -> list[User]:
    """Get all users in the network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        List of User model instances.

    Raises:
        PiazzaSDKError: On unexpected errors.

        Example:
            ```python
            # Example for get_all_users
            res = await get_all_users()
            ```
    """
    try:
        raw = await rpc.get_users()
        users_raw: list[dict[str, Any]] = raw.get("users", []) if isinstance(raw, dict) else []
        return [User.model_validate(u, extra="ignore") for u in users_raw]
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise UserError(f"Failed to get users: {exc}") from exc


async def get_instructor_stats(
    rpc: RPC, *, session: SessionStateManager | None = None
) -> dict[str, Any]:
    """Get instructor-specific statistics for this network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        Raw instructor stats dictionary.

    Raises:
        NotFoundError: If stats not found.
        PiazzaSDKError: On unexpected errors.

        Example:
            ```python
            # Example for get_instructor_stats
            res = await get_instructor_stats()
            ```
    """
    try:
        return await rpc.get_instructor_stats()
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise UserError(f"Failed to get instructor stats: {exc}") from exc


async def get_online_users(rpc: RPC, *, session: SessionStateManager | None = None) -> int:
    """Get currently online users in the network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        Count of online users.

    Raises:
        NotFoundError: If users not found.
        PiazzaSDKError: On unexpected errors.

        Example:
            ```python
            # Example for get_online_users
            res = await get_online_users()
            ```
    """
    try:
        raw: dict[str, Any] = await rpc.get_online_users()
        users_count = raw.get("users", 0)
        if isinstance(users_count, list):
            return len(users_count)
        return int(users_count) if isinstance(users_count, (int, float, str)) else 0
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise UserError(f"Failed to get online users: {exc}") from exc


async def get_users_by_ids(
    rpc: RPC, *, session: SessionStateManager | None = None, ids: list[str]
) -> list[User]:
    raw = await rpc.network_get_users(ids)
    return [User.model_validate(u) for u in raw]


async def set_user_stat(
    rpc: RPC, *, session: SessionStateManager | None = None, stat: str, val: Any
) -> bool:
    await rpc.user_set(stat, val)
    return True


async def unset_user_stat(
    rpc: RPC, *, session: SessionStateManager | None = None, stat: str
) -> bool:
    await rpc.user_unset(stat)
    return True


async def get_user_status(
    rpc: RPC, *, session: SessionStateManager | None = None
) -> dict[str, Any]:
    """Get the global user status containing enrolled classes and profile data.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        Raw user status dictionary.

    Raises:
        UserError: On unexpected errors.

        Example:
            ```python
            # Example for get_user_status
            res = await get_user_status()
            ```
    """
    try:
        return await rpc.user_status()
    except Exception as exc:
        raise UserError(f"Failed to get user status: {exc}") from exc


async def get_my_events_info(
    rpc: RPC, *, session: SessionStateManager | None = None
) -> dict[str, Any]:
    return await rpc.company_event_get_my_events_info()


async def get_unread_message_count(rpc: RPC, *, session: SessionStateManager | None = None) -> int:
    """Get the count of unread direct messages for the current user.

    Delegates to :meth:`RPC.get_unread_message_count`, which normalizes the
    raw heartbeat payload (dict, scalar, or unexpected shapes) into ``int``.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        Integer count of unread messages.
    """
    return await rpc.get_unread_message_count()


async def set_user_setting(
    rpc: RPC, *, session: SessionStateManager | None = None, stat: UserStatKey | str, val: Any
) -> dict[str, Any]:
    """Set a global user preference or UI state.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        stat: The key of the stat to set (e.g., UserStatKey.LIVE_PREVIEW).
        val: The value to set it to.

    Returns:
        The raw response dictionary.

    Raises:
        UserError: If setting fails.
    """
    try:
        return await rpc.user_set(stat=str(stat), val=val)
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise UserError(f"Failed to set user setting {stat}: {exc}") from exc


async def unset_user_setting(
    rpc: RPC, *, session: SessionStateManager | None = None, stat: UserStatKey | str
) -> dict[str, Any]:
    """Unset/clear a global user preference or UI state.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        stat: The key of the stat to unset.

    Returns:
        The raw response dictionary.

    Raises:
        UserError: If unsetting fails.
    """
    try:
        return await rpc.user_unset(stat=str(stat))
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise UserError(f"Failed to unset user setting {stat}: {exc}") from exc
