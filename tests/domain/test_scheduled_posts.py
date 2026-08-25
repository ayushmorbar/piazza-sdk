"""Unit tests for scheduled-post creation (network.save_draft flow)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.domain.posts import (
    _extract_draft_id,
    _to_epoch_ms,
    add_followup,
    create_post,
    schedule_post,
)
from piazza_sdk.exceptions import ContentError, ValidationError


def _rpc_with_draft(draft_response: Any) -> MagicMock:
    rpc = MagicMock()
    rpc.network_id = "test_nid"
    rpc.network_save_draft = AsyncMock(return_value=draft_response)
    rpc.content_create = AsyncMock(return_value={"id": "new_post_1", "nr": 42})
    return rpc


class TestToEpochMs:
    def test_datetime_utc(self):
        dt = datetime(2026, 1, 1, 0, 0, 30, tzinfo=UTC)
        assert _to_epoch_ms(dt) == 1767225630000

    def test_naive_datetime_treated_as_utc(self):
        naive = datetime(2026, 1, 1, 0, 0, 30)  # noqa: DTZ001 - naive is the point
        assert _to_epoch_ms(naive) == 1767225630000

    def test_passthrough_number(self):
        assert _to_epoch_ms(1893456000000) == 1893456000000
        assert _to_epoch_ms(1893456000000.5) == 1893456000000

    @pytest.mark.parametrize("bad", [True, "soon", None, [1]])
    def test_invalid_shapes_rejected(self, bad):
        with pytest.raises(ValidationError):
            _to_epoch_ms(bad)


class TestExtractDraftId:
    def test_bare_string(self):
        assert _extract_draft_id("abc123") == "abc123"

    def test_dict_id(self):
        assert _extract_draft_id({"id": "d1"}) == "d1"

    def test_nested_draft_id(self):
        assert _extract_draft_id({"draft": {"draftId": "d2"}}) == "d2"

    def test_int_coerced(self):
        assert _extract_draft_id({"id": 77}) == "77"

    def test_missing_raises_content_error(self):
        with pytest.raises(ContentError, match="draft ID"):
            _extract_draft_id({"nope": True})


class TestSchedulePost:
    """Two-step wire flow: network.save_draft then content.create."""

    async def test_payload_shapes_and_confirmation(self):
        rpc = _rpc_with_draft("draft_9")  # live returns a bare string
        rpc.content_create = AsyncMock(return_value={"scheduled": True})
        at = datetime(2030, 6, 1, 12, 0, 0, tzinfo=UTC)

        result = await schedule_post(
            rpc, title="Future Q", content="<p>body</p>", at=at, folders=["hw1"]
        )
        assert result.draft_id == "draft_9"
        assert result.scheduled is True

        draft_call = rpc.network_save_draft.await_args.kwargs["draft"]
        assert draft_call["folders"] == ["hw1"]
        assert draft_call["txt"] == {"post_summary": "Future Q"}
        btn = draft_call["btn"]
        assert btn["schedule_later"] is True
        assert btn["post_type_question"] is True
        assert btn["post_type_note"] is False
        assert isinstance(btn["schedule_later_time"], int)

        create_params = rpc.content_create.await_args.kwargs
        assert create_params["subject"] == "Future Q"
        assert create_params["draftId"] == "draft_9"
        assert create_params["config"]["schedule_later"] is True
        assert create_params["config"]["schedule_later_time"] == btn["schedule_later_time"]

    async def test_scheduled_flag_defaults_false_on_empty_result(self):
        rpc = _rpc_with_draft({"id": "d"})
        rpc.content_create = AsyncMock(return_value={})
        result = await schedule_post(rpc, title="t", content="c", at=1)
        assert result.draft_id == "d"
        assert result.scheduled is False

    async def test_note_button_state(self):
        rpc = _rpc_with_draft({"id": "d"})
        await schedule_post(rpc, title="n", content="c", at=1, post_type="note")
        btn = rpc.network_save_draft.await_args.kwargs["draft"]["btn"]
        assert btn["post_type_note"] is True
        assert btn["post_type_question"] is False

    async def test_poll_rejected(self):
        rpc = _rpc_with_draft({})
        with pytest.raises(ValidationError, match="poll"):
            await schedule_post(rpc, title="t", content="c", at=1, post_type="poll")
        rpc.network_save_draft.assert_not_called()

    async def test_default_folder_general(self):
        rpc = _rpc_with_draft({"id": "d"})
        await schedule_post(rpc, title="t", content="c", at=1)
        draft = rpc.network_save_draft.await_args.kwargs["draft"]
        assert draft["folders"] == ["General"]

    async def test_config_merge_does_not_clobber_caller_keys(self):
        rpc = _rpc_with_draft({"id": "d"})
        await schedule_post(rpc, title="t", content="c", at=1, config={"custom": 1})
        cfg = rpc.content_create.await_args.kwargs["config"]
        assert cfg["custom"] == 1
        assert cfg["schedule_later"] is True

    async def test_unrecognized_draft_response_raises(self):
        rpc = _rpc_with_draft({"unexpected": True})
        with pytest.raises(ContentError, match="draft ID"):
            await schedule_post(rpc, title="t", content="c", at=1)

    @pytest.mark.parametrize("empty", [{"title": ""}, {"content": " "}])
    async def test_empty_fields_rejected(self, empty):
        rpc = _rpc_with_draft({})
        kwargs: dict[str, str] = {"title": "t", "content": "c"}
        kwargs.update(empty)
        with pytest.raises(ValidationError):
            await schedule_post(rpc, at=1, **kwargs)


# ---------------------------------------------------------------------------
# Private posts to staff (feed_groups contract)
# ---------------------------------------------------------------------------


class TestCreatePostPrivate:
    """private_to_staff injects config.feed_groups = instr_{nid},{uid}."""

    @staticmethod
    def _rpc(uid: str | None = "u_42") -> MagicMock:
        rpc = MagicMock()
        rpc.network_id = "nid_1"
        rpc.content_create = AsyncMock(return_value={"id": "p_new"})
        if uid is not None:
            rpc.get_user_profile = AsyncMock(return_value={"user_id": uid})
        else:
            rpc.get_user_profile = AsyncMock(return_value={})
        return rpc

    async def test_resolves_uid_and_injects_feed_groups(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c", private_to_staff=True)
        cfg = rpc.content_create.await_args.kwargs["config"]
        assert cfg == {"feed_groups": "instr_nid_1,u_42"}
        rpc.get_user_profile.assert_awaited_once()

    async def test_explicit_uid_skips_profile_call(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c", private_to_staff=True, author_uid="u_pre")
        cfg = rpc.content_create.await_args.kwargs["config"]
        assert cfg == {"feed_groups": "instr_nid_1,u_pre"}
        rpc.get_user_profile.assert_not_called()

    async def test_unresolvable_uid_raises_validation(self):
        rpc = self._rpc(uid=None)
        with pytest.raises(ValidationError, match="author UID"):
            await create_post(rpc, title="t", content="c", private_to_staff=True)

    async def test_merges_with_caller_config_without_clobber(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c", private_to_staff=True, config={"custom": 7})
        cfg = rpc.content_create.await_args.kwargs["config"]
        assert cfg["custom"] == 7
        assert cfg["feed_groups"] == "instr_nid_1,u_42"

    async def test_no_config_key_when_public(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c")
        assert "config" not in rpc.content_create.await_args.kwargs


# ---------------------------------------------------------------------------
# Announcement + bypass_email flags (hfaran parity)
# ---------------------------------------------------------------------------


class TestCreatePostFlags:
    """is_announcement -> config key; bypass_email -> prof_override."""

    @staticmethod
    def _rpc() -> MagicMock:
        rpc = MagicMock()
        rpc.network_id = "nid_1"
        rpc.content_create = AsyncMock(return_value={"id": "p_new"})
        return rpc

    async def test_defaults_omit_both_keys(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c")
        kwargs = rpc.content_create.await_args.kwargs
        assert "prof_override" not in kwargs
        assert "config" not in kwargs

    async def test_announcement_injects_config_int(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c", is_announcement=True)
        assert rpc.content_create.await_args.kwargs["config"] == {"is_announcement": 1}

    async def test_bypass_email_sets_prof_override_and_config(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c", bypass_email=True)
        kwargs = rpc.content_create.await_args.kwargs
        assert kwargs["prof_override"] is True
        assert kwargs["config"] == {"bypass_email": 1}

    async def test_combined_flags(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c", is_announcement=True, bypass_email=True)
        kwargs = rpc.content_create.await_args.kwargs
        assert kwargs["prof_override"] is True
        assert kwargs["config"] == {"bypass_email": 1, "is_announcement": 1}

    async def test_caller_config_wins_over_flags(self):
        rpc = self._rpc()
        await create_post(
            rpc, title="t", content="c", bypass_email=True, config={"bypass_email": 0}
        )
        cfg = rpc.content_create.await_args.kwargs["config"]
        assert cfg["bypass_email"] == 0

    async def test_explicit_prof_override_kwarg_not_duplicated(self):
        rpc = self._rpc()
        await create_post(rpc, title="t", content="c", bypass_email=True)
        # flag path owns the key exactly once
        kwargs = rpc.content_create.await_args.kwargs
        assert list(kwargs).count("prof_override") == 1


# ---------------------------------------------------------------------------
# Instructor follow-up (config.ionly)
# ---------------------------------------------------------------------------


class TestInstructorFollowup:
    """add_followup(instructor=True) injects config.ionly with editor marker."""

    @staticmethod
    def _rpc() -> MagicMock:
        rpc = MagicMock()
        rpc.content_create = AsyncMock(return_value={"id": "fu_1"})
        return rpc

    async def test_ionly_true_with_editor_marker(self):
        rpc = self._rpc()
        await add_followup(rpc, post_id="p1", content="note", instructor=True)
        kwargs = rpc.content_create.await_args.kwargs
        assert kwargs["type"] == "followup"
        assert kwargs["config"] == {"editor": "rte", "ionly": True}

    async def test_no_config_when_not_instructor(self):
        rpc = self._rpc()
        await add_followup(rpc, post_id="p1", content="hi")
        assert "config" not in rpc.content_create.await_args.kwargs

    async def test_caller_config_wins_over_defaults(self):
        rpc = self._rpc()
        await add_followup(
            rpc, post_id="p1", content="x", instructor=True, config={"editor": "plain"}
        )
        cfg = rpc.content_create.await_args.kwargs["config"]
        assert cfg == {"editor": "plain", "ionly": True}
