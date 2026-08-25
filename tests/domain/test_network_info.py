"""Unit tests for network info parsing and the role permission matrix."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.network import get_network_info, parse_network_entry
from piazza_sdk.exceptions import NotFoundError
from piazza_sdk.models.enums import UserRole
from piazza_sdk.models.network import NetworkConfig, NetworkInfo


def _roles_matrix() -> dict[str, Any]:
    """Build a realistic 5-role config.roles payload (from Go reference)."""
    full = {
        "admin_roster": True,
        "new_post": True,
        "new_followup": True,
        "question_edit": True,
        "question_delete": True,
        "expert_answer_create": True,
        "member_answer_edit": True,
    }
    return {
        "admin": {**full, "can_post_anonymous_all": True},
        "instructor": {**full, "can_post_anonymous_members": True},
        "professor": dict(full),
        "student": {
            "new_post": True,
            "new_followup": True,
            "member_answer_create": True,
            "question_edit": False,
        },
        "ta": dict(full),
    }


def _network_entry(**overrides: Any) -> dict[str, Any]:
    """Build a realistic user.status networks[] entry."""
    entry: dict[str, Any] = {
        "id": "mqsgm1zclb114z",
        "name": "CS 101",
        "course_number": "CS 101",
        "term": "Spring 2024",
        "status": "active",
        "folders": ["hw1", "lectures"],
        "user_count": 250,
        "school_ext": "gatech",
        "short_number": "cs101",
        "anonymity": "full_anonymity",
        "auto_join": "no_autojoin",
        "config": {
            "roles": _roles_matrix(),
            "class_sections": {"allow_enroll": 1, "sections": ["A", "B"]},
            "default_posts_to_private": False,
            "disable_folders": False,
            "unknown_future_key": 123,
        },
        "also_unknown_top_level": "ignored",
    }
    entry.update(overrides)
    return entry


def _status_with(*entries: dict[str, Any]) -> dict[str, Any]:
    return {"networks": list(entries)}


# ── parse_network_entry ─────────────────────────────────────────────────


class TestParseNetworkEntry:
    def test_full_entry_parses_roles(self):
        info = parse_network_entry(_network_entry())
        assert isinstance(info.config, NetworkConfig)
        assert info.config.roles is not None
        assert info.config.roles.admin is not None
        assert info.config.roles.admin.can_post_anonymous_all is True
        assert info.config.roles.student is not None
        assert info.config.roles.student.question_edit is False

    def test_identity_and_slug_fields(self):
        info = parse_network_entry(_network_entry())
        assert info.id == info.nid == "mqsgm1zclb114z"
        assert info.school_ext == "gatech"
        assert info.short_number == "cs101"
        assert info.users == 250

    def test_unknown_keys_tolerated(self):
        info = parse_network_entry(_network_entry())
        assert info.name == "CS 101"  # parsed despite unknown extras above

    def test_missing_config_yields_none(self):
        info = parse_network_entry({"id": "n1"})
        assert info.config is None
        assert info.nid == "n1"

    def test_non_dict_config_yields_none(self):
        info = parse_network_entry({"id": "n1", "config": [1, 2]})
        assert info.config is None

    def test_roles_present_but_malformed_entries_tolerated(self):
        entry = _network_entry()
        assert isinstance(entry["config"], dict)
        entry["config"]["roles"] = {"student": {"new_post": "yes"}}
        info = parse_network_entry(entry)
        # Pydantic coerces truthy strings for bool fields; must not raise.
        assert info.config is not None
        assert info.config.roles is not None
        assert info.config.roles.student is not None
        assert info.config.roles.student.new_post is True


# ── NetworkInfo.can / resources_url ────────────────────────────────────


class TestNetworkInfoCapabilities:
    def test_can_true_for_permitted_action(self):
        info = parse_network_entry(_network_entry())
        assert info.can("ta", "new_post") is True
        assert info.can(UserRole.INSTRUCTOR, "admin_roster") is True

    def test_can_false_for_denied_action(self):
        info = parse_network_entry(_network_entry())
        assert info.can("student", "question_edit") is False

    def test_can_false_for_unknown_role_or_action(self):
        info = parse_network_entry(_network_entry())
        assert info.can("dean", "new_post") is False
        assert info.can("student", "teleport") is False

    def test_can_false_without_matrix(self):
        info = NetworkInfo(id="x")
        assert info.can("student", "new_post") is False

    def test_resources_url_normalizes_term(self):
        info = parse_network_entry(_network_entry())
        assert info.resources_url == "https://piazza.com/gatech/spring2024/cs101/home"

    def test_resources_url_empty_without_slugs(self):
        assert NetworkInfo(term="Fall 2030").resources_url == ""


# ── get_network_info ────────────────────────────────────────────────────


class TestGetNetworkInfo:
    @pytest.mark.asyncio
    async def test_found_returns_parsed_info(self):
        rpc = MagicMock()
        rpc.user_status = AsyncMock(return_value=_status_with(_network_entry()))
        info = await get_network_info(rpc, nid="mqsgm1zclb114z")
        assert info.name == "CS 101"
        assert info.can("ta", "new_post") is True

    @pytest.mark.asyncio
    async def test_absent_nid_raises_not_found(self):
        rpc = MagicMock()
        rpc.user_status = AsyncMock(return_value=_status_with(_network_entry()))
        with pytest.raises(NotFoundError, match="not found"):
            await get_network_info(rpc, nid="other")

    @pytest.mark.asyncio
    async def test_malformed_status_treated_as_not_found(self):
        """A non-dict status yields the empty-networks path -> NotFoundError."""
        rpc = MagicMock()
        rpc.user_status = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError, match="not found"):
            await get_network_info(rpc, nid="x")
