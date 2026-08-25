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
    "unbookmark_post",
    "unfavorite_post",
    "unpin_post",
    "unresolve_post",
    "upload_asset",
    "view_post",
]

import asyncio
import mimetypes
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from piazza_sdk.exceptions import (
    ContentError,
    NotFoundError,
    PiazzaSDKError,
    UploadError,
    ValidationError,
)
from piazza_sdk.models.post import AssetUploadResponse, PostCreatedResponse

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
            course — Piazza rejects unknown folders with
            "Please specify folder" (verified live).
        **kwargs: Additional parameters.

    Returns:
        PostCreatedResponse with new post ID.

    Raises:
        ValidationError: If title or content is empty.

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
    extra = dict(kwargs)
    if options is not None:
        extra.update(options.to_kwargs())
    # Piazza's content.create expects ``subject`` (verified live: sending
    # only ``title`` fails with "Missing parameter: subject"), an anonymity
    # *string* ("no"/"stud"/"full") — bool False fails with "Invalid
    # anonymity setting" — and at least one folder ("Please specify
    # folder"). ``title`` is still sent for backward compatibility.
    if folders is None:
        folders = ["General"]
    raw = await rpc.content_create(
        subject=title,
        title=title,
        content=content,
        type=post_type,
        anonymous="stud" if anonymous else "no",
        folders=folders,
        **extra,
    )
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
