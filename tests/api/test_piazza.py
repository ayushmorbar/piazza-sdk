"""Unit tests for api/piazza.py — Piazza high-level client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.api.network import Network
from piazza_sdk.api.piazza import Piazza
from piazza_sdk.models.user import EmailPrefEntry


class TestPiazzaNetworkFactory:
    """Verify Piazza client creates and caches Network instances."""

    def test_piazza_network_creates_instance(self, mock_session):
        piazza = Piazza(mock_session)
        network = piazza.network("12345")
        assert isinstance(network, Network)
        assert network._nid == "12345"

    def test_piazza_network_caches_instances(self, mock_session):
        piazza = Piazza(mock_session)
        n1 = piazza.network("111")
        n2 = piazza.network("111")
        assert n1 is n2

    def test_piazza_network_different_nids(self, mock_session):
        piazza = Piazza(mock_session)
        n1 = piazza.network("111")
        n2 = piazza.network("222")
        assert n1 is not n2


class TestPiazzaUserClassesAndProfile:
    """Verify profile and classes fetching from Piazza client."""

    @pytest.mark.asyncio
    async def test_get_user_classes_from_profile_networks(self, mock_session):
        """Classes derive from user_profile.get_profile -> networks."""
        mock_rpc = MagicMock()
        mock_rpc.get_user_profile = AsyncMock(
            return_value={
                "name": "Test Instructor",
                "networks": [{"id": "c1", "name": "Class 1"}, {"id": "c2", "name": "Class 2"}],
            }
        )
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        classes = await piazza.get_user_classes()
        assert len(classes) == 2
        assert classes[0]["id"] == "c1"
        assert classes[1]["name"] == "Class 2"


class TestPiazzaGlobalDelegations:
    """Verify global convenience RPC methods on Piazza client."""

    @pytest.mark.asyncio
    async def test_get_my_events_info(self, mock_session):
        mock_rpc = MagicMock()
        mock_rpc.company_event_get_my_events_info = AsyncMock(return_value={"events": []})
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        res = await piazza.get_my_events_info()
        assert res == {"events": []}

    @pytest.mark.asyncio
    async def test_get_unread_message_count(self, mock_session):
        mock_rpc = MagicMock()
        mock_rpc.get_unread_message_count = AsyncMock(return_value=3)
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        count = await piazza.get_unread_message_count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_page_event(self, mock_session):
        mock_rpc = MagicMock()
        mock_rpc.generic_page_event = AsyncMock(return_value={})
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        res = await piazza.page_event(type="view", page="dashboard")
        assert res is True

    @pytest.mark.asyncio
    async def test_sanitize_html(self, mock_session):
        mock_rpc = MagicMock()
        mock_rpc.generic_sanitize_html = AsyncMock(return_value={"html": "<p>clean</p>"})
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        res = await piazza.sanitize_html(text="<p>dirty</p>")
        assert res == {"html": "<p>clean</p>"}

    @pytest.mark.asyncio
    async def test_get_email_preferences(self, mock_session):
        mock_rpc = MagicMock()
        mock_rpc.user_status = AsyncMock(
            return_value={"config": {"email_prefs": {"n1": {"new": "instantly"}}}}
        )
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        prefs = await piazza.get_email_preferences()
        assert isinstance(prefs["n1"], EmailPrefEntry)
        assert prefs["n1"].new == "instantly"

    @pytest.mark.asyncio
    async def test_opt_out_of_emails(self, mock_session):
        mock_rpc = MagicMock()
        mock_rpc.user_status = AsyncMock(
            return_value={"config": {"email_prefs": {"n1": {"new": "instantly"}, "career": {}}}}
        )
        mock_rpc.user_update = AsyncMock(return_value={})
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        result = await piazza.opt_out_of_emails()
        assert set(result) == {"n1"}
        assert result["n1"]["new"] == "no-emails"
        mock_rpc.user_update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_set_email_notification(self, mock_session):
        mock_rpc = MagicMock()
        mock_rpc.user_status = AsyncMock(
            return_value={"config": {"email_prefs": {"n1": {"new": "instantly", "throttle": 0}}}}
        )
        mock_rpc.user_update = AsyncMock(return_value={})
        piazza = Piazza(mock_session)
        piazza._user_rpc = mock_rpc

        updated = await piazza.set_email_notification("n1", new="no-emails")
        assert updated["new"] == "no-emails"
        assert updated["throttle"] == 0  # preserved by partial merge
