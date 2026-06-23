"""User domain operations for Piazza SDK.

Provides standalone functions for user retrieval and instructor statistics.
"""

from __future__ import annotations

__all__ = ["get_all_users", "get_instructor_stats", "get_online_users"]

from typing import TYPE_CHECKING, Any

from piazza_sdk.exceptions import ContentError, NotFoundError, PiazzaSDKError
from piazza_sdk.models.user import User

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager


async def get_all_users(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
) -> list[User]:
    """Get all users in the network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        List of User model instances.

    Raises:
        PiazzaSDKError: On unexpected errors.
    """
    try:
        raw = await rpc.get_users()
        users_raw: list[dict[str, Any]] = (
            raw.get("users", []) if isinstance(raw, dict) else []
        )
        return [User.model_validate(u, extra="ignore") for u in users_raw]
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise ContentError(f"Failed to get users: {exc}") from exc


async def get_instructor_stats(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
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
    """
    try:
        return await rpc.get_instructor_stats()
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to get instructor stats: {exc}") from exc


async def get_online_users(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
) -> list[User]:
    """Get currently online users in the network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        List of online User model instances.

    Raises:
        NotFoundError: If users not found.
        PiazzaSDKError: On unexpected errors.
    """
    try:
        raw: dict[str, Any] = await rpc.get_online_users()
        users_raw: list[dict[str, Any]] = raw.get("users", [])
        return [User.model_validate(u, extra="ignore") for u in users_raw]
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to get online users: {exc}") from exc
