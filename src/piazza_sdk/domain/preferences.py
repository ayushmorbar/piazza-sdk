"""Preferences domain operations for Piazza SDK.

Provides standalone functions for user preference management.
"""

from __future__ import annotations

__all__ = ["get_preferences", "update_preferences"]

from typing import TYPE_CHECKING, Any

from piazza_sdk.exceptions import ContentError, PiazzaSDKError
from piazza_sdk.models.user import UserPreferences

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager


async def get_preferences(
    rpc: RPC, *, session: SessionStateManager | None = None
) -> UserPreferences:
    """Retrieve the current user's preferences for this network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        UserPreferences model with the current settings.

    Raises:
        PiazzaSDKError: On unexpected errors.
    """
    try:
        raw: dict[str, Any] = await rpc.get_user_preferences()
        return UserPreferences(**raw)
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise ContentError(f"Failed to get preferences: {exc}") from exc


async def update_preferences(
    rpc: RPC, *, session: SessionStateManager | None = None, prefs: UserPreferences
) -> None:
    """Update the current user's preferences for this network.

    Uses ``exclude_unset=True`` to only transmit explicitly set fields,
    preventing a partial-update wipe of unset preferences.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        prefs: UserPreferences with the fields to update.

    Raises:
        PiazzaSDKError: On unexpected errors.
    """
    try:
        payload = prefs.model_dump(by_alias=True, exclude_unset=True)
        await rpc.update_user_preferences(payload)
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise ContentError(f"Failed to update preferences: {exc}") from exc
