"""Live API verification for Phase 1–5 changes.

Opt-in only: credentials are read from environment variables (or a local
``.env``) and every test is skipped unless they are provided. Excluded
from default runs via the ``live`` marker.

Run explicitly with:
    pytest -m live tests/test_live_phase5.py -v -s
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from piazza_sdk.adapters.auth import SessionConfig, SessionState
from piazza_sdk.adapters.http import RPC
from piazza_sdk.adapters.session import SessionStateManager
from piazza_sdk.api.network import Network

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_dotenv(path: Path = Path(".env")) -> None:
    """Minimal .env loader so live tests are self-sufficient (no dotenv dep)."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

# ── Credentials from environment (never hardcoded) ───────────────────
INSTRUCTOR_EMAIL = os.environ.get("PIAZZA_INSTRUCTOR_EMAIL") or os.environ.get("PIAZZA_EMAIL", "")
INSTRUCTOR_PASSWORD = os.environ.get("PIAZZA_INSTRUCTOR_PASSWORD") or os.environ.get(
    "PIAZZA_PASSWORD", ""
)
COURSE_ID = os.environ.get("PIAZZA_COURSE_ID", "")

STUDENT_EMAIL = os.environ.get("PIAZZA_STUDENT_EMAIL", "")
STUDENT_PASSWORD = os.environ.get("PIAZZA_STUDENT_PASSWORD", "")
STUDENT_COURSE_ID = os.environ.get("PIAZZA_STUDENT_COURSE_ID", "")

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


@live
@requires_student_creds
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


@live
@requires_instructor_creds
@requires_student_creds
@pytest.mark.asyncio
async def test_cross_role_interaction():
    """Dual-Role: Student creates a post → Instructor answers and endorses it
    → Instructor deletes it.
    """
    # 1. Student creates a post
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

        # 2. Student adds a followup
        followup_id = await student_network.create_followup(
            post=post_id, content="Student followup question."
        )
        logger.info("✓ Student created followup: %s", followup_id)

    # 3. Instructor interacts with it
    instructor_config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(instructor_config) as instructor_session:
        await instructor_session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        instructor_rpc = RPC(
            session=instructor_session, base_url=instructor_config.base_url, network_id=COURSE_ID
        )
        instructor_network = Network(instructor_rpc, COURSE_ID)

        # Instructor answers the followup
        await instructor_network.answer_post(
            post_id=post_id, content="Instructor answer to the main post.", instructor_answer=True
        )
        logger.info("✓ Instructor answered post.")

        # Instructor endorses the post
        await instructor_network.endorse_post(post_id=post_id)
        logger.info("✓ Instructor endorsed post.")

        # Instructor deletes the post to clean up
        await instructor_network.delete_post(post_id)
        logger.info("✓ Instructor deleted post: %s", post_id)
