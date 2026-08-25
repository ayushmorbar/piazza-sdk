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
    from collections.abc import Sequence

    from piazza_sdk.auth import SessionStateManager
    from piazza_sdk.models.enums import UserStatKey
    from piazza_sdk.models.user import EmailPrefEntry


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

    async def demo_login(self, auth: str | None = None, url: str | None = None) -> None:
        """Authenticate as a demo user via a "Share Your Class" link.

        Delegates to the underlying :class:`SessionStateManager`. Provide
        exactly one of *auth* (share-link token) or the full demo *url*.

        Raises:
            ValidationError: If both or neither of *auth*/*url* is given.
            AuthenticationError: If the demo link is rejected by the server.
        """
        await self._session.demo_login(auth=auth, url=url)

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

        Enriches each class dict with an ``is_ta`` boolean derived from
        the user's ``prof_hash`` in ``user.status``.

        Automatically restores the session if expired.

        Returns:
            List of class dictionaries; each carries a ``nid`` key taken
            from its mapping key when not already present.

        Example:
            ```python
            # Example for get_user_classes
            res = await get_user_classes()
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        entries = await self._fetch_class_entries()
        await self._enrich_is_ta(entries)
        return entries

    async def _fetch_class_entries(self) -> list[dict[str, Any]]:
        """Fetch raw class entries from user profile."""
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
        return self._parse_class_entries(raw_classes)

    @staticmethod
    def _parse_class_entries(raw_classes: Any) -> list[dict[str, Any]]:
        """Parse raw classes dict or list into a list of dicts with nid keys."""
        if isinstance(raw_classes, dict):
            entries: list[dict[str, Any]] = []
            for nid, value in raw_classes.items():
                if isinstance(value, dict):
                    item = dict(value)
                    item.setdefault("nid", nid)
                    entries.append(item)
            return entries
        if isinstance(raw_classes, list):
            return [item for item in raw_classes if isinstance(item, dict)]
        return []

    async def _enrich_is_ta(self, entries: list[dict[str, Any]]) -> None:
        """Set ``is_ta`` on each class entry from user.status prof_hash."""
        try:
            status = await self.get_user_status()
        except PiazzaSDKError:
            return
        uid = str(status.get("id", ""))
        prof_map = self._build_prof_map(status.get("networks", []))
        for entry in entries:
            nid = str(entry.get("nid", ""))
            entry["is_ta"] = uid != "" and uid in prof_map.get(nid, {})

    @staticmethod
    def _build_prof_map(networks: Any) -> dict[str, dict[str, Any]]:
        """Map network IDs to their ``prof_hash`` dicts."""
        prof_map: dict[str, dict[str, Any]] = {}
        if not isinstance(networks, list):
            return prof_map
        for net in networks:
            if isinstance(net, dict):
                nid = str(net.get("id", ""))
                if nid:
                    prof_map[nid] = net.get("prof_hash", {})
        return prof_map

    async def get_user_profile(self) -> dict[str, Any]:
        """Get the current user's profile via JSON-RPC.

        Uses the canonical ``user_profile.get_profile`` RPC method.
        Automatically restores the session if expired.

        Returns:
            User profile dictionary with name, email, school, roles,
            skills, tags, and enrolled classes.

        Example:
            ```python
            # Example for get_user_profile
            res = await get_user_profile()
            ```
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

        Example:
            ```python
            # Example for get_user_status
            res = await get_user_status()
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import get_user_status  # noqa: PLC0415

        return await get_user_status(self._get_user_rpc())

    async def get_my_events_info(self) -> dict[str, Any]:
        """Get the current user's events and notifications info.

        Uses the ``user.get_my_events_info`` RPC method.  Automatically
        restores the session if expired.

        Returns:
            Dictionary containing event counts and notification metadata.

        Example:
            ```python
            # Example for get_my_events_info
            res = await get_my_events_info()
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import get_my_events_info  # noqa: PLC0415

        return await get_my_events_info(self._get_user_rpc())

    async def get_unread_message_count(self) -> int:
        """Get the count of unread messages for the current user.

        Uses the ``user.get_unread_message_count`` RPC method.
        Automatically restores the session if expired.

        Returns:
            Integer count of unread messages.

        Example:
            ```python
            # Example for get_unread_message_count
            res = await get_unread_message_count()
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import get_unread_message_count  # noqa: PLC0415

        return await get_unread_message_count(self._get_user_rpc())

    async def set_user_setting(self, stat: UserStatKey | str, val: Any) -> dict[str, Any]:
        """Set a global user preference or UI state.

        Uses the ``user.set`` RPC method.

        Args:
            stat: The key of the stat to set (e.g. ``UserStatKey.LIVE_PREVIEW``).
            val: The value to set it to.

        Returns:
            The raw response dictionary.
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import set_user_setting  # noqa: PLC0415

        return await set_user_setting(self._get_user_rpc(), stat=stat, val=val)

    async def unset_user_setting(self, stat: UserStatKey | str) -> dict[str, Any]:
        """Unset/clear a global user preference or UI state.

        Uses the ``user.unset`` RPC method.

        Args:
            stat: The key of the stat to unset.

        Returns:
            The raw response dictionary.
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import unset_user_setting  # noqa: PLC0415

        return await unset_user_setting(self._get_user_rpc(), stat=stat)

    async def get_email_preferences(self) -> dict[str, EmailPrefEntry]:
        """Read the current user's global email notification preferences.

        Uses ``user.status`` (``config.email_prefs``) and returns a typed
        view keyed by network ID. Automatically restores the session if
        expired.

        Returns:
            Mapping of preference key to :class:`EmailPrefEntry`.

        Example:
            ```python
            # Example for get_email_preferences
            res = await get_email_preferences()
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import get_email_preferences  # noqa: PLC0415

        return await get_email_preferences(self._get_user_rpc())

    async def set_email_notification(  # noqa: PLR0913 - explicit optional flag surface
        self,
        nid: str,
        *,
        new: str | None = None,
        updates: str | None = None,
        no_events: bool | None = None,
        auto_follow: str | None = None,
        throttle: int | None = None,
    ) -> dict[str, Any]:
        """Partially update one course's email notification settings.

        Read-modify-write against the full preference map; all other
        courses are preserved. Automatically restores the session if
        expired.

        Args:
            nid: Network ID of the course whose settings change.
            new: New-post notification mode (e.g. ``"instantly"``,
                ``"daily"``, ``"no-emails"``).
            updates: Update notification mode.
            no_events: Whether event notifications are suppressed.
            auto_follow: Auto-follow setting.
            throttle: Email throttling value.

        Returns:
            The updated raw entry for *nid*.

        Example:
            ```python
            # Example for set_email_notification
            res = await set_email_notification(nid='...')
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import set_email_notification  # noqa: PLC0415

        return await set_email_notification(
            self._get_user_rpc(),
            nid,
            new=new,
            updates=updates,
            no_events=no_events,
            auto_follow=auto_follow,
            throttle=throttle,
        )

    async def opt_out_of_emails(
        self, *, exclude_nids: Sequence[str] = (), keep_careers: bool = False
    ) -> dict[str, Any]:
        """Disable email notifications for every enrolled course at once.

        Sets ``new: "no-emails"`` on each entry of the global
        ``email_prefs`` map via ``user.update``. Courses listed in
        ``exclude_nids`` keep their current mode; the non-course
        ``career`` entry is dropped unless ``keep_careers=True``.

        Args:
            exclude_nids: Course IDs to leave untouched.
            keep_careers: Whether to preserve the ``career`` prefs entry.

        Returns:
            The final ``email_prefs`` payload that was written.

        Example:
            ```python
            # Example for opt_out_of_emails
            res = await opt_out_of_emails()
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.users import opt_out_of_emails  # noqa: PLC0415

        return await opt_out_of_emails(
            self._get_user_rpc(), exclude_nids=exclude_nids, keep_careers=keep_careers
        )

    async def page_event(self, type: str, **kwargs: Any) -> bool:
        """Record a page-view event for analytics.

        Uses the ``generic.page_event`` RPC method.  Automatically
        restores the session if expired.

        Args:
            type: Event type string (e.g. ``"page"``).
            **kwargs: Additional event payload fields.

        Returns:
            ``True`` if the event was accepted by the server.

        Example:
            ```python
            # Example for page_event
            res = await page_event(type='...')
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.generic import page_event  # noqa: PLC0415

        return await page_event(self._get_user_rpc(), type=type, **kwargs)

    async def sanitize_html(self, **kwargs: Any) -> dict[str, Any]:
        """Sanitize HTML content via Piazza's server-side cleaner.

        Uses the ``generic.sanitize_html`` RPC method.  Automatically
        restores the session if expired.

        Args:
            **kwargs: Arbitrary keyword arguments forwarded to the RPC
                call (typically ``content`` with raw HTML).

        Returns:
            Dictionary containing the sanitized HTML under the
            ``sanitized`` key (and possibly other metadata).

        Example:
            ```python
            # Example for sanitize_html
            res = await sanitize_html()
            ```
        """
        if self._session.needs_refresh:
            await self._session.refresh()
        from piazza_sdk.domain.generic import sanitize_html  # noqa: PLC0415

        return await sanitize_html(self._get_user_rpc(), **kwargs)
