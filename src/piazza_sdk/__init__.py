"""Piazza SDK - async Python client for Piazza's internal API.

Usage:
    from piazza_sdk import SessionStateManager, SessionConfig, Piazza

    config = SessionConfig(course_id="your_course_id")
    async with SessionStateManager(config) as session:
        await session.login(email="user@example.com", password="pass")
        piazza = Piazza(session)
        classes = await piazza.get_user_classes()
"""

from piazza_sdk._version import __version__, version
from piazza_sdk.api.network import Network
from piazza_sdk.api.piazza import Piazza
from piazza_sdk.api.rpc import RPC
from piazza_sdk.auth import CookieJar, SessionConfig, SessionState, SessionStateManager
from piazza_sdk.exceptions import (
    AuthenticationError,
    ContentError,
    FeedError,
    NetworkError,
    NotFoundError,
    PermissionError,
    PiazzaSDKError,
    RateLimitError,
    SearchError,
    StatisticsError,
    UploadError,
    UserError,
    ValidationError,
)
from piazza_sdk.models.enums import (
    AnonymityLevel,
    ChangeType,
    FeedItemDefaultAnonymity,
    FeedItemType,
    FeedSortOrder,
    FolderType,
    NotificationType,
    PostStatus,
    PostType,
    ResponseFormat,
    SortField,
    UserRole,
    Visibility,
)
from piazza_sdk.models.feed import (
    Feed,
    FeedFilter,
    FeedItem,
    FolderFilter,
    FollowingFilter,
    SearchBuilder,
    SearchFilter,
    SortFilter,
    UnreadFilter,
)
from piazza_sdk.models.network import HallOfFameItem, NetworkInfo, Statistics
from piazza_sdk.models.post import (
    ChangeLogEntry,
    Endorsement,
    Post,
    PostRevision,
    PublishingOptions,
)
from piazza_sdk.models.user import User, UserPreferences

PiazzaSession = SessionStateManager

__all__ = [
    # Core
    "SessionConfig",
    "SessionState",
    "SessionStateManager",
    "PiazzaSession",
    "CookieJar",
    "Piazza",
    "Network",
    "RPC",
    # Exceptions
    "AuthenticationError",
    "ContentError",
    "FeedError",
    "NetworkError",
    "NotFoundError",
    "PermissionError",
    "PiazzaSDKError",
    "RateLimitError",
    "SearchError",
    "StatisticsError",
    "UploadError",
    "UserError",
    "ValidationError",
    # Enums
    "AnonymityLevel",
    "ChangeType",
    "FeedItemDefaultAnonymity",
    "FeedItemType",
    "FeedSortOrder",
    "FolderType",
    "NotificationType",
    "PostStatus",
    "PostType",
    "ResponseFormat",
    "SortField",
    "UserRole",
    "Visibility",
    # Models
    "ChangeLogEntry",
    "Endorsement",
    "Feed",
    "FeedFilter",
    "FeedItem",
    "FolderFilter",
    "FollowingFilter",
    "HallOfFameItem",
    "NetworkInfo",
    "Post",
    "PostRevision",
    "PublishingOptions",
    "SearchBuilder",
    "SearchFilter",
    "SortFilter",
    "Statistics",
    "UnreadFilter",
    "User",
    "UserPreferences",
    # Version
    "__version__",
    "version",
]
