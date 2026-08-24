"""Piazza client entry point for Piazza SDK.

Provides the Piazza class as the top-level entry point for
interacting with Piazza's API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from piazza_sdk.api.network import Network
from piazza_sdk.api.rpc import RPC
from piazza_sdk.exceptions import PiazzaSDKError

if TYPE_CHECKING:
    from piazza_sdk.auth import SessionStateManager


class Piazza:
    """Top-level Piazza client.

    Provides user-level operations and creates Network instances
    for per-class operations.

    Usage:
        async with SessionStateManager(config) as session:
            await session.login(email="user@example.com", password="pass")
            piazza = Piazza(session)
            classes = await piazza.get_user_classes()
            network = piazza.network(classes[0]["nid"])
    """

    def __init__(self, session: SessionStateManager) -> None:
        self._session = session
        self._networks: dict[str, Network] = {}
        self._user_rpc: RPC | None = None

    def _retry_kwargs(self) -> dict[str, Any]:
        """Map SessionConfig retry knobs onto RPC kwargs (when numeric)."""
        retries = getattr(self._session.config, "retries", None)
        retry_delay = getattr(self._session.config, "retry_delay", None)
        return {
            "max_attempts": retries if isinstance(retries, int) else None,
            "retry_base_delay": retry_delay if isinstance(retry_delay, int | float) else None,
        }

    def _get_user_rpc(self) -> RPC:
        """Return a reusable RPC instance with no network ID (user-level endpoints)."""
        if self._user_rpc is None:
            self._user_rpc = RPC(
                session=self._session,
                base_url=self._session.config.base_url,
                network_id="",
                on_auth_error=self._session.handle_auth_error,
                **self._retry_kwargs(),
            )
        return self._user_rpc

    def network(self, nid: str) -> Network:
        """Get or create a Network instance for the given NID.

        Args:
            nid: Network/course ID.

        Returns:
            Network instance for the given NID.
        """
        if nid not in self._networks:
            rpc = RPC(
                session=self._session,
                base_url=self._session.config.base_url,
                network_id=nid,
                on_auth_error=self._session.handle_auth_error,
                **self._retry_kwargs(),
            )
            self._networks[nid] = Network(rpc, nid, session=self._session)
        return self._networks[nid]

    async def get_user_classes(self) -> list[dict[str, Any]]:
        """Get list of classes (networks) the user belongs to.

        Uses the ``user_profile.get_profile`` RPC and extracts its
        ``all_classes`` mapping (``{nid -> class dict}``) — the legacy
        ``/user/api/get_user_classes`` REST path returns HTTP 404 on the
        current Piazza API (verified live 2026-08).

        Automatically restores the session if expired.

        Returns:
            List of class dictionaries; each carries a ``nid`` key taken
            from its mapping key when not already present.
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        try:
            profile = await self._get_user_rpc().get_user_profile()
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise PiazzaSDKError(f"Failed to get user classes: {exc}") from exc

        raw_classes: Any = (
            profile.get("all_classes", profile.get("networks", []))
            if isinstance(profile, dict)
            else []
        )
        if isinstance(raw_classes, dict):
            entries: list[Any] = []
            for nid, value in raw_classes.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("nid", nid)
                    entries.append(item)
            return entries
        if isinstance(raw_classes, list):
            return [item for item in raw_classes if isinstance(item, dict)]
        return []

    async def get_user_profile(self) -> dict[str, Any]:
        """Get the current user's profile via JSON-RPC.

        Uses the canonical ``user_profile.get_profile`` RPC method.
        Automatically restores the session if expired.

        Returns:
            User profile dictionary with name, email, school, roles,
            skills, tags, and enrolled classes.
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        try:
            return await self._get_user_rpc().get_user_profile()
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise PiazzaSDKError(f"Failed to get user profile: {exc}") from exc

    async def get_user_status(self) -> dict[str, Any]:
        """Get the global user status (contains enrolled classes and profile data).

        Uses the canonical ``user.status`` RPC method.
        Automatically restores the session if expired.

        Returns:
            Raw user status dictionary.
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import get_user_status  # noqa: PLC0415

        return await get_user_status(self._get_user_rpc())

    async def get_my_events_info(self) -> dict[str, Any]:
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import get_my_events_info  # noqa: PLC0415

        return await get_my_events_info(self._get_user_rpc())

    async def get_unread_message_count(self) -> int:
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import get_unread_message_count  # noqa: PLC0415

        return await get_unread_message_count(self._get_user_rpc())

    async def page_event(self, type: str, **kwargs: Any) -> bool:
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.generic import page_event  # noqa: PLC0415

        return await page_event(self._get_user_rpc(), type=type, **kwargs)

    async def sanitize_html(self, **kwargs: Any) -> dict[str, Any]:
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.generic import sanitize_html  # noqa: PLC0415

        return await sanitize_html(self._get_user_rpc(), **kwargs)
