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

    def _get_user_rpc(self) -> RPC:
        """Return a reusable RPC instance with no network ID (user-level endpoints)."""
        if self._user_rpc is None:
            self._user_rpc = RPC(
                session=self._session,
                base_url=self._session.config.base_url,
                network_id="",
                on_auth_error=self._session._rpc_refresh,
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
                on_auth_error=self._session._rpc_refresh,
            )
            self._networks[nid] = Network(rpc, nid, session=self._session)
        return self._networks[nid]

    async def get_user_classes(self) -> list[dict[str, Any]]:
        """Get list of classes (networks) the user belongs to.

        Automatically restores the session if expired.

        Returns:
            List of class dictionaries with id, name, nid, etc.
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        try:
            raw = await self._get_user_rpc()._safe_call(
                "/user/api/get_user_classes", {}, error_msg="Failed to get user classes"
            )
            return raw.get("result", []) if isinstance(raw, dict) else []  # type: ignore[no-any-return]
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise PiazzaSDKError(f"Failed to get user classes: {exc}") from exc

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
            raw = await self._get_user_rpc().get_user_profile()
            return raw.get("result", raw) if isinstance(raw, dict) else raw  # type: ignore[no-any-return]
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise PiazzaSDKError(f"Failed to get user profile: {exc}") from exc
