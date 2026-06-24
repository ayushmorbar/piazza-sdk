"""Basic tests for Piazza SDK."""

from datetime import datetime

import pytest

from piazza_sdk import (
    AnonymityLevel,
    AuthenticationError,
    ChangeLogEntry,
    ChangeType,
    ContentError,
    Endorsement,
    FeedError,
    FeedItem,
    FeedSortOrder,
    FolderFilter,
    FollowingFilter,
    NotFoundError,
    PermissionError,
    PiazzaSDKError,
    Post,
    PostStatus,
    PostType,
    RateLimitError,
    SearchError,
    StatisticsError,
    UnreadFilter,
    User,
    UserError,
    UserRole,
    ValidationError,
    Visibility,
)
from piazza_sdk.models.post import Answer, Child, FollowUp


class TestEnums:
    """Test enumeration types."""

    def test_post_type(self):
        """Test PostType enum."""
        assert PostType.NOTE.value == "note"
        assert PostType.QUESTION.value == "question"
        assert PostType.POLL.value == "poll"

    def test_change_type(self):
        """Test ChangeType enum."""
        assert ChangeType.CREATE.value == "create"
        assert ChangeType.FOLLOWUP.value == "followup"
        assert ChangeType.FEEDBACK.value == "feedback"
        assert ChangeType.INSTRUCTOR_ANSWER.value == "i_answer"
        assert ChangeType.STUDENT_ANSWER.value == "s_answer"

    def test_visibility(self):
        """Test Visibility enum."""
        assert Visibility.PUBLIC.value == "public"
        assert Visibility.PRIVATE.value == "private"
        assert Visibility.GROUP.value == "group"
        assert Visibility.INSTRUCTORS_ONLY.value == "instructors_only"

    def test_user_role(self):
        """Test UserRole enum."""
        assert UserRole.STUDENT.value == "student"
        assert UserRole.INSTRUCTOR.value == "instructor"
        assert UserRole.PROFESSOR.value == "professor"
        assert UserRole.TA.value == "ta"
        assert UserRole.ADMIN.value == "admin"

    def test_feed_sort_order(self):
        """Test FeedSortOrder enum."""
        assert FeedSortOrder.UPDATED.value == "updated"
        assert FeedSortOrder.CREATED.value == "created"
        assert FeedSortOrder.ACTIVITY.value == "activity"
        assert FeedSortOrder.UPDATED_ASC.value == "updated_asc"
        assert FeedSortOrder.UPDATED_DESC.value == "updated_desc"
        assert FeedSortOrder.ACTIVITY_ASC.value == "activity_asc"
        assert FeedSortOrder.ACTIVITY_DESC.value == "activity_desc"

    def test_anonymity_level(self):
        """Test AnonymityLevel enum."""
        assert AnonymityLevel.NO.value == "no"
        assert AnonymityLevel.YES.value == "yes"
        assert AnonymityLevel.FULL.value == "full"
        assert AnonymityLevel.STUD.value == "stud"

    def test_post_status(self):
        """Test PostStatus enum."""
        assert PostStatus.ACTIVE.value == "active"
        assert PostStatus.PRIVATE.value == "private"
        assert PostStatus.RESOLVED.value == "resolved"
        assert PostStatus.SUPERSEDED.value == "superseded"


class TestModels:
    """Test data models."""

    def test_user_model(self):
        """Test User model."""
        user_data = {
            "id": "user123",
            "name": "Test User",
            "email": "test@example.com",
            "role": ["student"],
            "is_instructor": False,
            "is_student": True,
            "is_ta": False,
            "is_admin": False,
        }
        user = User(**user_data)
        assert user.id == "user123"
        assert user.name == "Test User"
        assert user.is_student is True

    def test_post_model(self):
        """Test Post model."""
        post_data = {
            "id": "post123",
            "type": "question",
            "title": "Test Post",
            "author": "Test Author",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "nr": 123,
            "raw": {},
        }
        post = Post(**post_data)
        assert post.id == "post123"
        assert post.type == PostType.QUESTION
        assert post.title == "Test Post"

    def test_post_normalized(self):
        """Test Post.normalized() converts HTML content to Markdown."""
        post = Post(
            id="norm1",
            type="question",
            title="<b>Bold Title</b>",
            subject="<p>Subject with <em>emphasis</em></p>",
            author="test@example.com",
            children=[
                Child(
                    id="c1",
                    type="answer",
                    subject="",
                    content="<p>Answer <strong>content</strong></p>",
                    uid="user1",
                )
            ],
            answers=[Answer(id="a1", uid="user1", content="<pre>code block</pre>")],
            followups=[
                FollowUp(
                    id="f1",
                    uid="user1",
                    subject="Followup <em>subject</em>",
                    content="<p>Followup body</p>",
                )
            ],
        )

        normalized = post.normalized()
        # Original unchanged
        assert "<b>" in post.title
        assert "<p>" in post.subject
        # Normalized has Markdown
        assert "**Bold Title**" in normalized.title
        assert "emphasis" in normalized.subject
        assert "<" not in normalized.children[0].content  # HTML stripped
        assert "content" in normalized.children[0].content
        assert "<" not in normalized.answers[0].content  # HTML stripped
        assert "code block" in normalized.answers[0].content
        assert "subject" in normalized.followups[0].subject
        assert "Followup body" in normalized.followups[0].content

    def test_post_normalized_empty_content(self):
        """Test Post.normalized() handles empty content gracefully."""
        post = Post(id="norm2", title="", subject="")
        normalized = post.normalized()
        assert normalized.title == ""
        assert normalized.subject == ""

    def test_feed_item_model(self):
        """Test FeedItem model."""
        feed_item_data = {
            "id": "feed123",
            "subject": "Test Subject",
            "type": "note",
            "created": datetime.now(),
            "updated": datetime.now(),
        }
        feed_item = FeedItem(**feed_item_data)
        assert feed_item.id == "feed123"
        assert feed_item.subject == "Test Subject"
        assert feed_item.type == "note"

    def test_change_log_entry_model(self):
        """Test ChangeLogEntry model."""
        change_data = {
            "id": "ch123",
            "anon": "no",
            "uid": "user123",
            "data": None,
            "to": None,
            "v": "public",
            "type": "create",
            "when": "1609459200000",
            "cid": "cid123",
        }
        change = ChangeLogEntry(**change_data)
        assert change.anon == AnonymityLevel.NO
        assert change.type == ChangeType.CREATE
        assert change.cid == "cid123"

    def test_endorsement_model(self):
        """Test Endorsement model."""
        endorsement_data = {
            "role": "student",
            "name": "Test User",
            "endorser": {"id": "uid123", "name": "Test User", "role": "student"},
            "admin": False,
            "photo": None,
            "id": "endorser123",
            "photo_url": None,
            "published": False,
            "us": False,
            "facebook_id": None,
        }
        endorsement = Endorsement(**endorsement_data)
        assert endorsement.role == "student"
        assert endorsement.name == "Test User"
        assert endorsement.endorser["id"] == "uid123"


class TestFilters:
    """Test feed filters."""

    def test_unread_filter(self):
        """Test UnreadFilter."""
        filter = UnreadFilter()
        kwargs = filter.to_kwargs()
        assert kwargs == {"updated": True}

    def test_following_filter(self):
        """Test FollowingFilter."""
        filter = FollowingFilter()
        kwargs = filter.to_kwargs()
        assert kwargs == {"following": True}

    def test_folder_filter(self):
        """Test FolderFilter."""
        filter = FolderFilter(folder_name="test_folder")
        kwargs = filter.to_kwargs()
        assert kwargs == {"folder": True, "filter_folder": "test_folder"}


class TestExceptions:
    """Test exception hierarchy."""

    def test_piazza_sdk_error(self):
        """Test base exception."""
        error = PiazzaSDKError("Test error")
        assert str(error) == "Test error"

    def test_authentication_error(self):
        """Test authentication error."""
        error = AuthenticationError("Auth failed")
        assert str(error) == "Auth failed"

    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = RateLimitError("Rate limited", retry_after_ms=5000)
        assert str(error) == "Rate limited"
        assert error.retry_after_ms == 5000

    def test_not_found_error(self):
        """Test not found error."""
        error = NotFoundError("Not found")
        assert str(error) == "Not found"

    def test_permission_error(self):
        """Test permission error."""
        error = PermissionError("Permission denied")
        assert str(error) == "Permission denied"

    def test_validation_error(self):
        """Test validation error."""
        error = ValidationError("Invalid data")
        assert str(error) == "Invalid data"

    def test_content_error(self):
        """Test content error."""
        error = ContentError("Content error")
        assert str(error) == "Content error"

    def test_feed_error(self):
        """Test feed error."""
        error = FeedError("Feed error")
        assert str(error) == "Feed error"

    def test_user_error(self):
        """Test user error."""
        error = UserError("User error")
        assert str(error) == "User error"

    def test_search_error(self):
        """Test search error."""
        error = SearchError("Search error")
        assert str(error) == "Search error"

    def test_statistics_error(self):
        """Test statistics error."""
        error = StatisticsError("Statistics error")
        assert str(error) == "Statistics error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
