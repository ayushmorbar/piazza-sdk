"""Shared test fixtures for Piazza SDK tests."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from piazza_sdk.auth import SessionConfig
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType, PostType, UserRole
from piazza_sdk.models.feed import FeedItem
from piazza_sdk.models.post import Post
from piazza_sdk.models.user import User


@pytest.fixture
def session_config() -> SessionConfig:
    """Create a test SessionConfig."""
    return SessionConfig(
        email="test@example.com",
        password="testpassword123",
        base_url="https://piazza.com",
        network_id="test_network_123",
    )


@pytest.fixture
def sample_user() -> User:
    """Create a sample User for testing."""
    return User(
        id="user_123",
        name="Test User",
        email="user@example.com",
        role=UserRole.STUDENT,
        school="Test University",
        major="Computer Science",
        class_year="2025",
    )


@pytest.fixture
def sample_feed_item() -> FeedItem:
    """Create a sample FeedItem for testing."""
    return FeedItem(
        id="post_123",
        subject="Test Post Subject",
        type=FeedItemType.QUESTION,
        created=datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
        updated=datetime(2025, 1, 15, 12, 45, tzinfo=UTC),
        default_anonymity=FeedItemDefaultAnonymity.FALSE,
        uid="user_456",
        folder="Homework 1",
        no_answer=True,
        is_pinned=False,
        follows=False,
        viewed=True,
        reputation=0,
        badge="",
        tags=["homework", "question"],
    )


@pytest.fixture
def sample_post() -> Post:
    """Create a sample Post for testing."""
    return Post(
        id="post_789",
        title="How to solve this integral?",
        subject="Calculus II - Integration by Parts",
        type=PostType.QUESTION,
        author="Student User",
        user_name="Student User",
        nr=1234,
        raw={"id": "post_789"},
        tags=["calculus", "homework"],
        folder="HW3",
        views=42,
    )


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock SessionStateManager with client and config attributes."""
    session = MagicMock()
    session.config = MagicMock()
    session.config.base_url = "https://piazza.com"
    session.client = AsyncMock()
    session.needs_refresh = False
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_rpc() -> MagicMock:
    """Create a mock RPC client."""
    rpc = MagicMock()
    rpc._request = AsyncMock(return_value={})
    return rpc
