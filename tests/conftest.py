"""Shared test fixtures and configuration for Piazza SDK test suite."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from piazza_sdk.config import PiazzaConfig, SessionConfig
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType, PostType
from piazza_sdk.models.feed import FeedItem
from piazza_sdk.models.post import Post
from piazza_sdk.models.user import User

# ── Environment Loader for Live Tests ─────────────────────────────────


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader so live tests are self-sufficient without extra dependencies."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


# ── Shared Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def session_config() -> SessionConfig:
    """Create a standard test SessionConfig instance."""
    return SessionConfig(course_id="test_course_123", base_url="https://piazza.com")


@pytest.fixture
def piazza_config() -> PiazzaConfig:
    """Create a standard test PiazzaConfig instance."""
    return PiazzaConfig(course_id="test_course_123", base_url="https://piazza.com")


@pytest.fixture
def sample_user() -> User:
    """Create a sample User for model testing."""
    return User(id="user_123", name="Test User", email="user@example.com", role=["student"])


@pytest.fixture
def sample_feed_item() -> FeedItem:
    """Create a sample FeedItem for model testing."""
    return FeedItem(
        id="post_123",
        subject="Test Post Subject",
        type=FeedItemType.QUESTION,
        created=datetime(2025, 1, 15, 10, 30, tzinfo=UTC),
        updated=datetime(2025, 1, 15, 12, 45, tzinfo=UTC),
        default_anonymity=FeedItemDefaultAnonymity.NO,
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
    """Create a sample Post for model testing."""
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
    """Create a mock SessionStateManager with client, config, and state attributes."""
    session = MagicMock()
    session.config = MagicMock()
    session.config.base_url = "https://piazza.com"
    session.config.course_id = "test_course_123"
    session.client = AsyncMock(spec=httpx.AsyncClient)
    session.needs_refresh = False
    session.refresh = AsyncMock()
    session.handle_auth_error = AsyncMock(return_value=False)
    session.is_session_alive = AsyncMock(return_value=True)
    return session


@pytest.fixture
def mock_rpc() -> MagicMock:
    """Create a mock RPC client for testing facades."""
    rpc = MagicMock()
    rpc.base_url = "https://piazza.com"
    rpc.network_id = "test_course_123"
    rpc.call = AsyncMock(return_value={})
    rpc._request = AsyncMock(return_value={})
    return rpc
