"""Offline smoke tests for Piazza SDK API surface.

Verifies critical import paths, model instantiation, and mock-based
API flows without network calls.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from piazza_sdk import Feed, FeedItem, Network, Piazza, Post, SessionConfig


class TestSmokeSessionConfig:
    """Verify SessionConfig instantiation and defaults."""

    def test_session_config_defaults(self):
        """SessionConfig has correct default user_agent with CalVer."""
        config = SessionConfig(course_id="test_course")
        assert config.course_id == "test_course"
        assert "piazza-sdk-python/" in config.user_agent
        assert config.timeout == 30.0

    def test_session_config_custom_ua(self):
        """SessionConfig accepts custom user_agent."""
        config = SessionConfig(course_id="c", user_agent="myapp/2.0")
        assert config.user_agent == "myapp/2.0"


class TestSmokePiazzaToNetwork:
    """Verify Piazza client creates Network instances correctly."""

    def test_piazza_network_creates_instance(self, mock_session):
        """Piazza.network() returns a Network for a given NID."""
        piazza = Piazza(mock_session)
        network = piazza.network("12345")
        assert isinstance(network, Network)
        assert network._nid == "12345"

    def test_piazza_network_caches(self, mock_session):
        """Piazza.network() caches Network instances by NID."""
        piazza = Piazza(mock_session)
        n1 = piazza.network("111")
        n2 = piazza.network("111")
        assert n1 is n2

    def test_piazza_network_different_nids(self, mock_session):
        """Different NIDs produce different Network instances."""
        piazza = Piazza(mock_session)
        n1 = piazza.network("111")
        n2 = piazza.network("222")
        assert n1 is not n2


class TestSmokeMockedGetPost:
    """Verify mocked get_post returns a validated Post model."""

    @pytest.mark.asyncio
    async def test_get_post_returns_post(self, mock_session):
        """Network.get_post with mocked RPC returns a Post model."""
        piazza = Piazza(mock_session)
        network = piazza.network("12345")

        now = datetime.now()
        raw_post = {
            "id": "cl123",
            "title": "Smoke test post",
            "type": "question",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "config": {},
            "tags": [],
            "children": [],
        }

        with patch.object(
            network._rpc, "content_get", new_callable=AsyncMock, return_value=raw_post
        ):
            post = await network.get_post("cl123")

        assert isinstance(post, Post)
        assert post.id == "cl123"
        assert post.title == "Smoke test post"


class TestSmokeMockedGetFeed:
    """Verify mocked get_feed returns a validated Feed model."""

    @pytest.mark.asyncio
    async def test_get_feed_returns_feed(self, mock_session):
        """Network.get_feed with mocked RPC returns a Feed model."""
        piazza = Piazza(mock_session)
        network = piazza.network("12345")

        now = datetime.now()
        raw_feed = {
            "feed": [
                {
                    "id": "cl100",
                    "subject": "First post",
                    "type": "question",
                    "created": now.isoformat(),
                },
                {
                    "id": "cl200",
                    "subject": "Second post",
                    "type": "note",
                    "created": now.isoformat(),
                },
            ]
        }

        with patch.object(
            network._rpc, "get_my_feed", new_callable=AsyncMock, return_value=raw_feed
        ):
            feed = await network.get_feed(limit=5)

        assert isinstance(feed, Feed)
        assert len(feed.feed) == 2
        assert isinstance(feed.feed[0], FeedItem)
        assert feed.feed[0].id == "cl100"
        assert feed.feed[1].subject == "Second post"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
