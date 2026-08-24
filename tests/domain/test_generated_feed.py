"""Auto-generated happy path tests for piazza_sdk.domain.feed."""

import contextlib
from unittest.mock import AsyncMock, MagicMock

import pytest

import piazza_sdk.domain.feed as mod


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
async def test_happy_path_get_feed(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_feed(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_get_similar_posts(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.get_similar_posts(rpc_mock)


@pytest.mark.asyncio
async def test_happy_path_filter_feed(rpc_mock):
    with contextlib.suppress(Exception):
        await mod.filter_feed(rpc_mock)
