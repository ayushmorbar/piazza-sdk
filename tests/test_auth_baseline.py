"""Baseline auth test — validates login/logout against the live Piazza API.

Opt-in only: credentials are read from environment variables (or a local
``.env``) and every test is skipped unless they are provided. These tests
are excluded from default pytest runs via the ``live`` marker.

Run explicitly with:
    pytest -m live tests/test_auth_baseline.py -v
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pytest

from piazza_sdk.adapters.auth import SessionConfig, SessionState
from piazza_sdk.adapters.http import RPC
from piazza_sdk.adapters.session import SessionStateManager

# INFO (not DEBUG): DEBUG echoes full request details including cookies.
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
async def test_instructor_login():
    """Test instructor login — establish baseline."""
    config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("Instructor login OK — session alive")


@live
@requires_instructor_creds
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


@live
@requires_student_creds
@pytest.mark.asyncio
async def test_student_login():
    """Test student login — establish baseline."""
    config = SessionConfig(course_id=STUDENT_COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=STUDENT_EMAIL, password=STUDENT_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("Student login OK — session alive")


@live
@requires_instructor_creds
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
