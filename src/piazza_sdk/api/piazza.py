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

    def network(self, nid: str) -> Network:
        """Get or create a Network instance for the given NID.

        Args:
            nid: Network/course ID.

        Returns:
            Network instance for the given NID.
        """
        if nid not in self._networks:
            rpc = RPC(
                client=self._session.client, base_url=self._session.config.base_url, network_id=nid
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
            rpc = RPC(
                client=self._session.client, base_url=self._session.config.base_url, network_id=""
            )
            raw = await rpc._request("POST", "/user/api/get_user_classes")
            return raw.get("result", []) if isinstance(raw, dict) else []
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise PiazzaSDKError(f"Failed to get user classes: {exc}") from exc

    async def get_user_profile(self) -> dict[str, Any]:
        """Get the current user's profile.

        Automatically restores the session if expired.

        Returns:
            User profile dictionary.
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        try:
            rpc = RPC(
                client=self._session.client, base_url=self._session.config.base_url, network_id=""
            )
            raw = await rpc._request("POST", "/user/api/get_user_profile")
            return raw if isinstance(raw, dict) else {}
        except PiazzaSDKError:
            raise
        except Exception as exc:
            raise PiazzaSDKError(f"Failed to get user profile: {exc}") from exc
