"""User domain operations for Piazza SDK.

Provides standalone functions for user retrieval and instructor statistics.
"""

from __future__ import annotations

__all__ = [
    "get_all_users",
    "get_email_preferences",
    "get_instructor_stats",
    "get_online_users",
    "get_user_status",
    "opt_out_of_emails",
    "set_email_notification",
    "set_user_setting",
    "unset_user_setting",
]

from typing import TYPE_CHECKING, Any

from piazza_sdk.exceptions import NotFoundError, PiazzaSDKError, UserError
from piazza_sdk.models.user import EmailPrefEntry, User

if TYPE_CHECKING:
    from collections.abc import Sequence

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


# Keys in ``email_prefs`` that are not network IDs (Go reference: "career").
_NON_COURSE_PREF_KEYS = frozenset({"career"})

# Notification mode that disables emails for a course (Go reference value).
_NO_EMAILS_MODE = "no-emails"


def _extract_email_prefs(status: dict[str, Any]) -> dict[str, Any]:
    """Extract the raw ``email_prefs`` mapping from a ``user.status`` result.

    The RPC layer has already unwrapped the JSON-RPC envelope, so the
    prefs live under ``config.email_prefs``. Defensive chaining keeps
    malformed or missing payloads from raising.

    Args:
        status: Unwrapped ``user.status`` result dictionary.

    Returns:
        Raw mapping of pref key (network ID, or non-course keys such as
        ``career``) to preference dict. Empty dict when absent.
    """
    config = status.get("config") if isinstance(status, dict) else None
    prefs = config.get("email_prefs") if isinstance(config, dict) else None
    return prefs if isinstance(prefs, dict) else {}


async def get_email_preferences(
    rpc: RPC, *, session: SessionStateManager | None = None
) -> dict[str, EmailPrefEntry]:
    """Read the current user's global email preferences.

    Fetches ``user.status`` and returns a typed view of
    ``config.email_prefs`` keyed by network ID (non-course keys such as
    ``career`` are included when present).

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.

    Returns:
        Mapping of preference key to :class:`EmailPrefEntry`.

    Raises:
        UserError: On unexpected errors.

    Example:
        ```python
        # Example for get_email_preferences
        res = await get_email_preferences()
        ```
    """
    try:
        status = await rpc.user_status()
        return {
            key: EmailPrefEntry.model_validate(value)
            for key, value in _extract_email_prefs(status).items()
            if isinstance(value, dict)
        }
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise UserError(f"Failed to get email preferences: {exc}") from exc


async def update_email_preferences(
    rpc: RPC, *, session: SessionStateManager | None = None, prefs: dict[str, dict[str, Any]]
) -> None:
    """Write back an ``email_prefs`` mapping via ``user.update``.

    Callers are expected to pass a mapping derived from a prior read so
    unknown server-side keys survive the round trip.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        prefs: Raw ``email_prefs`` mapping to persist.

    Raises:
        UserError: On unexpected errors.
    """
    try:
        await rpc.user_update(email_prefs=prefs)
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise UserError(f"Failed to update email preferences: {exc}") from exc


async def set_email_notification(  # noqa: PLR0913 - explicit optional flag surface
    rpc: RPC,
    nid: str,
    *,
    session: SessionStateManager | None = None,
    new: str | None = None,
    updates: str | None = None,
    no_events: bool | None = None,
    auto_follow: str | None = None,
    throttle: int | None = None,
) -> dict[str, Any]:
    """Partially update one course's notification settings.

    Performs a read-modify-write against the full ``email_prefs`` map so
    every other course (and any unknown per-entry keys) is preserved
    exactly as the server returned it. Only the supplied flags on *nid*
    are overwritten.

    Args:
        rpc: RPC client instance.
        nid: Network ID of the course whose settings change.
        session: Optional session manager for automatic refresh.
        new: New-post notification mode (e.g. ``"instantly"``,
            ``"daily"``, ``"no-emails"``).
        updates: Update notification mode.
        no_events: Whether event notifications are suppressed.
        auto_follow: Auto-follow setting.
        throttle: Email throttling value.

    Returns:
        The updated entry for *nid* after the merge (raw dict).

    Raises:
        UserError: If the course is not present in ``email_prefs`` or
            the write fails.
    """
    try:
        status = await rpc.user_status()
        prefs = _extract_email_prefs(status)
        if nid not in prefs or not isinstance(prefs[nid], dict):
            raise UserError(f"No email preferences found for course {nid}")
        changes: dict[str, Any] = {}
        if new is not None:
            changes["new"] = new
        if updates is not None:
            changes["updates"] = updates
        if no_events is not None:
            changes["no_events"] = no_events
        if auto_follow is not None:
            changes["auto_follow"] = auto_follow
        if throttle is not None:
            changes["throttle"] = throttle
        merged: dict[str, Any] = {**prefs[nid], **changes}
        prefs[nid] = merged
        await rpc.user_update(email_prefs=prefs)
        return merged
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise UserError(f"Failed to set email notification for {nid}: {exc}") from exc


async def opt_out_of_emails(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    exclude_nids: Sequence[str] = (),
    keep_careers: bool = False,
) -> dict[str, Any]:
    """Disable email notifications for every enrolled course at once.

    Sets ``new: "no-emails"`` on each entry of ``user.status``'s
    ``config.email_prefs``, mirroring the bulk opt-out semantics of the
    reference Go client. Non-course keys (``career``) are dropped before
    write-back unless ``keep_careers`` is set; courses listed in
    ``exclude_nids`` keep their current mode.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        exclude_nids: Course IDs to leave untouched.
        keep_careers: Whether to preserve the ``career`` prefs entry.

    Returns:
        The final ``email_prefs`` payload sent to ``user.update``.

    Raises:
        UserError: On unexpected errors.
    """
    try:
        status = await rpc.user_status()
        prefs = _extract_email_prefs(status)
        excluded = frozenset(exclude_nids)
        result: dict[str, Any] = {}
        for key, entry in prefs.items():
            # Non-course keys (career) are never flipped — pass through as-is.
            if key in _NON_COURSE_PREF_KEYS:
                if keep_careers:
                    result[key] = entry
                continue
            if key in excluded or not isinstance(entry, dict):
                result[key] = entry
                continue
            result[key] = {**entry, "new": _NO_EMAILS_MODE}
        await rpc.user_update(email_prefs=result)
        return result
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise UserError(f"Failed to opt out of emails: {exc}") from exc
