"""Consolidated live API verification suite for Piazza SDK.

Opt-in only: credentials are read from environment variables (or a local .env)
and tests are skipped unless credentials are provided. Excluded from default
test runs via the `live` pytest marker.

Run explicitly with:
    pytest -m live tests/test_live.py -v -s
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from piazza_sdk.adapters.auth import SessionState
from piazza_sdk.adapters.http import RPC
from piazza_sdk.adapters.session import SessionStateManager
from piazza_sdk.api.network import Network
from piazza_sdk.api.piazza import Piazza
from piazza_sdk.config import PiazzaConfig, SessionConfig
from piazza_sdk.exceptions import NotFoundError
from piazza_sdk.models.enums import UserRole
from piazza_sdk.models.user import EmailPrefEntry
from piazza_sdk.utils.normalization import extract_urls

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
async def test_instructor_live_all_queries():  # noqa: PLR0915
    """Instructor workflow verifying all read-only and query endpoints in data-dictionary.md."""
    config = PiazzaConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("✓ Instructor login OK")

        # 1. Session liveness
        alive = await session.is_session_alive()
        assert alive, "Session should be alive"
        logger.info("✓ Session alive check OK")

        piazza = Piazza(session)
        rpc = RPC(session=session, base_url=config.base_url, network_id=COURSE_ID)
        network = Network(rpc, COURSE_ID)

        # 2. User profile and class mappings
        profile = await piazza.get_user_profile()
        assert isinstance(profile, dict)
        classes = await piazza.get_user_classes()
        assert isinstance(classes, list)
        logger.info("✓ User profile and %d classes retrieved", len(classes))

        # 3. HAR Global utilities
        events = await piazza.get_my_events_info()
        assert isinstance(events, dict)
        unread = await piazza.get_unread_message_count()
        assert isinstance(unread, int)
        clean_html = await piazza.sanitize_html(text="<p>Hello <b>world</b></p>")
        assert isinstance(clean_html, dict)
        await piazza.page_event(type="view", page="test_page")
        logger.info("✓ Global HAR endpoints OK (events, unread=%d, sanitize, page_event)", unread)

        # 4. Feed queries & pagination
        feed = await network.get_feed(limit=5)
        assert feed.feed, "Feed should contain items"
        logger.info("✓ Feed retrieved: %d items (total=%d)", len(feed.feed), feed.total)

        unread_feed = await network.get_user_unread_feed(limit=3)
        assert hasattr(unread_feed, "feed")
        logger.info("✓ User unread feed retrieved: %d items", len(unread_feed.feed))

        posted_feed = await network.get_user_posted_feed(limit=3)
        assert hasattr(posted_feed, "feed")
        logger.info("✓ User posted feed retrieved: %d items", len(posted_feed.feed))

        first_item = feed.feed[0]
        post = await network.get_post(first_item.id)
        assert post.id == first_item.id
        assert isinstance(post.change_log, list)
        assert len(post.change_log) > 0, "change_log should be populated from wire 'change_log' key"
        assert isinstance(post.revisions, list)
        assert len(post.revisions) > 0, "revisions should be populated from wire 'history' key"
        assert post.revisions[0].revision >= 1, "revision numbers should be auto-numbered from 1"
        logger.info(
            "✓ Post retrieved: %s (type=%s, tags=%s, change_log=%d, revisions=%d)",
            post.id,
            post.type,
            post.tags,
            len(post.change_log),
            len(post.revisions),
        )

        # 5. Similar posts (Piazza retired content.get_similar endpoint -> raises NotFoundError)
        try:
            similar = await network.get_similar_posts(first_item.id)
            logger.info("✓ Similar posts returned: %d items", len(similar))
        except NotFoundError:
            logger.info("✓ Verified content.get_similar maps to NotFoundError per wire contract")

        # 6. Statistics, Instructor Stats & Online Users
        stats = await network.get_statistics()
        assert stats.total.posts >= 0
        assert stats.total.questions >= 0
        logger.info(
            "✓ Network stats: posts=%d, questions=%d, users=%d, daily=%d",
            stats.total.posts,
            stats.total.questions,
            len(stats.users),
            len(stats.daily),
        )

        inst_stats = await network.get_instructor_stats()
        assert isinstance(inst_stats, dict)
        logger.info("✓ Instructor stats retrieved: keys=%s", list(inst_stats.keys())[:5])

        users = await network.get_users()
        assert isinstance(users, list)
        logger.info("✓ Users retrieved: %d users", len(users))

        online = await network.get_online_users()
        logger.info("✓ Online users count: %s", online)

        hof = await network.get_hall_of_fame()
        assert isinstance(hof, list)
        logger.info("✓ Hall of Fame retrieved: %d items", len(hof))

        # 7. Preferences
        prefs = await network.get_preferences()
        logger.info("✓ User preferences retrieved: %s", prefs)

        # 8. Search
        search_feed = await network.search("test", limit=3)
        assert hasattr(search_feed, "feed")
        logger.info("✓ Search returned %d items", len(search_feed.feed))

        # 9. Clean session logout
        await session.logout()
        assert session.state == SessionState.CLOSED
        logger.info("✓ Instructor logout OK")


@live
@requires_student_creds
@pytest.mark.asyncio
async def test_student_live_all_queries():
    """Student workflow verifying student profile, feed, preferences, and search."""
    config = PiazzaConfig(course_id=STUDENT_COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=STUDENT_EMAIL, password=STUDENT_PASSWORD)
        assert session.state == SessionState.AUTHENTICATED
        logger.info("✓ Student login OK")

        piazza = Piazza(session)
        rpc = RPC(session=session, base_url=config.base_url, network_id=STUDENT_COURSE_ID)
        network = Network(rpc, STUDENT_COURSE_ID)

        # Profile & Classes
        profile = await piazza.get_user_profile()
        assert isinstance(profile, dict)
        classes = await piazza.get_user_classes()
        assert isinstance(classes, list)
        logger.info("✓ Student classes: %d classes", len(classes))

        # Feed & Search
        feed = await network.get_feed(limit=3)
        assert feed.feed, "Student feed should have items"
        logger.info("✓ Student feed: %d items", len(feed.feed))

        first_item = feed.feed[0]
        post = await network.get_post(first_item.id)
        assert post.id == first_item.id

        search_res = await network.search("test", limit=2)
        assert hasattr(search_res, "feed")
        logger.info("✓ Student search returned %d items", len(search_res.feed))

        prefs = await network.get_preferences()
        logger.info("✓ Student preferences: %s", prefs)

        await session.logout()
        assert session.state == SessionState.CLOSED
        logger.info("✓ Student logout OK")


@live
@requires_instructor_creds
@requires_student_creds
@pytest.mark.asyncio
async def test_dual_role_complete_lifecycle():  # noqa: PLR0915
    """Comprehensive cross-role post lifecycle test:

    1. Student creates question post
    2. Student auto-saves draft & adds follow-up
    3. Student posts student answer
    4. Student bookmarks & favorites post
    5. Student marks post as viewed
    6. Instructor answers post (instructor answer)
    7. Instructor endorses post and removes endorsement
    8. Instructor pins and unpins post
    9. Instructor resolves post (with full metadata update)
    10. Instructor locks post
    11. Instructor unlocks, then unresolves post (verifies unresolve_post feature)
    12. Instructor re-resolves and locks post
    13. Instructor adds tag
    14. Instructor cancels draft edit
    15. Instructor checks updated post state (including is_upvoted property)
    16. Instructor deletes post to ensure clean network
    """
    post_id: str | None = None
    followup_id: str | None = None

    # Step 1-5: Student Operations
    student_config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(student_config) as student_session:
        await student_session.login(email=STUDENT_EMAIL, password=STUDENT_PASSWORD)
        student_rpc = RPC(
            session=student_session, base_url=student_config.base_url, network_id=COURSE_ID
        )
        student_network = Network(student_rpc, COURSE_ID)

        # 1. Create Question Post
        create_res = await student_network.create_post(
            post_type="question",
            folders=["other"],
            title="Comprehensive Live Test Thread",
            content="Testing all Piazza SDK features from data dictionary.",
            bypass_email=True,
            silent_update=True,
        )
        post_id = create_res.id
        assert post_id, "Post creation must return a valid ID"
        logger.info("✓ [Student] Created post: %s", post_id)

        # 2. Auto-save draft (supported types: followup, s_answer, i_answer)
        await student_network.auto_save_draft(
            post_id=post_id, type="followup", body="Draft content auto-saved"
        )
        logger.info("✓ [Student] Auto-save draft OK")

        # 3. Create Followup
        followup = await student_network.create_followup(
            post=post_id, content="Can someone clarify the details?"
        )
        followup_id = followup.id
        assert followup_id, "Followup must return an ID"
        logger.info("✓ [Student] Created followup: %s", followup_id)

        # 4. Student Answer
        await student_network.answer_post(
            post_id=post_id,
            content="Here is a preliminary student thought.",
            instructor_answer=False,
        )
        logger.info("✓ [Student] Posted student answer OK")

        # 5. Bookmark, Favorite & View
        await student_network.bookmark_post(post_id)
        await student_network.unbookmark_post(post_id)
        await student_network.favorite_post(post_id)
        await student_network.unfavorite_post(post_id)
        await student_network.view_post(post_id)
        logger.info("✓ [Student] Bookmark/Unbookmark, Favorite/Unfavorite & View OK")

    # Step 6-14: Instructor Operations
    instructor_config = SessionConfig(course_id=COURSE_ID)
    async with SessionStateManager(instructor_config) as instructor_session:
        await instructor_session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        instructor_rpc = RPC(
            session=instructor_session, base_url=instructor_config.base_url, network_id=COURSE_ID
        )
        instructor_network = Network(instructor_rpc, COURSE_ID)

        try:
            # 6. Instructor Answer
            await instructor_network.answer_post(
                post_id=post_id,
                content="Official instructor answer with full details.",
                instructor_answer=True,
            )
            logger.info("✓ [Instructor] Posted instructor answer OK")

            # 7. Endorse & Remove Endorsement
            await instructor_network.endorse_post(post_id=post_id)
            await instructor_network.remove_endorsement(post_id=post_id)
            logger.info("✓ [Instructor] Endorse & Remove Endorsement OK")

            # 8. Pin & Unpin
            await instructor_network.pin_post(post_id)
            await instructor_network.unpin_post(post_id)
            logger.info("✓ [Instructor] Pin & Unpin post OK")

            # 9. Resolve Post
            resolved = await instructor_network.resolve_post(post_id)
            assert resolved
            logger.info("✓ [Instructor] Resolve post OK")

            # 10. Unresolve Post (verifies new unresolve_post feature — before lock)
            unresolved = await instructor_network.unresolve_post(post_id)
            assert unresolved
            logger.info("✓ [Instructor] Unresolve post OK (verifies unresolve_post feature)")

            # 11. Re-resolve and Lock Post
            await instructor_network.resolve_post(post_id)
            await instructor_network.lock_post(post_id)
            logger.info("✓ [Instructor] Re-resolve and lock OK")

            # 12. Add Tag
            await instructor_network.add_tag(post_id, "test_tag")
            logger.info("✓ [Instructor] Add Tag OK")

            # 13. Cancel Edit
            await instructor_network.cancel_edit()
            logger.info("✓ [Instructor] Cancel Edit OK")

            # 14. Verify updated post state (including is_upvoted property)
            updated_post = await instructor_network.get_post(post_id)
            assert updated_post.id == post_id
            assert len(updated_post.children) >= 2
            answers = [c for c in updated_post.children if c.type in ("i_answer", "s_answer")]
            assert len(answers) >= 1
            assert isinstance(updated_post.is_upvoted, bool)
            logger.info(
                "✓ [Instructor] Post verified: %d children, %d answers, is_upvoted=%s",
                len(updated_post.children),
                len(answers),
                updated_post.is_upvoted,
            )

        finally:
            # 16. Clean up post
            if post_id:
                await instructor_network.delete_post(post_id)
                logger.info("✓ [Instructor] Cleaned up test post %s via delete_post", post_id)


@live
@requires_instructor_creds
@pytest.mark.asyncio
async def test_cookie_persistence_and_encryption_live():
    """Live test verifying cookie persistence with Fernet encryption and session restoration."""
    key = Fernet.generate_key().decode()
    with tempfile.TemporaryDirectory() as tmpdir:
        cookie_file = Path(tmpdir) / "piazza_live_cookies.json"

        # Phase 1: Login and save encrypted cookies
        config1 = PiazzaConfig(course_id=COURSE_ID, cookie_path=cookie_file, encryption_key=key)
        async with SessionStateManager(config1) as session1:
            await session1.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
            assert session1.state == SessionState.AUTHENTICATED
            await session1.cookies.save(cookie_file)
            assert cookie_file.exists()
            logger.info("✓ Encrypted cookies saved to disk (%d bytes)", cookie_file.stat().st_size)

        # Phase 2: Create brand new session, restore cookies, and test live API
        config2 = PiazzaConfig(course_id=COURSE_ID, cookie_path=cookie_file, encryption_key=key)
        async with SessionStateManager(config2) as session2:
            restored = await session2.restore_cookies()
            assert restored, "Cookies should be successfully restored"
            assert session2.state == SessionState.AUTHENTICATED
            alive = await session2.is_session_alive()
            assert alive, "Restored session should be live and valid"
            logger.info("✓ Restored encrypted session successfully authenticated on live API")


@live
@pytest.mark.asyncio
async def test_live_throttle_activates():
    """Live test: throttle delays requests when enabled."""
    config = PiazzaConfig(
        course_id=COURSE_ID, throttle_enabled=True, throttle_min_delay=1.0, throttle_max_delay=1.5
    )
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        network = Network(
            RPC(session=session, base_url=config.base_url, network_id=COURSE_ID), COURSE_ID
        )

        start = time.monotonic()
        await network.get_feed(limit=1)
        await network.get_feed(limit=1)
        elapsed = time.monotonic() - start
        assert elapsed >= 1.0, (
            f"Throttle did not delay requests sufficiently (elapsed {elapsed:.2f}s < 1.0s)"
        )
        logger.info("✓ Throttle correctly delayed requests (elapsed: %.2fs)", elapsed)


@live
@pytest.mark.asyncio
async def test_live_throttle_idle_reset():
    """Live test: idle timeout resets throttle so next request is fast."""
    config = PiazzaConfig(
        course_id=COURSE_ID, throttle_enabled=True, throttle_min_delay=1.0, throttle_max_delay=1.5
    )
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        network = Network(
            RPC(session=session, base_url=config.base_url, network_id=COURSE_ID), COURSE_ID
        )

        # Prime the throttle with a request
        await network.get_feed(limit=1)
        # Sleep longer than max_delay to trigger idle reset
        await asyncio.sleep(1.6)
        start = time.monotonic()
        await network.get_feed(limit=1)
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, (
            f"Idle reset failed, request was throttled (elapsed {elapsed:.2f}s >= 1.0s)"
        )
        logger.info("✓ Throttle idle reset skipped delay correctly (elapsed: %.2fs)", elapsed)


@live
@pytest.mark.asyncio
async def test_live_throttle_multiple_rapid_requests():
    """Live test:3 rapid throttled requests are properly paced."""
    config = PiazzaConfig(
        course_id=COURSE_ID, throttle_enabled=True, throttle_min_delay=1.0, throttle_max_delay=1.5
    )
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        network = Network(
            RPC(session=session, base_url=config.base_url, network_id=COURSE_ID), COURSE_ID
        )

        # 3 rapid calls should take at least min_delay * (N-1) = 2.0s
        start = time.monotonic()
        for _ in range(3):
            await network.search("test")
        elapsed = time.monotonic() - start
        assert elapsed >= 2.0, (
            f"Multiple rapid throttled requests failed delay check (elapsed {elapsed:.2f}s)"
        )
        logger.info("✓ 3 rapid throttled requests correctly paced (elapsed: %.2fs)", elapsed)


@live
@pytest.mark.asyncio
async def test_live_not_found_detection():
    """Live test: embedded error detection raises NotFoundError for non-existent post."""
    config = PiazzaConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        network = Network(
            RPC(session=session, base_url=config.base_url, network_id=COURSE_ID), COURSE_ID
        )

        with pytest.raises(NotFoundError):
            await network.get_post("9999999999")
        logger.info("✓ Not found detection properly raised NotFoundError on live API")


@live
@requires_instructor_creds
@pytest.mark.asyncio
async def test_live_no_throttle_performance():
    """Live test verifying performance without throttle is fast."""

    config = PiazzaConfig(course_id=COURSE_ID, throttle_min_delay=0.0, throttle_max_delay=0.0)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        network = Network(
            RPC(session=session, base_url=config.base_url, network_id=COURSE_ID), COURSE_ID
        )

        start = time.monotonic()
        for i in range(3):
            await network.get_feed(limit=1)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0, f"Unthrottled requests too slow (elapsed {elapsed:.2f}s >= 2.0s)"
        logger.info("✓ Unthrottled 3 rapid requests were fast (elapsed: %.2fs)", elapsed)


# ── Phase 1 LIVE verification: global email preferences ────────────────


@live
@requires_instructor_creds
@pytest.mark.asyncio
async def test_live_email_preferences_roundtrip():
    """Live verify: user.status email_prefs read + user.update flip/revert.

    Flips one course to ``no-emails``, asserts the change is visible on a
    fresh read, then reverts to the original value and asserts the revert.
    Skips the flip when the original ``new`` value is unknown so cleanup
    stays exact.
    """
    config = PiazzaConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        piazza = Piazza(session)

        prefs = await piazza.get_email_preferences()
        assert isinstance(prefs, dict), "email_prefs should be a mapping"
        assert prefs, "email_prefs should be present"
        logger.info("✓ email_prefs keys: %s", sorted(prefs))

        # Typed entries parse cleanly; career key tolerated if present.
        for key, entry in prefs.items():
            assert isinstance(entry, EmailPrefEntry), f"entry {key} not typed"

        course_keys = [k for k in prefs if k != "career"]
        nid = COURSE_ID if COURSE_ID in prefs else course_keys[0]
        original_new = prefs[nid].new
        logger.info("✓ target=%s original new=%r", nid, original_new)

        # No-op RMW write must succeed and preserve the value.
        updated = await piazza.set_email_notification(nid, new=original_new or "instantly")
        assert updated["new"] == (original_new or "instantly")

        if original_new is None:
            logger.info("! original 'new' missing; skipped destructive flip")
            return

        # Real flip -> visible on fresh read.
        await piazza.set_email_notification(nid, new="no-emails")
        after = await piazza.get_email_preferences()
        assert after[nid].new == "no-emails", "flip not visible on read-back"
        logger.info("✓ flip to no-emails verified on live read-back")

        # Revert -> visible on fresh read.
        await piazza.set_email_notification(nid, new=original_new)
        restored = await piazza.get_email_preferences()
        assert restored[nid].new == original_new, "revert not visible on read-back"
        logger.info("✓ revert to %r verified — state restored", original_new)


# ── LIVE verification: network info & role permissions ─────────


@live
@requires_instructor_creds
@pytest.mark.asyncio
async def test_live_network_info_roles_matrix():
    """Live verify: user.status networks[] parse, config.roles, resources_url.

    Asserts the instructor's course carries a roles matrix with
    instructor-level posting rights, and that the derived Resources URL
    responds with HTTP 200.
    """

    config = PiazzaConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        rpc = RPC(session=session, base_url=config.base_url, network_id=COURSE_ID)
        network = Network(rpc, COURSE_ID)

        info = await network.info()
        assert info.nid == COURSE_ID
        logger.info(
            "✓ info parsed: name=%r term=%r school_ext=%r short_number=%s",
            info.name,
            info.term,
            info.school_ext,
            info.short_number,
        )

        # Role matrix presence is data-dependent; log rather than hard-fail.
        if info.config is not None and info.config.roles is not None:
            roles_present = [
                r for r in ("admin", "instructor", "ta") if getattr(info.config.roles, r)
            ]
            logger.info("✓ roles present: %s", roles_present or "none")
            if "instructor" in roles_present:
                assert info.can(UserRole.INSTRUCTOR, "new_post") is True
                logger.info("✓ can(instructor, new_post) == True")
        else:
            logger.info("! config.roles absent for this course (schema drift?)")

        url = info.resources_url
        assert url.startswith("https://piazza.com/"), f"bad resources_url: {url}"
        resp = await session.client.get(url)
        assert resp.status_code == 200, f"resources_url returned {resp.status_code}: {url}"
        logger.info("✓ resources_url live 200: %s", url)


# ── Phase 3 LIVE verification: iter_content + extract_urls ─────────────


@live
@requires_instructor_creds
@pytest.mark.asyncio
async def test_live_post_iter_content():
    """Live verify: Post.iter_content walks a real post tree; extract_urls scans."""
    config = PiazzaConfig(course_id=COURSE_ID)
    async with SessionStateManager(config) as session:
        await session.login(email=INSTRUCTOR_EMAIL, password=INSTRUCTOR_PASSWORD)
        network = Network(
            RPC(session=session, base_url=config.base_url, network_id=COURSE_ID), COURSE_ID
        )

        feed = await network.get_feed(limit=5)
        assert feed.feed
        post = await network.get_post(feed.feed[0].id)

        bodies = list(post.iter_content())
        assert bodies, "iter_content should yield at least one revision body"
        logger.info(
            "✓ iter_content yielded %d bodies from post %s (children=%d)",
            len(bodies),
            post.id,
            len(post.children),
        )
        assert any(b.strip() for b in bodies), "at least one body should be non-blank"

        urls = extract_urls("\n".join(bodies))
        logger.info("✓ extract_urls found %d links: %s", len(urls), urls[:5])
