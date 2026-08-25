"""Post domain operations for Piazza SDK.

Provides standalone functions for post creation, modification, and management.
"""

from __future__ import annotations

__all__ = [
    "add_followup",
    "add_tag",
    "answer_post",
    "auto_save_draft",
    "bookmark_post",
    "cancel_edit",
    "create_folder",
    "create_post",
    "create_reply",
    "delete_post",
    "edit_post",
    "endorse",
    "favorite_post",
    "mark_as_unread",
    "mark_duplicate",
    "pin_post",
    "remove_endorsement",
    "remove_tag",
    "resolve_post",
    "save_draft",
    "schedule_post",
    "unbookmark_post",
    "unfavorite_post",
    "unpin_post",
    "unresolve_post",
    "upload_asset",
    "view_post",
]

import asyncio
import mimetypes
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from piazza_sdk.exceptions import (
    ContentError,
    NotFoundError,
    PiazzaSDKError,
    UploadError,
    ValidationError,
)
from piazza_sdk.models.post import (
    AssetUploadResponse,
    PostCreatedResponse,
    ScheduledPostConfirmation,  # noqa: I001 - grouped import
)

if TYPE_CHECKING:
    from piazza_sdk.api.rpc import RPC
    from piazza_sdk.auth import SessionStateManager
    from piazza_sdk.models.enums import PostType
    from piazza_sdk.models.post import PublishingOptions


async def create_post(  # noqa: PLR0913
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    title: str,
    content: str,
    post_type: PostType | str = "question",
    anonymous: bool = False,
    options: PublishingOptions | None = None,
    folders: list[str] | None = None,
    private_to_staff: bool = False,
    author_uid: str | None = None,
    **kwargs: Any,
) -> PostCreatedResponse:
    """Create a new post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        title: Post title/subject.
        content: Post content (HTML or plain text).
        post_type: Type of post (question, note, poll).
        anonymous: Whether to post anonymously.
        options: Publishing options (bypass email, silent update, anonymity).
        folders: Folder names to file the post under. Defaults to
            ``["General"]``. The folder must already exist in the target
            course - Piazza rejects unknown folders with
            "Please specify folder" (verified live).
        private_to_staff: Make the post visible only to instructors.
            Resolves the author UID from ``user_profile.get_profile``
            (one extra round-trip) and injects
            ``config.feed_groups = "instr_{nid},{uid}"`` (hfaran #77
            contract).
        author_uid: Pre-resolved author user ID; skips the profile
            round-trip when ``private_to_staff`` is set.
        **kwargs: Additional parameters.

    Returns:
        PostCreatedResponse with new post ID.

    Raises:
        ValidationError: If title or content is empty, or the author
            UID cannot be resolved for a staff-private post.

        Example:
            ```python
            # Example for create_post
            res = await create_post()
            ```
    """
    if not title or not title.strip():
        raise ValidationError("title must be non-empty")
    if not content or not content.strip():
        raise ValidationError("content must be non-empty")

    extra_config = kwargs.pop("config", None)
    config: dict[str, Any] = dict(extra_config) if isinstance(extra_config, dict) else {}
    if private_to_staff:
        uid = author_uid
        if uid is None:
            profile = await rpc.get_user_profile()
            candidate = profile.get("user_id") if isinstance(profile, dict) else None
            if not candidate:
                raise ValidationError(
                    "Could not resolve author UID for private post; pass author_uid explicitly"
                )
            uid = str(candidate)
        nid = getattr(rpc, "network_id", "") or ""
        config["feed_groups"] = f"instr_{nid},{uid}"

    extra = dict(kwargs)
    if options is not None:
        extra.update(options.to_kwargs())
    # Piazza's content.create expects ``subject`` (verified live: sending
    # only ``title`` fails with "Missing parameter: subject"), an anonymity
    # *string* ("no"/"stud"/"full") - bool False fails with "Invalid
    # anonymity setting" - and at least one folder ("Please specify
    # folder"). ``title`` is still sent for backward compatibility.
    if folders is None:
        folders = ["General"]
    payload: dict[str, Any] = {
        "subject": title,
        "title": title,
        "content": content,
        "type": post_type,
        "anonymous": "stud" if anonymous else "no",
        "folders": folders,
        **extra,
    }
    if config:
        payload["config"] = config
    raw = await rpc.content_create(**payload)
    result = raw.get("result", raw)
    return PostCreatedResponse.model_validate(result)


async def add_followup(  # noqa: PLR0913
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    post_id: str,
    content: str,
    anonymous: bool = False,
    options: PublishingOptions | None = None,
    instructor: bool = False,
    **kwargs: Any,
) -> PostCreatedResponse:
    """Add a follow-up to an existing post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the parent post.
        content: Followup content.
        anonymous: Whether to post anonymously.
        options: Publishing options.
        instructor: Post as an instructor-only follow-up by injecting
            ``config.ionly = True`` with the rich-text editor marker.
            Caller-supplied ``config`` keys win.
        **kwargs: Additional parameters.

    Returns:
        PostCreatedResponse with new follow-up ID.

    Raises:
        ValidationError: If content is empty.

        Example:
            ```python
            # Example for add_followup
            res = await add_followup()
            ```
    """
    if not content or not content.strip():
        raise ValidationError("content must be non-empty")
    extra = dict(kwargs)
    if instructor:
        caller_config = extra.pop("config", None)
        merged: dict[str, Any] = {"editor": "rte", "ionly": True}
        if isinstance(caller_config, dict):
            merged.update(caller_config)
        extra["config"] = merged
    if options is not None:
        extra.update(options.to_kwargs())
    anon_str = "stud" if anonymous else "no"
    raw = await rpc.content_create(
        type="followup", cid=post_id, subject=content, content=content, anonymous=anon_str, **extra
    )
    result = raw.get("result", raw)
    return PostCreatedResponse.model_validate(result)


async def create_reply(  # noqa: PLR0913
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    post_id: str,
    content: str,
    anonymous: bool = False,
    options: PublishingOptions | None = None,
    **kwargs: Any,
) -> PostCreatedResponse:
    """Add a reply (feedback) to an existing follow-up.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the follow-up (the parent of this reply).
        content: Reply content.
        anonymous: Whether to post anonymously.
        options: Publishing options.
        **kwargs: Additional parameters.

    Returns:
        PostCreatedResponse with new reply ID.

    Raises:
        ValidationError: If content is empty.

        Example:
            ```python
            # Example for create_reply
            res = await create_reply()
            ```
    """
    if not content or not content.strip():
        raise ValidationError("content must be non-empty")
    extra = dict(kwargs)
    if options is not None:
        extra.update(options.to_kwargs())
    anon_str = "stud" if anonymous else "no"
    raw = await rpc.content_create(
        type="feedback", cid=post_id, subject=content, content=content, anonymous=anon_str, **extra
    )
    result = raw.get("result", raw)
    return PostCreatedResponse.model_validate(result)


async def answer_post(  # noqa: PLR0913
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    post_id: str,
    content: str,
    instructor_answer: bool = False,
    anonymous: bool = False,
    revision: int = 1,
) -> None:
    """Answer an existing post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post to answer.
        content: Answer content.
        instructor_answer: Whether this is an instructor answer.
        anonymous: Whether to post anonymously (students only).
        revision: Revision number; must exceed the current answer's history size.

    Raises:
        ValidationError: If post_id or content is empty.
        NotFoundError: If the post does not exist.
        ContentError: If the answer fails.

        Example:
            ```python
            # Example for answer_post
            res = await answer_post()
            ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    if not content or not content.strip():
        raise ValidationError("content must be non-empty")
    try:
        await rpc.content_answer(
            post_id, content, instructor_answer, anonymous=anonymous, revision=revision
        )
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to answer post {post_id}: {exc}") from exc


async def endorse(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    post_id: str,
    as_instructor_badge: bool = False,
) -> bool:
    """Endorse a post or answer.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post or answer to endorse.
        as_instructor_badge: If True, award an instructor badge.

    Returns:
        True if endorsement was successful.

    Raises:
        ValidationError: If post_id is empty.
        NotFoundError: If the post does not exist.
        ContentError: If the endorsement fails.

        Example:
            ```python
            # Example for endorse
            res = await endorse()
            ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    try:
        if as_instructor_badge:
            await rpc.add_badge(post_id)
        else:
            await rpc.content_upvote(post_id)
        return True
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to endorse post {post_id}: {exc}") from exc


async def delete_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    """Delete a post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post to delete.

    Returns:
        True if deletion was successful.

    Raises:
        ValidationError: If post_id is empty.
        NotFoundError: If the post does not exist.
        ContentError: If the deletion fails.

        Example:
            ```python
            # Example for delete_post
            res = await delete_post()
            ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    try:
        # Annotated ``Any`` so the defensive isinstance below survives strict
        # type checking — mocked/alternative transports may return non-dicts.
        raw: Any = await rpc.content_delete(post_id)
        # Verified live: content.delete returns an empty dict on success
        # (no {"result": "success"} wrapper). Success = no embedded error
        # AND no explicitly failed result value.
        if not isinstance(raw, dict):
            return True
        return raw.get("result", "success") in (None, "success")
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to delete post {post_id}: {exc}") from exc


async def add_tag(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str, tag: str
) -> None:
    """Add a tag to a post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post.
        tag: Tag name to add.

    Raises:
        ValidationError: If post_id or tag is empty.
        NotFoundError: If the post does not exist.
        ContentError: If adding the tag fails.

        Example:
            ```python
            # Example for add_tag
            res = await add_tag()
            ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    if not tag or not tag.strip():
        raise ValidationError("tag must be non-empty")
    try:
        await rpc.content_add_tag(post_id, tag)
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to add tag to post {post_id}: {exc}") from exc


async def remove_tag(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str, tag: str
) -> None:
    """Remove a tag from a post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post.
        tag: Tag name to remove.

    Raises:
        ValidationError: If post_id or tag is empty.
        NotFoundError: If the post does not exist.
        ContentError: If removing the tag fails.

        Example:
            ```python
            # Example for remove_tag
            res = await remove_tag()
            ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    if not tag or not tag.strip():
        raise ValidationError("tag must be non-empty")
    try:
        await rpc.content_remove_tag(post_id, tag)
    except (NotFoundError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to remove tag from post {post_id}: {exc}") from exc


async def resolve_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    """Mark a post as resolved.

    Fetches the current post data and re-submits it with
    ``status="resolved"`` via ``content.update``.  This is the
    preferred way to change post-level status — the dedicated
    ``content.mark_resolved`` RPC can return *Invalid content* on
    some live API payloads and should only be used for follow-up/comment
    resolution.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post to resolve.

    Returns:
        True if the operation succeeded.

    Raises:
        ValidationError: If post_id is empty.

    Note:
        Unlike sibling operations, generic (non-SDK) exceptions propagate
        unwrapped here.  This is an intentional, tested contract — callers
        that need uniform wrapping should catch ``Exception`` at the call site.

    Example:
        ```python
        from piazza_sdk.api.rpc import RPC
        from piazza_sdk.domain.posts import resolve_post

        async def mark_answered(rpc: RPC, post_id: str) -> bool:
            \"\"\"Mark a question as resolved once answered.\"\"\"
            return await resolve_post(rpc, post_id=post_id)

        # Typical usage inside an async session context:
        success = await resolve_post(rpc, post_id="cl7k3x2f5")
        if success:
            print("Post marked as resolved")
        ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    post_data: dict[str, Any] = {}
    if hasattr(rpc, "content_get"):
        # Annotated ``Any``: duck-typed RPCs (mocks, alternate transports) may
        # return a bare dict instead of a coroutine.
        res: Any = rpc.content_get(post_id)
        if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
            post_data = await res
        elif isinstance(res, dict):
            post_data = res
    history_entries = post_data.get("history", [])
    first_hist = (
        history_entries[0] if history_entries and isinstance(history_entries[0], dict) else {}
    )
    subject = first_hist.get("subject", post_data.get("subject", ""))
    content = first_hist.get("content", post_data.get("content", ""))
    folders = post_data.get("folders", ["other"])
    raw: Any = await rpc.content_update(
        cid=post_id,
        subject=subject,
        content=content,
        folders=folders,
        anonymous=post_data.get("default_anonymity", "no"),
        status="resolved",
    )
    if not isinstance(raw, dict):
        return True
    return raw.get("result", "success") in (None, "success")


async def unresolve_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    """Mark a resolved post as active (unresolve).

    This fetches the current post data and re-submits it with
    ``status="active"`` via ``content.update``.  Mirrors the behaviour
    of :func:`resolve_post` but sets the status back to ``"active"``.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post to unresolve.

    Returns:
        True if the operation succeeded.

    Raises:
        ValidationError: If post_id is empty.

    Note:
        Unlike sibling operations, generic (non-SDK) exceptions propagate
        unwrapped here.  This is an intentional, tested contract — callers
        that need uniform wrapping should catch ``Exception`` at the call site.

    Example:
        ```python
        from piazza_sdk.api.rpc import RPC
        from piazza_sdk.domain.posts import unresolve_post

        async def reopen_question(rpc: RPC, post_id: str) -> bool:
            \"\"\"Reopen a previously resolved question so students can reply.\"\"\"
            return await unresolve_post(rpc, post_id=post_id)

        # Typical usage inside an async session context:
        success = await unresolve_post(rpc, post_id="cl7k3x2f5")
        if success:
            print("Post reopened successfully")
        ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    post_data: dict[str, Any] = {}
    if hasattr(rpc, "content_get"):
        res: Any = rpc.content_get(post_id)
        if asyncio.iscoroutine(res) or hasattr(res, "__await__"):
            post_data = await res
        elif isinstance(res, dict):
            post_data = res
    history_entries = post_data.get("history", [])
    first_hist = (
        history_entries[0] if history_entries and isinstance(history_entries[0], dict) else {}
    )
    subject = first_hist.get("subject", post_data.get("subject", ""))
    content = first_hist.get("content", post_data.get("content", ""))
    folders = post_data.get("folders", ["other"])
    raw: Any = await rpc.content_update(
        cid=post_id,
        subject=subject,
        content=content,
        folders=folders,
        anonymous=post_data.get("default_anonymity", "no"),
        status="active",
    )
    if not isinstance(raw, dict):
        return True
    return raw.get("result", "success") in (None, "success")


async def mark_as_unread(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    """Mark a post as unread for the current user.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        post_id: ID of the post to mark.

    Returns:
        True if the operation succeeded.

    Raises:
        ValidationError: If post_id is empty.
        PiazzaSDKError: On unexpected errors.

        Example:
            ```python
            # Example for mark_as_unread
            res = await mark_as_unread()
            ```
    """
    if not post_id or not post_id.strip():
        raise ValidationError("post_id must be non-empty")
    try:
        raw: dict[str, Any] = await rpc.mark_as_unread(post_id)
        return raw.get("result") == "success"
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise ContentError(f"Failed to mark post as unread: {exc}") from exc


async def create_folder(
    rpc: RPC, *, session: SessionStateManager | None = None, folder_name: str
) -> list[str]:
    """Create a new folder in the network.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        folder_name: Name of the folder to create.

    Returns:
        Updated list of folder names after creation.

    Raises:
        ValidationError: If folder_name is empty.
        PiazzaSDKError: On unexpected errors.

        Example:
            ```python
            # Example for create_folder
            res = await create_folder()
            ```
    """
    if not folder_name or not folder_name.strip():
        raise ValidationError("folder_name must be non-empty")
    try:
        raw: dict[str, Any] = await rpc.add_folder(folder_name)
        folders: list[str] = raw.get("folders", []) if isinstance(raw, dict) else []
        return folders
    except PiazzaSDKError:
        raise
    except Exception as exc:
        raise ContentError(f"Failed to create folder: {exc}") from exc


async def save_draft(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    subject: str,
    content: str,
    post_type: PostType | str = "question",
    **kwargs: Any,
) -> str:
    """Save a post as a draft.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        subject: Post title/subject.
        content: Post content (HTML or plain text).
        post_type: Type of post (question, note, poll).
        **kwargs: Additional parameters.

    Returns:
        The draft post ID.

    Raises:
        ValidationError: If subject or content is empty.
        ContentError: If saving the draft fails.

        Example:
            ```python
            # Example for save_draft
            res = await save_draft()
            ```
    """
    if not subject or not subject.strip():
        raise ValidationError("subject must be non-empty")
    if not content or not content.strip():
        raise ValidationError("content must be non-empty")
    try:
        result = await rpc.content_save_draft(
            subject=subject, content=content, post_type=post_type, **kwargs
        )
        draft_id = result.get("id")
        if not isinstance(draft_id, str) or not draft_id:
            raise ContentError("Piazza backend accepted the draft but failed to return an ID.")
        return draft_id
    except (ContentError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to save draft: {exc}") from exc


# Milliseconds per second for unix-millisecond scheduling timestamps.
_MS_PER_SECOND = 1000

# Wire keys a ``network.save_draft`` response may carry the ID under.
_DRAFT_ID_KEYS = ("id", "draft_id", "draftId")


def _to_epoch_ms(at: datetime | int | float) -> int:
    """Normalize a scheduling target to a unix-millisecond timestamp.

    Args:
        at: Aware/naive :class:`~datetime.datetime` (naive is treated as
            UTC) or an already-epoch-milliseconds number.

    Returns:
        Unix epoch milliseconds.

    Raises:
        ValidationError: If *at* is neither datetime nor number.
    """
    if isinstance(at, bool):
        raise ValidationError("at must be a datetime or unix millisecond timestamp")
    if isinstance(at, int | float):
        return int(at)
    if isinstance(at, datetime):
        aware = at if at.tzinfo is not None else at.replace(tzinfo=UTC)
        return int(aware.timestamp() * _MS_PER_SECOND)
    raise ValidationError("at must be a datetime or unix millisecond timestamp")


def _extract_draft_id(response: Any) -> str:
    """Pull the draft identifier out of a ``network.save_draft`` response.

    Args:
        response: Unwrapped API response (dict or bare string).

    Returns:
        The draft ID string.

    Raises:
        ContentError: If no recognizable identifier is present.
    """
    if isinstance(response, str) and response.strip():
        return response
    if isinstance(response, dict):
        nested = response.get("draft")
        candidates: list[Any] = [response.get(key) for key in _DRAFT_ID_KEYS]
        if isinstance(nested, dict):
            candidates.extend(nested.get(key) for key in _DRAFT_ID_KEYS)
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, int) and not isinstance(value, bool):
                return str(value)
    raise ContentError(f"Could not extract draft ID from network.save_draft response: {response!r}")


async def schedule_post(  # noqa: PLR0913 - explicit scheduling surface
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    title: str,
    content: str,
    at: datetime | int | float,
    post_type: PostType | str = "question",
    anonymous: bool = False,
    folders: list[str] | None = None,
    **kwargs: Any,
) -> ScheduledPostConfirmation:
    """Create a scheduled post (question or note).

    Implements the two-step wire flow used by Piazza's web scheduler
    (both steps live-verified 2026-08):

    1. ``network.save_draft`` persists the draft carrying
       ``btn.schedule_later`` / ``btn.schedule_later_time`` and returns
       the draft ID as a **bare-string** result.
    2. ``content.create`` submits with ``draftId`` plus
       ``config.schedule_later`` / ``config.schedule_later_time`` and is
       confirmed with ``{"scheduled": true}`` — no post ID exists until
       Piazza publishes the content at *at*.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        title: Post title/subject.
        content: Post content (HTML or plain text).
        at: When to publish — :class:`~datetime.datetime` or unix
            milliseconds since epoch. Must be in the future.
        post_type: ``"question"`` or ``"note"``; polls cannot be
            scheduled upstream.
        anonymous: Whether to post anonymously.
        folders: Folder names; must exist in the course (defaults to
            ``["General"]``).
        **kwargs: Additional parameters forwarded to ``content.create``.

    Returns:
        ScheduledPostConfirmation with the draft ID and the backend's
        ``scheduled`` flag.

    Raises:
        ValidationError: On empty title/content, poll type, or invalid
            *at* shape.
        ContentError: If either wire step fails.

        Example:
            ```python
            # Example for schedule_post
            res = await schedule_post()
            ```
    """
    if not title or not title.strip():
        raise ValidationError("title must be non-empty")
    if not content or not content.strip():
        raise ValidationError("content must be non-empty")
    normalized_type = str(post_type).lower()
    if normalized_type == "poll":
        raise ValidationError("Piazza does not support scheduling poll posts")
    publish_at_ms = _to_epoch_ms(at)

    try:
        draft_response = await rpc.network_save_draft(
            draft={
                "content": content,
                "folders": folders if folders is not None else ["General"],
                "btn": {
                    "post_type_note": normalized_type == "note",
                    "post_type_question": normalized_type == "question",
                    "schedule_later": True,
                    "schedule_later_time": publish_at_ms,
                },
                "txt": {"post_summary": title},
            }
        )
        draft_id = _extract_draft_id(draft_response)

        extra_config = kwargs.pop("config", None)
        config: dict[str, Any] = (
            {**extra_config, "schedule_later": True, "schedule_later_time": publish_at_ms}
            if isinstance(extra_config, dict)
            else {"schedule_later": True, "schedule_later_time": publish_at_ms}
        )
        raw = await rpc.content_create(
            subject=title,
            title=title,
            content=content,
            type=post_type,
            anonymous="stud" if anonymous else "no",
            folders=folders if folders is not None else ["General"],
            draftId=draft_id,
            config=config,
            **kwargs,
        )
        result = raw if isinstance(raw, dict) else {}
        return ScheduledPostConfirmation(
            draft_id=draft_id, scheduled=bool(result.get("scheduled", False))
        )
    except (ContentError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise ContentError(f"Failed to schedule post: {exc}") from exc


async def upload_asset(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    filename: str,
    file_data: bytes,
    content_type: str | None = None,
) -> AssetUploadResponse:
    """Upload a file asset to Piazza.

    Args:
        rpc: RPC client instance.
        session: Optional session manager for automatic refresh.
        filename: Name of the file to upload.
        file_data: Raw bytes of the file content.
        content_type: MIME type of the file. Auto-detected if not provided.

    Returns:
        AssetUploadResponse with asset ID and upload URL.

    Raises:
        ValidationError: If filename or file_data is empty.
        UploadError: If the upload fails.

        Example:
            ```python
            # Example for upload_asset
            res = await upload_asset()
            ```
    """
    if not filename or not filename.strip():
        raise ValidationError("filename must be non-empty")
    if not file_data:
        raise ValidationError("file_data must not be empty")
    if content_type is None:
        guessed, _ = mimetypes.guess_type(filename)
        content_type = guessed or "application/octet-stream"
    try:
        url_data = await rpc.asset_get_upload_url(filename)
        upload_url: str | None = url_data.get("url") or url_data.get("upload_url")
        if not upload_url:
            raise UploadError("No upload URL returned from API")
        parsed = urlparse(upload_url)
        allowed_upload_hosts = {"s3.amazonaws.com", "piazza.com"}
        if parsed.hostname and not any(
            parsed.hostname == h or parsed.hostname.endswith("." + h) for h in allowed_upload_hosts
        ):
            raise ValidationError(
                f"upload URL host '{parsed.hostname}' not in allowed list: {allowed_upload_hosts}"
            )
        http_client = rpc.client
        response = await http_client.put(
            upload_url, content=file_data, headers={"Content-Type": content_type}
        )
        response.raise_for_status()
        return AssetUploadResponse(
            id=url_data.get("id", ""), url=url_data.get("url") or url_data.get("upload_url")
        )
    except (UploadError, PiazzaSDKError):
        raise
    except Exception as exc:
        raise UploadError(f"Failed to upload asset {filename}: {exc}") from exc


async def bookmark_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    await rpc.content_bookmark(post_id)
    return True


async def unbookmark_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    await rpc.content_unbookmark(post_id)
    return True


async def favorite_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    await rpc.content_mark_favorite(post_id)
    return True


async def unfavorite_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str
) -> bool:
    await rpc.content_mark_unfavorite(post_id)
    return True


async def view_post(rpc: RPC, *, session: SessionStateManager | None = None, post_id: str) -> bool:
    await rpc.content_view(post_id)
    return True


async def edit_post(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str, type: str, **kwargs: Any
) -> bool:
    await rpc.content_edit(post_id, type=type, **kwargs)
    return True


async def cancel_edit(
    rpc: RPC, *, session: SessionStateManager | None = None, network_id: str
) -> bool:
    await rpc.content_cancel_edit(network_id)
    return True


async def remove_endorsement(
    rpc: RPC, *, session: SessionStateManager | None = None, post_id: str, type: str = "tag_good"
) -> bool:
    await rpc.content_remove_feedback(post_id, type)
    return True


async def auto_save_draft(  # noqa: PLR0913
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    post_id: str,
    type: str,
    body: str,
    revision: int = 1,
    editor: str = "rte",
) -> bool:
    await rpc.content_auto_save(post_id, type, body, revision, editor)
    return True


async def pin_post(rpc: RPC, *, session: SessionStateManager | None = None, post_id: str) -> bool:
    """Pin a post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        post_id: The ID of the post to pin.

    Returns:
        True if successful.

        Example:
            ```python
            # Example for pin_post
            res = await pin_post()
            ```
    """
    await rpc.content_pin(post_id)
    return True


async def unpin_post(rpc: RPC, *, session: SessionStateManager | None = None, post_id: str) -> bool:
    """Unpin a post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        post_id: The ID of the post to unpin.

    Returns:
        True if successful.

        Example:
            ```python
            # Example for unpin_post
            res = await unpin_post()
            ```
    """
    await rpc.content_unpin(post_id)
    return True


async def mark_duplicate(
    rpc: RPC,
    *,
    session: SessionStateManager | None = None,
    duplicate_id: str,
    master_id: str,
    message: str = "",
) -> bool:
    """Mark a post as a duplicate of another post.

    Args:
        rpc: RPC client instance.
        session: Optional session manager.
        duplicate_id: The ID of the post that is a duplicate.
        master_id: The ID of the post to keep.
        message: Optional reason or message for duplication.

    Returns:
        True if successful.

        Example:
            ```python
            # Example for mark_duplicate
            res = await mark_duplicate()
            ```
    """
    await rpc.content_duplicate(duplicate_id, master_id, message)
    return True
