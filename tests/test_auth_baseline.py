"""Baseline auth test — validates login/logout with live credentials.

Run with: python -m pytest tests/test_auth_baseline.py -v

This test runs against the real Piazza API to establish a baseline
before any model/endpoint changes.
"""

from __future__ import annotations

import logging

import pytest

from piazza_sdk.adapters.auth import SessionConfig, SessionState
from piazza_sdk.adapters.http import RPC
from piazza_sdk.adapters.session import SessionStateManager

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ── Instructor credentials ──────────────────────────────────────────
INSTRUCTOR_EMAIL = "regita2049@cadebek.com"
INSTRUCTOR_PASSWORD = "cadebek.com"
COURSE_ID = "mqsgm1zclb114z"

# ── Student credentials ─────────────────────────────────────────────
STUDENT_EMAIL = "galahej384@divahd.com"
STUDENT_PASSWORD = "divahd.com"
STUDENT_COURSE_ID = "mqsgm1zclb114z"


@pytest.mark.asyncio
async def test_instructor_login():
    """Test instructor login — establish baseline."""
    config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("Instructor login OK — session alive")


@pytest.mark.asyncio
async def test_instructor_login_check_logout():
    """Test instructor login → is_session_alive → logout."""
    config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED

        alive = await session.is_session_alive()
        logger.info("Session alive: %s", alive)
        assert alive, "Session should be alive right after login"

        await session.logout()
        assert session.state == SessionState.CLOSED


@pytest.mark.asyncio
async def test_student_login():
    """Test student login — establish baseline."""
    config = SessionConfig(course_id=STUDENT_COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=STUDENT_EMAIL, password=STUDENT_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("Student login OK — session alive")


@pytest.mark.asyncio
async def test_instructor_rpc_call():
    """Test instructor login → RPC call → logout."""
    config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED

        rpc = RPC(session=session, base_url=config.base_url, network_id=COURSE_ID)
        count = await rpc.get_unread_message_count()
        logger.info("Unread messages: %s", count)

        profile = await rpc.get_user_profile()
        logger.info("User profile keys: %s", list(profile.keys()))

        await session.logout()
