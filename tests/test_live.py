"""Consolidated live API verification suite for Piazza SDK.

Opt-in only: credentials are read from environment variables (or a local .env)
and tests are skipped unless credentials are provided. Excluded from default
test runs via the `live` pytest marker.

Run explicitly with:
    pytest -m live tests/test_live.py -v -s
"""

from __future__ import annotations

import logging
import os

import pytest

from piazza_sdk.adapters.auth import SessionState
from piazza_sdk.adapters.http import RPC
from piazza_sdk.adapters.session import SessionStateManager
from piazza_sdk.api.network import Network
from piazza_sdk.api.piazza import Piazza
from piazza_sdk.config import PiazzaConfig, SessionConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Credentials from environment (never hardcoded) ───────────────────
INSTRUCTOR_EMAIL = os.environ.get("PIAZZA_INSTRUCTOR_EMAIL") or os.environ.get("PIAZZA_EMAIL", "")
INSTRUCTOR_PASSWORD = os.environ.get("PIAZZA_INSTRUCTOR_PASSWORD") or os.environ.get(
    "PIAZZA_PASSWORD", ""
)
COURSE_ID = os.environ.get("PIAZZA_COURSE_ID", "")

STUDENT_EMAIL = os.environ.get("PIAZZA_STUDENT_EMAIL", "")
STUDENT_PASSWORD = os.environ.get("PIAZZA_STUDENT_PASSWORD", "")
STUDENT_COURSE_ID = os.environ.get("PIAZZA_STUDENT_COURSE_ID", "") or COURSE_ID

live = pytest.mark.live
requires_instructor_creds = pytest.mark.skipif(
    not (INSTRUCTOR_EMAIL and INSTRUCTOR_PASSWORD and COURSE_ID),
    reason="set PIAZZA_INSTRUCTOR_EMAIL / PIAZZA_INSTRUCTOR_PASSWORD / PIAZZA_COURSE_ID",
)
requires_student_creds = pytest.mark.skipif(
    not (STUDENT_EMAIL and STUDENT_PASSWORD and STUDENT_COURSE_ID),
    reason="set PIAZZA_STUDENT_EMAIL / PIAZZA_STUDENT_PASSWORD / PIAZZA_STUDENT_COURSE_ID",
)


@live
@requires_instructor_creds
@pytest.mark.asyncio
async def test_instructor_live_flow():
    """Instructor workflow: login → check alive → feed → post details → stats → search → logout."""
    config = PiazzaConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("✓ Instructor login OK")

        alive = await session.is_session_alive()
        assert alive, "Session should be alive"
        logger.info("✓ Session alive check OK")

        rpc = RPC(session=session, base_url=config.base_url, network_id=COURSE_ID)
        network = Network(rpc, COURSE_ID)

        # 1. Feed & Post Inspection
        feed = await network.get_feed(limit=3)
        assert feed.feed, "Feed should have items"
        logger.info("✓ Feed retrieved: %d items", len(feed.feed))

        first_item = feed.feed[0]
        post = await network.get_post(first_item.id)
        assert post.id == first_item.id
        logger.info(
            "✓ Post retrieved: %s (type=%s, %d children)", post.id, post.type, len(post.children)
        )

        # 2. Statistics & Users
        stats = await network.get_statistics()
        logger.info(
            "✓ Stats retrieved: total_posts=%d, questions=%d, users=%d",
            stats.total.posts,
            stats.total.questions,
            len(stats.users),
        )

        users = await network.get_users()
        logger.info("✓ Users retrieved: %d users", len(users))

        # 3. Search
        search_feed = await network.search("test", limit=2)
        logger.info("✓ Search returned %d items", len(search_feed.feed))

        # 4. Logout
        await session.logout()
        assert session.state == SessionState.CLOSED
        logger.info("✓ Instructor logout OK")


@live
@requires_student_creds
@pytest.mark.asyncio
async def test_student_live_flow():
    """Student workflow: login → feed → post details → search → logout."""
    config = PiazzaConfig(course_id=STUDENT_COURSE_ID)
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

        search_feed = await network.search("discussion", limit=2)
        logger.info("✓ Search returned %d items", len(search_feed.feed))

        await session.logout()
        assert session.state == SessionState.CLOSED
        logger.info("✓ Student logout OK")


@live
@requires_instructor_creds
@requires_student_creds
@pytest.mark.asyncio
async def test_dual_role_cross_interaction():
    """Dual-Role: Student creates a question → Instructor answers and endorses
    → Instructor deletes.
    """
    # 1. Student creates a post and follow-up
    student_config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(student_config) as student_session:
        await student_session.login(email=STUDENT_EMAIL, password=STUDENT_PASSWORD)
        student_rpc = RPC(
            session=student_session, base_url=student_config.base_url, network_id=COURSE_ID
        )
        student_network = Network(student_rpc, COURSE_ID)

        post_response = await student_network.create_post(
            post_type="question",
            folders=["other"],
            title="Cross-Role Test Post",
            content="This is a test post created by the student.",
            bypass_email=True,
            silent_update=True,
        )
        post_id = post_response.id
        logger.info("✓ Student created post: %s", post_id)

        followup = await student_network.create_followup(
            post=post_id, content="Student followup question."
        )
        logger.info("✓ Student created followup: %s", followup.id)

    # 2. Instructor interacts with student's post
    instructor_config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(instructor_config) as instructor_session:
        await instructor_session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        instructor_rpc = RPC(
            session=instructor_session, base_url=instructor_config.base_url, network_id=COURSE_ID
        )
        instructor_network = Network(instructor_rpc, COURSE_ID)

        # Answer as instructor
        await instructor_network.answer_post(
            post_id=post_id, content="Instructor answer to the main post.", instructor_answer=True
        )
        logger.info("✓ Instructor answered post.")

        # Endorse
        await instructor_network.endorse_post(post_id=post_id)
        logger.info("✓ Instructor endorsed post.")

        # Delete to clean up
        await instructor_network.delete_post(post_id)
        logger.info("✓ Instructor deleted test post: %s", post_id)


@live
@requires_instructor_creds
@pytest.mark.asyncio
async def test_har_endpoints_live():
    """Live verification of newly mapped HAR utility endpoints."""
    config = PiazzaConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        piazza = Piazza(session)

        # 1. Global events info
        events = await piazza.get_my_events_info()
        assert isinstance(events, dict)
        logger.info("✓ get_my_events_info OK")

        # 2. Unread messages
        unread = await piazza.get_unread_message_count()
        assert isinstance(unread, int)
        logger.info("✓ get_unread_message_count: %d", unread)

        # 3. HTML sanitization
        clean_html = await piazza.sanitize_html(text="<p>Hello <b>world</b></p>")
        assert isinstance(clean_html, dict)
        assert "Hello" in clean_html.get("text", "")
        logger.info("✓ sanitize_html OK")

        # 4. Page event
        await piazza.page_event(type="view", page="test_page")
        logger.info("✓ page_event OK")
