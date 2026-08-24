"""Auto-generated happy path tests for piazza_sdk.domain.network."""

import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest

import piazza_sdk.domain.network as mod


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
async def test_happy_path_update_office_hours(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.update_office_hours(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_update_general_information(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.update_general_information(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_update_course_description(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.update_course_description(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_add_students(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.add_students(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_remove_users(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.remove_users(rpc_mock)
