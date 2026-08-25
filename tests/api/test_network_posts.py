"""Tests for api/network.py facade layer.

Covers session lifecycle, delegation to domain functions, input validation,
error wrapping, and async iterators. Methods already tested in
test_feature_parity.py and test_advanced_features.py are excluded.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from piazza_sdk.api.network import Network
from piazza_sdk.exceptions import NotFoundError, PiazzaSDKError, ValidationError
from piazza_sdk.models.enums import FeedItemDefaultAnonymity, FeedItemType
from piazza_sdk.models.feed import Feed, FeedItem
from piazza_sdk.models.post import AssetUploadResponse, Post, PostCreatedResponse, PublishingOptions

# ── Helpers ───────────────────────────────────────────────────────────


def _make_network() -> Network:
    """Create a Network with mocked internals."""
    net = object.__new__(Network)
    net._rpc = AsyncMock()
    net._session = AsyncMock()
    net._nid = "test_nid"
    return net


def _make_feed_item(item_id: str = "item_1", subject: str = "Subject") -> FeedItem:
    return FeedItem(
        id=item_id,
        subject=subject,
        type=FeedItemType.QUESTION,
        created=datetime.now(UTC),
        updated=datetime.now(UTC),
        default_anonymity=FeedItemDefaultAnonymity.NO,
    )


def _make_feed(items: list[FeedItem] | None = None) -> MagicMock:
    feed = MagicMock(spec=Feed)
    feed.feed = [_make_feed_item()] if items is None else items
    return feed


# ── Session lifecycle ─────────────────────────────────────────────────


class TestGetPost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_post("")

    @pytest.mark.asyncio
    async def test_whitespace_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.get_post("   ")

    @pytest.mark.asyncio
    async def test_empty_result_raises_not_found(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(return_value=None)
        with pytest.raises(NotFoundError, match="Post not found"):
            await net.get_post("missing_post")

    @pytest.mark.asyncio
    async def test_empty_dict_raises_not_found(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(return_value={})
        with pytest.raises(NotFoundError, match="Post not found"):
            await net.get_post("empty_post")

    @pytest.mark.asyncio
    async def test_returns_post_model(self) -> None:
        net = _make_network()
        raw = {
            "id": "p1",
            "title": "Test Post",
            "subject": "Test Subject",
            "type": "question",
            "author": "Alice",
            "nr": 5,
            "tags": ["hw1"],
            "folder": "Homework",
            "views": 100,
        }
        net._rpc.content_get = AsyncMock(return_value=raw)
        result = await net.get_post("p1")
        assert isinstance(result, Post)
        assert result.id == "p1"
        assert result.title == "Test Post"
        assert result.nr == 5
        assert result.tags == ["hw1"]

    @pytest.mark.asyncio
    async def test_parse_error_raises_piazza_sdk_error(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(side_effect=RuntimeError("json parse fail"))
        with pytest.raises(PiazzaSDKError, match="Failed to parse post"):
            await net.get_post("bad_post")

    @pytest.mark.asyncio
    async def test_piazza_sdk_error_passthrough(self) -> None:
        net = _make_network()
        net._rpc.content_get = AsyncMock(side_effect=NotFoundError("gone"))
        with pytest.raises(NotFoundError):
            await net.get_post("gone_post")


class TestCreatePost:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_create_post") as mock:
            mock.return_value = PostCreatedResponse(id="new_post")
            result = await net.create_post("title", "content")
        assert result.id == "new_post"
        mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_all_params(self) -> None:
        net = _make_network()
        opts = PublishingOptions(bypass_email=True)
        with patch("piazza_sdk.api.network._domain_create_post") as mock:
            mock.return_value = PostCreatedResponse(id="p1")
            await net.create_post(
                "title", "content", post_type="note", anonymous=True, options=opts, extra="val"
            )
        call_kwargs = mock.call_args[1]
        assert call_kwargs["title"] == "title"
        assert call_kwargs["content"] == "content"
        assert call_kwargs["post_type"] == "note"
        assert call_kwargs["anonymous"] is True
        assert call_kwargs["options"] is opts
        assert call_kwargs["extra"] == "val"


class TestCreateFollowup:
    @pytest.mark.asyncio
    async def test_string_post_id(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_add_followup") as mock:
            mock.return_value = {"ok": True}
            await net.create_followup("p1", "followup content")
        mock.assert_awaited_once()
        assert mock.call_args[1]["post_id"] == "p1"

    @pytest.mark.asyncio
    async def test_post_model_extracts_id(self) -> None:
        net = _make_network()
        post = Post(id="p2", title="t", raw={})
        with patch("piazza_sdk.api.network._domain_add_followup") as mock:
            mock.return_value = {"ok": True}
            await net.create_followup(post, "content")
        assert mock.call_args[1]["post_id"] == "p2"

    @pytest.mark.asyncio
    async def test_passes_options(self) -> None:
        net = _make_network()
        opts = PublishingOptions(silent_update=True)
        with patch("piazza_sdk.api.network._domain_add_followup") as mock:
            mock.return_value = {"ok": True}
            await net.create_followup("p1", "content", anonymous=True, options=opts)
        call_kwargs = mock.call_args[1]
        assert call_kwargs["anonymous"] is True
        assert call_kwargs["options"] is opts


class TestResolvePost:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_resolve_post") as mock:
            mock.return_value = True
            result = await net.resolve_post("p1")
        mock.assert_awaited_once_with(net._rpc, post_id="p1")
        assert result is True


class TestUnresolvePost:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_unresolve_post") as mock:
            mock.return_value = True
            result = await net.unresolve_post("p1")
        mock.assert_awaited_once_with(net._rpc, post_id="p1")
        assert result is True


class TestDeletePost:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_delete_post") as mock:
            mock.return_value = True
            result = await net.delete_post("p1")
        assert result is True
        mock.assert_awaited_once_with(net._rpc, post_id="p1")


class TestMarkAsUnread:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_mark_as_unread") as mock:
            mock.return_value = True
            result = await net.mark_as_unread("p1")
        assert result is True
        mock.assert_awaited_once_with(net._rpc, post_id="p1")


class TestEndorsePost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.endorse_post("")

    @pytest.mark.asyncio
    async def test_delegates_and_fetches_post(self) -> None:
        net = _make_network()
        with (
            patch("piazza_sdk.api.network._domain_endorse") as mock_endorse,
            patch.object(net, "get_post", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Post(id="p1", title="t", raw={})
            result = await net.endorse_post("p1", as_instructor_badge=True)
        mock_endorse.assert_awaited_once_with(net._rpc, post_id="p1", as_instructor_badge=True)
        mock_get.assert_awaited_once_with("p1")
        assert isinstance(result, Post)


class TestPinPost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.pin_post("")

    @pytest.mark.asyncio
    async def test_pins_via_dedicated_rpc_and_returns_post(self) -> None:
        net = _make_network()
        with (
            patch.object(net._rpc, "content_pin", new_callable=AsyncMock) as mock_pin,
            patch.object(net, "get_post", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Post(id="p1", title="t", raw={})
            result = await net.pin_post("p1")
        mock_pin.assert_awaited_once_with("p1")
        mock_get.assert_awaited_once_with("p1")
        assert isinstance(result, Post)

    @pytest.mark.asyncio
    async def test_unpins_via_dedicated_rpc_and_returns_post(self) -> None:
        net = _make_network()
        with (
            patch.object(net._rpc, "content_unpin", new_callable=AsyncMock) as mock_unpin,
            patch.object(net, "get_post", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Post(id="p1", title="t", raw={})
            result = await net.unpin_post("p1")
        mock_unpin.assert_awaited_once_with("p1")
        mock_get.assert_awaited_once_with("p1")
        assert isinstance(result, Post)


class TestLockPost:
    @pytest.mark.asyncio
    async def test_empty_post_id_raises(self) -> None:
        net = _make_network()
        with pytest.raises(ValidationError, match="post_id must be non-empty"):
            await net.lock_post("")

    @pytest.mark.asyncio
    async def test_adds_lock_tag_and_returns_post(self) -> None:
        # Locking is intentionally tag-based (no dedicated Piazza endpoint).
        net = _make_network()
        with (
            patch.object(net, "add_tag", new_callable=AsyncMock) as mock_tag,
            patch.object(net, "get_post", new_callable=AsyncMock) as mock_get,
        ):
            mock_get.return_value = Post(id="p1", title="t", raw={})
            result = await net.lock_post("p1")
        mock_tag.assert_awaited_once_with("p1", "lock")
        mock_get.assert_awaited_once_with("p1")
        assert isinstance(result, Post)


class TestAddTag:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_add_tag") as mock:
            await net.add_tag("p1", "important")
        mock.assert_awaited_once_with(net._rpc, post_id="p1", tag="important")


class TestRemoveTag:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_remove_tag") as mock:
            await net.remove_tag("p1", "old_tag")
        mock.assert_awaited_once_with(net._rpc, post_id="p1", tag="old_tag")


class TestCreateFolder:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_create_folder") as mock:
            mock.return_value = ["HW1", "HW2", "HW3"]
            result = await net.create_folder("HW3")
        assert result == ["HW1", "HW2", "HW3"]
        mock.assert_awaited_once_with(net._rpc, folder_name="HW3")


class TestSaveDraft:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_save_draft") as mock:
            mock.return_value = "draft_123"
            result = await net.save_draft("subject", "content", post_type="note")
        assert result == "draft_123"
        mock.assert_awaited_once_with(
            net._rpc, subject="subject", content="content", post_type="note"
        )


class TestUploadAsset:
    @pytest.mark.asyncio
    async def test_delegates_to_domain(self) -> None:
        net = _make_network()
        file_data = b"\x89PNG\r\n"
        with patch("piazza_sdk.api.network._domain_upload_asset") as mock:
            mock.return_value = AssetUploadResponse(
                id="asset_1", url="https://example.com/file.png"
            )
            result = await net.upload_asset("photo.png", file_data)
        assert result.id == "asset_1"
        mock.assert_awaited_once_with(
            net._rpc, filename="photo.png", file_data=file_data, content_type=None
        )

    @pytest.mark.asyncio
    async def test_passes_content_type(self) -> None:
        net = _make_network()
        with patch("piazza_sdk.api.network._domain_upload_asset") as mock:
            mock.return_value = AssetUploadResponse(id="a1")
            await net.upload_asset("doc.pdf", b"data", content_type="application/pdf")
        mock.assert_awaited_once_with(
            net._rpc, filename="doc.pdf", file_data=b"data", content_type="application/pdf"
        )


# ── Users ─────────────────────────────────────────────────────────────
