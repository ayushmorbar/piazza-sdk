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
from piazza_sdk.models.post import Post, PostCreatedResponse, PostRevision, PublishingOptions
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
