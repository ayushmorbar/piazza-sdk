"""Unit tests for Piazza SDK models, filters, enums, and builders."""

from __future__ import annotations

from datetime import UTC, datetime

from piazza_sdk.models.enums import (
    AnonymityLevel,
    ChangeType,
    FeedItemDefaultAnonymity,
    FeedItemType,
    FeedSortOrder,
    PostType,
    UserRole,
    Visibility,
)
from piazza_sdk.models.feed import (
    Feed,
    FeedItem,
    FolderFilter,
    SearchBuilder,
    SearchFilter,
    UnreadFilter,
)
from piazza_sdk.models.network import HallOfFameItem, NetworkInfo
from piazza_sdk.models.post import (
    ChangeLogEntry,
    Post,
    PostCreatedResponse,
    PostRevision,
    PublishingOptions,
)
from piazza_sdk.models.user import User, UserPreferences

# ==============================================================================
# Enums Tests
# ==============================================================================


class TestEnums:
    """Test enumeration values and representations."""

    def test_post_type(self):
        assert PostType.NOTE.value == "note"
        assert PostType.QUESTION.value == "question"
        assert PostType.POLL.value == "poll"

    def test_change_type(self):
        assert ChangeType.CREATE.value == "create"
        assert ChangeType.FOLLOWUP.value == "followup"
        assert ChangeType.FEEDBACK.value == "feedback"
        assert ChangeType.INSTRUCTOR_ANSWER.value == "i_answer"
        assert ChangeType.STUDENT_ANSWER.value == "s_answer"

    def test_visibility(self):
        assert Visibility.PUBLIC.value == "public"
        assert Visibility.PRIVATE.value == "private"
        assert Visibility.GROUP.value == "group"
        assert Visibility.INSTRUCTORS_ONLY.value == "instructors_only"

    def test_anonymity_level(self):
        assert AnonymityLevel.FULL.value == "full"
        assert AnonymityLevel.STUD.value == "stud"
        assert AnonymityLevel.NO.value == "no"

    def test_user_role(self):
        assert UserRole.STUDENT.value == "student"
        assert UserRole.PROFESSOR.value == "professor"
        assert UserRole.TA.value == "ta"
        assert UserRole.INSTRUCTOR.value == "instructor"

    def test_feed_sort_order(self):
        assert FeedSortOrder.UPDATED.value == "updated"
        assert FeedSortOrder.CREATED.value == "created"

    def test_feed_item_type(self):
        assert FeedItemType.QUESTION.value == "question"
        assert FeedItemType.NOTE.value == "note"
        assert FeedItemType.POLL.value == "poll"

    def test_feed_item_default_anonymity(self):
        assert FeedItemDefaultAnonymity.NO.value == "no"
        assert FeedItemDefaultAnonymity.STUD.value == "stud"


# ==============================================================================
# Post & Interaction Models
# ==============================================================================


class TestPostModel:
    """Test Post and related sub-models."""

    def test_post_creation_minimal(self):
        post = Post(id="p1", title="Title", raw={})
        assert post.id == "p1"
        assert post.title == "Title"
        assert post.views == 0
        assert post.unique_views is None

    def test_post_answer_properties(self):
        """post.student_answer and post.instructor_answer filter children correctly."""
        post = Post(
            id="p1",
            title="Title",
            raw={},
            children=[
                {
                    "id": "c1",
                    "type": "s_answer",
                    "subject": "student answer",
                    "created": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "c2",
                    "type": "i_answer",
                    "subject": "instructor answer",
                    "created": "2025-01-01T00:00:00Z",
                },
                {
                    "id": "c3",
                    "type": "followup",
                    "subject": "followup text",
                    "created": "2025-01-01T00:00:00Z",
                },
            ],
        )
        assert post.student_answer is not None
        assert post.student_answer.subject == "student answer"
        assert post.instructor_answer is not None
        assert post.instructor_answer.subject == "instructor answer"

    def test_post_no_answers_returns_none(self):
        post = Post(
            id="p1",
            title="Title",
            raw={},
            children=[{"id": "c1", "type": "followup", "subject": "f"}],
        )
        assert post.student_answer is None
        assert post.instructor_answer is None

    def test_post_unique_views(self):
        post = Post(id="p1", title="Title", raw={}, unique_views=42)
        assert post.unique_views == 42

    def test_post_extra_fields_ignored(self):
        """Server-fed extra keys are tolerated and ignored without error."""
        post = Post(id="p1", title="Title", raw={}, unknown_server_key="extra_data")
        assert post.id == "p1"

    def test_post_revision_model(self):
        rev = PostRevision(
            subject="Rev Subject",
            content="Rev Content",
            uid="user_1",
            created=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert rev.subject == "Rev Subject"
        assert rev.content == "Rev Content"

    def test_post_created_response(self):
        resp = PostCreatedResponse(id="new_post_id")
        assert resp.id == "new_post_id"

    def test_publishing_options(self):
        opts = PublishingOptions(
            bypass_email=True, silent_update=True, anonymity=AnonymityLevel.STUD
        )
        assert opts.bypass_email is True
        assert opts.silent_update is True
        assert opts.anonymity == AnonymityLevel.STUD

    def test_wire_key_change_log_via_alias(self):
        """Post.change_log is aliased as ``log`` — wire data uses ``log``."""
        post = Post(id="p1", title="T", raw={}, log=[{"id": "cl1"}])
        assert len(post.change_log) == 1
        assert post.change_log[0].id == "cl1"

    def test_wire_key_endorsements_direct(self):
        """Post.endorsements maps directly from ``tag_good`` via network layer."""
        post = Post(id="p1", title="T", raw={}, endorsements=[{"role": "student", "tag": "good"}])
        assert len(post.endorsements) == 1
        assert post.endorsements[0].tag == "good"

    def test_wire_key_revisions_direct(self):
        """Post.revisions maps from ``history`` via network layer."""
        post = Post(id="p1", title="T", raw={}, revisions=[{"subject": "Q1", "content": "body1"}])
        assert len(post.revisions) == 1
        assert post.revisions[0].subject == "Q1"

    def test_revision_auto_numbering(self):
        """PostRevision.revision auto-increments from list index when all are 0."""
        post = Post(
            id="p1",
            title="T",
            raw={},
            revisions=[
                {"subject": "v1", "content": "c1"},
                {"subject": "v2", "content": "c2"},
                {"subject": "v3", "content": "c3"},
            ],
        )
        assert post.revisions[0].revision == 1
        assert post.revisions[1].revision == 2
        assert post.revisions[2].revision == 3

    def test_revision_auto_numbering_skipped_when_explicit(self):
        """Auto-numbering is skipped if any revision already has an explicit number."""
        post = Post(
            id="p1",
            title="T",
            raw={},
            revisions=[
                {"subject": "v1", "content": "c1", "revision": 5},
                {"subject": "v2", "content": "c2"},
            ],
        )
        assert post.revisions[0].revision == 5
        assert post.revisions[1].revision == 0

    def test_change_log_entry_wire_aliases(self):
        """ChangeLogEntry accepts wire keys ``n`` (type) and ``t`` (when)."""
        entry = ChangeLogEntry(n="update", t="2025-08-20T12:00:00Z", id="cl_1")
        assert entry.type == ChangeType.UPDATE
        assert entry.when == "2025-08-20T12:00:00Z"

    def test_change_type_includes_update(self):
        """ChangeType enum includes UPDATE value for wire data ``\"update\"``."""
        assert ChangeType.UPDATE.value == "update"

    def test_full_wire_format_post_construction(self):
        """End-to-end: construct Post from full HAR-like wire payload.

        ``tag_good`` → ``endorsements`` and ``history`` → ``revisions``
        are mapped by network.py.  ``log`` is an alias on the Post model.
        ``change_log`` is the Python attribute name; ``log`` is the alias.
        """
        wire = {
            "id": "l2345abc",
            "nr": 42,
            "type": "question",
            "subject": "How does X work?",
            "uid": "u_student1",
            "status": "active",
            "log": [
                {"id": "cl1", "n": "create", "u": "u_student1"},
                {"id": "cl2", "n": "update", "u": "u_student1"},
            ],
            "endorsements": [{"role": "instructor", "tag": "good", "endorser": {"id": "u_prof1"}}],
            "revisions": [
                {"subject": "How does X work?", "content": "Initial"},
                {"subject": "How does X work? (edited)", "content": "Updated body"},
            ],
            "children": [{"id": "c1", "type": "i_answer", "subject": "Here's how"}],
            "folders": ["hw3"],
            "views": 120,
        }
        post = Post(**wire)
        assert post.id == "l2345abc"
        assert post.nr == 42
        assert len(post.change_log) == 2
        assert post.change_log[0].type == ChangeType.CREATE
        assert post.change_log[1].type == ChangeType.UPDATE
        assert len(post.endorsements) == 1
        assert post.endorsements[0].tag == "good"
        assert len(post.revisions) == 2
        assert post.revisions[0].revision == 1
        assert post.revisions[1].revision == 2
        assert len(post.children) == 1
        assert post.folders == ["hw3"]
        assert post.views == 120

    def test_network_layer_wire_key_mapping(self):
        """Simulate network.py's Post construction with HAR wire keys."""
        # Simulate what network.py line 240-245 does:
        raw = {
            "id": "net_post_1",
            "change_log": [{"id": "cl1", "n": "create", "u": "u1"}],
            "tag_good": [{"role": "student", "tag": "good"}],
            "history": [{"subject": "Q", "content": "body"}],
        }
        post = Post(
            id=raw.get("id", ""),
            log=raw.get("change_log", []),
            endorsements=raw.get("tag_good", []),
            revisions=raw.get("history", []),
        )
        assert len(post.change_log) == 1
        assert post.change_log[0].id == "cl1"
        assert len(post.endorsements) == 1
        assert post.endorsements[0].tag == "good"
        assert len(post.revisions) == 1
        assert post.revisions[0].revision == 1


# ==============================================================================
# Feed Models & Search Builder
# ==============================================================================


class TestFeedModels:
    """Test FeedItem, Feed, filters, and SearchBuilder."""

    def test_feed_item_creation(self):
        item = FeedItem(
            id="f1",
            subject="Sub",
            type=FeedItemType.NOTE,
            created=datetime.now(UTC),
            updated=datetime.now(UTC),
            default_anonymity=FeedItemDefaultAnonymity.NO,
            folder="general",
            tag="tag1",
        )
        assert item.id == "f1"
        assert item.folder == "general"
        assert item.tag == "tag1"

    def test_feed_container(self):
        feed = Feed(feed=[])
        assert feed.feed == []
        assert feed.total == 0

    def test_folder_filter(self):
        f = FolderFilter(folder_name="hw1")
        assert f.folder_name == "hw1"
        assert f.to_kwargs() == {"folder": True, "filter_folder": "hw1"}

    def test_unread_filter(self):
        f = UnreadFilter()
        assert f.to_kwargs() == {"updated": True}

    def test_search_builder_fluent_api(self):
        """SearchBuilder allows chaining queries, limits, offsets, and folders."""
        builder = (
            SearchBuilder()
            .with_query("quantum computing")
            .in_folder("Physics")
            .limit(25)
            .offset(10)
        )
        assert builder._query == "quantum computing"
        assert builder._folder == "Physics"
        assert builder._limit == 25
        assert builder._offset == 10

        filter_model = builder.compile()
        assert isinstance(filter_model, SearchFilter)
        assert filter_model.query == "quantum computing"
        assert filter_model.folder == "Physics"
        assert filter_model.limit == 25
        assert filter_model.offset == 10


# ==============================================================================
# Network & User Models
# ==============================================================================


class TestNetworkAndUserModels:
    """Test NetworkInfo, HallOfFameItem, User, UserPreferences."""

    def test_network_info(self):
        info = NetworkInfo(id="net_1", name="CS 101", term="Fall 2025", status="active")
        assert info.id == "net_1"
        assert info.name == "CS 101"

    def test_hall_of_fame_item(self):
        item = HallOfFameItem(
            uid="hof_1",
            votes=15,
            response_time_seconds=300,
            snippet="Great answer snippet",
            timestamp=1700000000,
        )
        assert item.uid == "hof_1"
        assert item.votes == 15
        assert item.snippet == "Great answer snippet"

    def test_user_model(self):
        user = User(id="u_1", name="Bob", email="bob@example.com", role=["student"])
        assert user.id == "u_1"
        assert user.is_student is True

    def test_user_preferences_model(self):
        prefs = UserPreferences(digest_frequency="daily", digest_hour=9, email_new_post=True)
        assert prefs.digest_frequency == "daily"
        assert prefs.digest_hour == 9
        assert prefs.email_new_post is True
