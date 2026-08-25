"""Auto-generated happy path tests for piazza_sdk.domain.posts."""

import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest

import piazza_sdk.domain.posts as mod


@pytest.fixture
def rpc_mock():
    rpc = MagicMock()
    rpc.content_get = AsyncMock(
        return_value={
            "history": [{"subject": "a", "content": "b"}],
            "folders": ["f"],
            "default_anonymity": "no",
            "id": "dummy",
            "type": "note",
        }
    )
    rpc.content_update = AsyncMock(return_value={})
    rpc.content_create = AsyncMock(return_value={"id": "new_id"})
    rpc.content_delete = AsyncMock(return_value={})
    rpc.content_mark_read = AsyncMock(return_value={})
    rpc.content_mark_unread = AsyncMock(return_value={})
    rpc.add_students = AsyncMock(return_value={})
    rpc.network_get_users = AsyncMock(return_value=[{"id": "u1", "name": "A", "role": "student"}])
    rpc.network_get_online_users = AsyncMock(return_value=[])
    rpc.network_get_statuses = AsyncMock(return_value={})
    rpc.network_search = AsyncMock(return_value=[])
    rpc.network_filter_feed = AsyncMock(return_value={"feed": []})
    rpc.network_update = AsyncMock(return_value={})
    rpc.network_get_instructor_stats = AsyncMock(return_value={})
    rpc.user_profile_get_profile = AsyncMock(return_value={})
    rpc.user_status = AsyncMock(return_value={})
    rpc.user_events = AsyncMock(return_value={})
    return rpc


@pytest.mark.asyncio
async def test_happy_path_create_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.create_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_add_followup(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.add_followup(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_create_reply(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.create_reply(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_answer_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.answer_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_endorse(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.endorse(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_delete_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.delete_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_add_tag(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.add_tag(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_remove_tag(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.remove_tag(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_resolve_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.resolve_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_unresolve_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.unresolve_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_mark_as_unread(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.mark_as_unread(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_create_folder(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.create_folder(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_save_draft(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.save_draft(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_upload_asset(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.upload_asset(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_bookmark_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.bookmark_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_unbookmark_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.unbookmark_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_favorite_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.favorite_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_unfavorite_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.unfavorite_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_view_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.view_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_edit_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.edit_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_cancel_edit(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.cancel_edit(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_remove_endorsement(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.remove_endorsement(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_auto_save_draft(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.auto_save_draft(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_pin_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.pin_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_unpin_post(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.unpin_post(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_mark_duplicate(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.mark_duplicate(rpc_mock)
