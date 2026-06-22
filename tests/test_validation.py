"""Tests for input validation in Network and utils."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from piazza_sdk import Network, Piazza
from piazza_sdk.exceptions import ValidationError


class TestNetworkInputValidation:
    """Verify Network methods reject invalid inputs."""

    @pytest.fixture
    def network(self, mock_session) -> Network:
        piazza = Piazza(mock_session)
        return piazza.network("12345")

    @pytest.mark.asyncio
    async def test_get_post_empty_id(self, network):
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await network.get_post("")

    @pytest.mark.asyncio
    async def test_get_post_whitespace_id(self, network):
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await network.get_post("   ")

    @pytest.mark.asyncio
    async def test_search_empty_query(self, network):
        with pytest.raises(ValidationError, match="query must be non-empty"):
            await network.search("")

    @pytest.mark.asyncio
    async def test_search_whitespace_query(self, network):
        with pytest.raises(ValidationError, match="query must be non-empty"):
            await network.search("   \t  ")

    @pytest.mark.asyncio
    async def test_create_post_empty_title(self, network):
        with pytest.raises(ValidationError, match="title must be non-empty"):
            await network.create_post(title="", content="some content")

    @pytest.mark.asyncio
    async def test_create_post_empty_content(self, network):
        with pytest.raises(ValidationError, match="content must be non-empty"):
            await network.create_post(title="My Title", content="")

    @pytest.mark.asyncio
    async def test_create_followup_empty_content(self, network):
        with pytest.raises(ValidationError, match="content must be non-empty"):
            await network.create_followup(post="cl123", content="")

    @pytest.mark.asyncio
    async def test_resolve_post_empty_id(self, network):
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await network.resolve_post("")

    @pytest.mark.asyncio
    async def test_valid_search_does_not_raise(self, network):
        with patch.object(
            network._rpc, "search", new_callable=AsyncMock, return_value={"feed": []}
        ):
            feed = await network.search("valid query")
            assert feed.feed == []

    @pytest.mark.asyncio
    async def test_valid_create_post_does_not_raise(self, network):
        with patch.object(
            network._rpc, "content_create", new_callable=AsyncMock, return_value={"id": "cl_new"}
        ):
            result = await network.create_post(title="Valid Title", content="Valid content")
            assert result == {"id": "cl_new"}
