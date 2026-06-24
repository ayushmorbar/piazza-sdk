"""Live API verification for Phase 1–5 changes.

Run with: python -m pytest tests/test_live_phase5.py -v -s
"""

from __future__ import annotations

import logging

import pytest

from piazza_sdk.adapters.auth import SessionConfig, SessionState
from piazza_sdk.adapters.http import RPC
from piazza_sdk.adapters.session import SessionStateManager
from piazza_sdk.api.network import Network

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTRUCTOR_EMAIL = "regita2049@cadebek.com"
INSTRUCTOR_PASSWORD = "cadebek.com"
COURSE_ID = "mqsgm1zclb114z"

STUDENT_EMAIL = "galahej384@divahd.com"
STUDENT_PASSWORD = "divahd.com"
STUDENT_COURSE_ID = "mqsgm1zclb114z"


@pytest.mark.asyncio
async def test_instructor_login_and_feed():
    """Instructor: login → feed → post → stats → logout."""
    config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("✓ Instructor login OK")

        alive = await session.is_session_alive()
        assert alive, "Session should be alive"
        logger.info("✓ Session alive check OK")

        rpc = RPC(session=session, base_url=config.base_url, network_id=COURSE_ID)
        network = Network(rpc, COURSE_ID)

        feed = await network.get_feed(limit=3)
        assert feed.feed, "Feed should have items"
        logger.info("✓ Feed retrieved: %d items", len(feed.feed))

        first_item = feed.feed[0]
        logger.info(
            "  First item: id=%s type=%s folder=%s",
            first_item.id,
            first_item.type,
            first_item.folder_num,
        )

        post = await network.get_post(first_item.id)
        logger.info(
            "✓ Post retrieved: %s (type=%s, has %d children)",
            post.id,
            post.type,
            len(post.children),
        )

        stats = await network.get_statistics()
        logger.info(
            "✓ Stats retrieved: total_posts=%d, total_questions=%d, users=%d, profs=%d",
            stats.total.posts,
            stats.total.questions,
            len(stats.users),
            len(stats.profs),
        )

        users = await network.get_users()
        logger.info("✓ Users retrieved: %d users", len(users))

        search_feed = await network.search("question", limit=2)
        logger.info("✓ Search returned %d items", len(search_feed.feed))

        await session.logout()
        assert session.state == SessionState.CLOSED
        logger.info("✓ Logout OK")


@pytest.mark.asyncio
async def test_student_login_and_feed():
    """Student: login → feed → post → search → logout."""
    config = SessionConfig(course_id=STUDENT_COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=STUDENT_EMAIL, password=STUDENT_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("✓ Student login OK")

        rpc = RPC(session=session, base_url=config.base_url, network_id=STUDENT_COURSE_ID)
        network = Network(rpc, STUDENT_COURSE_ID)

        feed = await network.get_feed(limit=3)
        assert feed.feed, "Feed should have items"
        logger.info("✓ Feed retrieved: %d items", len(feed.feed))

        first_item = feed.feed[0]
        post = await network.get_post(first_item.id)
        logger.info("✓ Post retrieved: %s (type=%s)", post.id, post.type)

        if post.student_answer:
            logger.info("  Student answer found: %s", post.student_answer.id)
        if post.instructor_answer:
            logger.info("  Instructor answer found: %s", post.instructor_answer.id)

        search_feed = await network.search("discussion", limit=2)
        logger.info("✓ Search returned %d items", len(search_feed.feed))

        await session.logout()
        assert session.state == SessionState.CLOSED
        logger.info("✓ Logout OK")
