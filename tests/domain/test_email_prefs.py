"""Unit tests for global email preferences (user.update) domain operations."""

from __future__ import annotations

import copy
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.users import (
    _extract_email_prefs,
    get_email_preferences,
    opt_out_of_emails,
    set_email_notification,
    update_email_preferences,
)
from piazza_sdk.exceptions import PiazzaSDKError, UserError
from piazza_sdk.models.user import EmailPrefEntry


def _status_with(prefs: dict[str, Any]) -> dict[str, Any]:
    """Build a user.status-shaped result carrying a deep copy of email_prefs."""
    return {"id": "u1", "config": {"email_prefs": copy.deepcopy(prefs)}}


def _rpc_with_status(status: dict[str, Any]) -> MagicMock:
    rpc = MagicMock()
    rpc.user_status = AsyncMock(return_value=status)
    rpc.user_update = AsyncMock(return_value={})
    return rpc


COURSE_PREFS = {
    "abc123": {
        "auto_follow": "yes",
        "new": "instantly",
        "updates": "daily",
        "no_events": False,
        "throttle": 0,
        "custom_future_key": 42,
    },
    "def456": {"new": "daily", "updates": "instantly", "no_events": False, "throttle": 5},
    "career": {"new": "weekly", "updates": "weekly"},
}


# ── _extract_email_prefs ────────────────────────────────────────────────


class TestExtractEmailPrefs:
    def test_extracts_from_config(self):
        assert _extract_email_prefs(_status_with({"a": {}})) == {"a": {}}

    def test_missing_config_returns_empty(self):
        assert _extract_email_prefs({"id": "u1"}) == {}

    def test_non_dict_status_returns_empty(self):
        assert _extract_email_prefs("garbage") == {}  # type: ignore[arg-type]

    def test_non_dict_prefs_returns_empty(self):
        assert _extract_email_prefs({"config": {"email_prefs": [1]}}) == {}


# ── get_email_preferences ───────────────────────────────────────────────


class TestGetEmailPreferences:
    @pytest.mark.asyncio
    async def test_typed_read_includes_career(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        prefs = await get_email_preferences(rpc)
        assert set(prefs) == {"abc123", "def456", "career"}
        assert isinstance(prefs["abc123"], EmailPrefEntry)
        assert prefs["abc123"].new == "instantly"
        assert prefs["career"].new == "weekly"

    @pytest.mark.asyncio
    async def test_unknown_entry_keys_ignored(self):
        rpc = _rpc_with_status(_status_with({"a": {"new": "daily", "zzz_unknown": True}}))
        entry = (await get_email_preferences(rpc))["a"]
        assert entry.new == "daily"

    @pytest.mark.asyncio
    async def test_empty_status(self):
        rpc = _rpc_with_status({})
        assert await get_email_preferences(rpc) == {}


# ── update_email_preferences ────────────────────────────────────────────


class TestUpdateEmailPreferences:
    @pytest.mark.asyncio
    async def test_forwards_raw_map_verbatim(self):
        rpc = _rpc_with_status({})
        raw = {"a": {"new": "no-emails"}}
        await update_email_preferences(rpc, prefs=raw)
        rpc.user_update.assert_awaited_once_with(email_prefs=raw)

    @pytest.mark.asyncio
    async def test_rpc_error_propagates_unwrapped(self):
        rpc = _rpc_with_status({})
        rpc.user_update = AsyncMock(side_effect=PiazzaSDKError("boom"))
        with pytest.raises(PiazzaSDKError):
            await update_email_preferences(rpc, prefs={})


# ── set_email_notification ──────────────────────────────────────────────


class TestSetEmailNotification:
    @pytest.mark.asyncio
    async def test_partial_merge_preserves_other_fields(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        updated = await set_email_notification(rpc, "abc123", new="no-emails")
        assert updated["new"] == "no-emails"
        # Untouched flags and unknown keys survive the merge.
        assert updated["updates"] == "daily"
        assert updated["custom_future_key"] == 42
        # Write-back contains the full map.
        sent = rpc.user_update.await_args.kwargs["email_prefs"]
        assert set(sent) == {"abc123", "def456", "career"}

    @pytest.mark.asyncio
    async def test_only_supplied_flags_change(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        await set_email_notification(rpc, "def456", no_events=True, throttle=9)
        sent = rpc.user_update.await_args.kwargs["email_prefs"]
        assert sent["def456"] == {
            "new": "daily",
            "updates": "instantly",
            "no_events": True,
            "throttle": 9,
        }
        assert sent["abc123"]["new"] == "instantly"  # other courses untouched

    @pytest.mark.asyncio
    async def test_all_flag_kinds_applied(self):
        rpc = _rpc_with_status(_status_with({"n1": {}}))
        updated = await set_email_notification(
            rpc, "n1", new="daily", updates="weekly", no_events=True, auto_follow="yes", throttle=3
        )
        assert updated == {
            "new": "daily",
            "updates": "weekly",
            "no_events": True,
            "auto_follow": "yes",
            "throttle": 3,
        }

    @pytest.mark.asyncio
    async def test_unknown_nid_raises_user_error(self):
        rpc = _rpc_with_status(_status_with({"a": {}}))
        with pytest.raises(UserError, match="No email preferences"):
            await set_email_notification(rpc, "missing")

    @pytest.mark.asyncio
    async def test_non_dict_entry_raises_user_error(self):
        rpc = _rpc_with_status(_status_with({"bad": "not-a-dict"}))
        with pytest.raises(UserError, match="No email preferences"):
            await set_email_notification(rpc, "bad")


# ── opt_out_of_emails ───────────────────────────────────────────────────


class TestOptOutOfEmails:
    @pytest.mark.asyncio
    async def test_flips_every_course_and_drops_career(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        result = await opt_out_of_emails(rpc)
        assert set(result) == {"abc123", "def456"}  # career dropped
        assert result["abc123"]["new"] == "no-emails"
        assert result["def456"]["new"] == "no-emails"
        rpc.user_update.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_excluded_nids_keep_current_mode(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        result = await opt_out_of_emails(rpc, exclude_nids=["def456"])
        assert result["abc123"]["new"] == "no-emails"
        assert result["def456"]["new"] == "daily"

    @pytest.mark.asyncio
    async def test_careers_kept_when_requested(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        result = await opt_out_of_emails(rpc, keep_careers=True)
        assert result["career"] == COURSE_PREFS["career"]  # untouched, not flipped

    @pytest.mark.asyncio
    async def test_unknown_keys_preserved_on_flip(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        result = await opt_out_of_emails(rpc)
        assert result["abc123"]["custom_future_key"] == 42
        assert result["abc123"]["throttle"] == 0

    @pytest.mark.asyncio
    async def test_non_dict_entries_passed_through(self):
        rpc = _rpc_with_status(_status_with({"weird": None}))
        result = await opt_out_of_emails(rpc)
        assert result["weird"] is None

    @pytest.mark.asyncio
    async def test_rpc_error_propagates_unwrapped(self):
        rpc = _rpc_with_status(_status_with(COURSE_PREFS))
        rpc.user_update = AsyncMock(side_effect=PiazzaSDKError("boom"))
        with pytest.raises(PiazzaSDKError):
            await opt_out_of_emails(rpc)
