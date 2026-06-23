"""Tests for piazza_sdk.utils.classification."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from piazza_sdk.models.enums import FeedItemType
from piazza_sdk.models.feed import FeedItem
from piazza_sdk.utils.classification import ActivityClassifier


def _dt_passthrough(*args: object, **kwargs: object) -> datetime:  # noqa: DTZ001
    """Forward datetime() calls through a mock — needed so the real
    constructor runs while ``datetime`` is patched."""
    return datetime(*args, **kwargs)  # noqa: DTZ001


def _make_feed_item(
    *,
    created: datetime | None = None,
    updated: datetime | None = None,
    no_answer: bool = False,
    reputation: int = 0,
    **kwargs,
) -> FeedItem:
    defaults = {
        "id": "post_1",
        "subject": "Test",
        "type": FeedItemType.QUESTION,
        "uid": "user_1",
        "tags": [],
    }
    defaults.update(kwargs)
    return FeedItem(
        created=created,
        updated=updated,
        no_answer=no_answer,
        reputation=reputation,
        **defaults,
    )


class TestClassify:
    """Tests for ActivityClassifier.classify."""

    def test_classify_both_none(self) -> None:
        item = _make_feed_item(created=None, updated=None)
        assert ActivityClassifier.classify(item) == "inactive"

    def test_classify_active_recent_update(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(hours=6)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"

    def test_classify_active_just_under_threshold(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(seconds=ActivityClassifier.ACTIVE_THRESHOLD - 1)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"

    def test_classify_inactive_at_active_threshold(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(seconds=ActivityClassifier.ACTIVE_THRESHOLD)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "inactive"

    def test_classify_inactive_between_thresholds(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(days=3)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "inactive"

    def test_classify_stale_at_inactive_threshold(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(seconds=ActivityClassifier.INACTIVE_THRESHOLD)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "stale"

    def test_classify_stale_between_inactive_and_stale(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(days=15)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "stale"

    def test_classify_stale_at_stale_threshold(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(seconds=ActivityClassifier.STALE_THRESHOLD)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "stale"

    def test_classify_stale_far_past(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(days=365)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "stale"

    def test_classify_uses_updated_over_created(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        created = now - timedelta(days=60)
        updated = now - timedelta(hours=2)
        item = _make_feed_item(created=created, updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"

    def test_classify_falls_back_to_created_when_updated_none(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        created = now - timedelta(hours=4)
        item = _make_feed_item(created=created, updated=None)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"

    def test_classify_naive_timestamp_treated_as_utc(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = datetime(2025, 6, 15, 6, 0)  # noqa: DTZ001 — intentionally naive
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"

    def test_classify_active_with_only_created(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        created = now - timedelta(minutes=30)
        item = _make_feed_item(created=created)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"

    def test_classify_inactive_with_only_created_aged(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        created = now - timedelta(days=4)
        item = _make_feed_item(created=created)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "inactive"

    def test_classify_exactly_now(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        item = _make_feed_item(updated=now)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"

    def test_classify_one_second_before_now(self) -> None:
        now = datetime(2025, 6, 15, 12, 0, tzinfo=UTC)
        updated = now - timedelta(seconds=1)
        item = _make_feed_item(updated=updated)
        with patch("piazza_sdk.utils.classification.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.side_effect = _dt_passthrough
            assert ActivityClassifier.classify(item) == "active"


class TestIsNew:
    """Tests for ActivityClassifier.is_new."""

    def test_is_new_no_answer_zero_reputation(self) -> None:
        item = _make_feed_item(no_answer=True, reputation=0)
        assert ActivityClassifier.is_new(item) is True

    def test_is_new_no_answer_positive_reputation(self) -> None:
        item = _make_feed_item(no_answer=True, reputation=5)
        assert ActivityClassifier.is_new(item) is False

    def test_is_new_has_answer_zero_reputation(self) -> None:
        item = _make_feed_item(no_answer=False, reputation=0)
        assert ActivityClassifier.is_new(item) is False

    def test_is_new_has_answer_positive_reputation(self) -> None:
        item = _make_feed_item(no_answer=False, reputation=10)
        assert ActivityClassifier.is_new(item) is False

    def test_is_new_negative_reputation(self) -> None:
        item = _make_feed_item(no_answer=True, reputation=-1)
        assert ActivityClassifier.is_new(item) is False

    def test_is_new_high_reputation(self) -> None:
        item = _make_feed_item(no_answer=True, reputation=999)
        assert ActivityClassifier.is_new(item) is False

    def test_is_new_defaults(self) -> None:
        item = _make_feed_item()
        assert ActivityClassifier.is_new(item) is False


class TestIsUnanswered:
    """Tests for ActivityClassifier.is_unanswered."""

    def test_is_unanswered_no_answer_true(self) -> None:
        item = _make_feed_item(no_answer=True)
        assert ActivityClassifier.is_unanswered(item) is True

    def test_is_unanswered_no_answer_false(self) -> None:
        item = _make_feed_item(no_answer=False)
        assert ActivityClassifier.is_unanswered(item) is False

    def test_is_unanswered_defaults(self) -> None:
        item = _make_feed_item()
        assert ActivityClassifier.is_unanswered(item) is False
