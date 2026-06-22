"""Activity classifier for Piazza SDK.

Classifies feed items and posts by activity status.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from piazza_sdk.models.feed import FeedItem


class ActivityClassifier:
    """Classifies feed items by activity status.

    Categorizes items as new, active, inactive, or stale based on
    various signals (views, responses, timestamps, etc.).
    """

    # Thresholds (in seconds)
    ACTIVE_THRESHOLD = 3600 * 24  # 1 day
    INACTIVE_THRESHOLD = 3600 * 24 * 7  # 7 days
    STALE_THRESHOLD = 3600 * 24 * 30  # 30 days

    @staticmethod
    def classify(feed_item: FeedItem) -> str:
        """Classify a feed item's activity level.

        Returns:
            One of: 'new', 'active', 'inactive', 'stale'
        """
        if not feed_item.updated and not feed_item.created:
            return "inactive"

        now = datetime.now(UTC)
        ts = feed_item.updated or feed_item.created

        if ts is None:
            return "inactive"

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        age = (now - ts).total_seconds()

        if age < ActivityClassifier.ACTIVE_THRESHOLD:
            return "active"
        if age < ActivityClassifier.INACTIVE_THRESHOLD:
            return "inactive"
        if age < ActivityClassifier.STALE_THRESHOLD:
            return "stale"
        return "stale"

    @staticmethod
    def is_new(feed_item: FeedItem) -> bool:
        """Check if item is newly created (no activity yet)."""
        return feed_item.no_answer and feed_item.reputation == 0

    @staticmethod
    def is_unanswered(feed_item: FeedItem) -> bool:
        """Check if item has no answer."""
        return feed_item.no_answer
