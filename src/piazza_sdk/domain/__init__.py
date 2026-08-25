"""Domain modules for Piazza SDK business logic.

Contains domain-specific functions extracted from the Network class.
Each module provides standalone async functions that operate on
RPC and session objects, enabling hexagonal architecture.
"""

from __future__ import annotations

from piazza_sdk.domain.feed import get_feed, get_similar_posts
from piazza_sdk.domain.posts import (
    add_followup,
    add_tag,
    answer_post,
    create_folder,
    create_post,
    delete_post,
    endorse,
    mark_as_unread,
    remove_tag,
    resolve_post,
    save_draft,
    unresolve_post,
    upload_asset,
)
from piazza_sdk.domain.preferences import get_preferences, update_preferences
from piazza_sdk.domain.search import search
from piazza_sdk.domain.statistics import get_statistics
from piazza_sdk.domain.users import get_all_users, get_instructor_stats, get_online_users

__all__ = [
    "add_followup",
    "add_tag",
    "answer_post",
    "create_folder",
    "create_post",
    "delete_post",
    "endorse",
    "get_all_users",
    "get_feed",
    "get_instructor_stats",
    "get_online_users",
    "get_preferences",
    "get_similar_posts",
    "get_statistics",
    "mark_as_unread",
    "remove_tag",
    "resolve_post",
    "save_draft",
    "search",
    "unresolve_post",
    "update_preferences",
    "upload_asset",
]
