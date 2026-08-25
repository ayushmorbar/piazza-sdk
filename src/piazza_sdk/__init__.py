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
from piazza_sdk.auth import CookieJar, SessionState, SessionStateManager
from piazza_sdk.config import PiazzaConfig, SessionConfig
from piazza_sdk.exceptions import (
    AuthenticationError,
    ContentError,
    FeedError,
    NetworkError,
    NotAuthenticatedError,
    NotFoundError,
    PermissionError,
    PiazzaSDKError,
    RateLimitError,
    SearchError,
    SessionClosedError,
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
    FeedItemStat,
    FolderFilter,
    FollowingFilter,
    SearchBuilder,
    SearchFilter,
    SortFilter,
    UnreadFilter,
)
from piazza_sdk.models.network import (
    ClassSections,
    HallOfFameItem,
    NetworkConfig,
    NetworkInfo,
    NetworkRoles,
    RolePermissions,
    Statistics,
    StatisticsStudents,
)
from piazza_sdk.models.post import (
    AssetUploadResponse,
    ChangeLogEntry,
    Endorsement,
    Post,
    PostCreatedResponse,
    PostRevision,
    PublishingOptions,
)
from piazza_sdk.models.user import EmailPrefEntry, User, UserPreferences

PiazzaSession = SessionStateManager

__all__ = [
    "PiazzaConfig",
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
    "NotAuthenticatedError",
    "NotFoundError",
    "PermissionError",
    "PiazzaSDKError",
    "RateLimitError",
    "SearchError",
    "SessionClosedError",
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
    "AssetUploadResponse",
    "ChangeLogEntry",
    "ClassSections",
    "EmailPrefEntry",
    "Endorsement",
    "Feed",
    "FeedFilter",
    "FeedItem",
    "FeedItemStat",
    "FolderFilter",
    "FollowingFilter",
    "HallOfFameItem",
    "NetworkConfig",
    "NetworkInfo",
    "NetworkRoles",
    "Post",
    "PostCreatedResponse",
    "PostRevision",
    "PublishingOptions",
    "RolePermissions",
    "SearchBuilder",
    "SearchFilter",
    "SortFilter",
    "Statistics",
    "StatisticsStudents",
    "UnreadFilter",
    "User",
    "UserPreferences",
    # Version
    "__version__",
    "version",
]
