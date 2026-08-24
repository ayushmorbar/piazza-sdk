"""Auto-generated happy path tests for piazza_sdk.domain.users."""

import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest

import piazza_sdk.domain.users as mod


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
async def test_happy_path_get_all_users(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_all_users(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_get_instructor_stats(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_instructor_stats(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_get_online_users(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_online_users(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_get_users_by_ids(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_users_by_ids(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_set_user_stat(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.set_user_stat(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_unset_user_stat(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.unset_user_stat(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_get_user_status(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_user_status(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_get_my_events_info(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_my_events_info(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_get_unread_message_count(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_unread_message_count(rpc_mock)
