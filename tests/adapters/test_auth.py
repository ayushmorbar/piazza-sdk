"""Unit tests for adapters/auth.py — CookieJar and SessionState."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from cryptography.fernet import Fernet

if TYPE_CHECKING:
    from pathlib import Path

from piazza_sdk.adapters.auth import CookieJar, SessionState
from piazza_sdk.exceptions import PiazzaSDKError


class TestSessionStateEnum:
    """Verify states defined on SessionState."""

    def test_states_exist(self):
        assert SessionState.UNAUTHENTICATED.value == "unauthenticated"
        assert SessionState.AUTHENTICATING.value == "authenticating"
        assert SessionState.AUTHENTICATED.value == "authenticated"
        assert SessionState.CLOSED.value == "closed"


class TestCookieJarHeaderManipulation:
    """Verify CookieJar cookie header parsing and serialization."""

    def test_update_from_header(self):
        jar = CookieJar()
        jar.update_from_header("session=abc123; path=/")
        assert "session" in jar.cookies
        assert jar.cookies["session"] == "abc123"

    def test_update_from_header_multiple(self):
        jar = CookieJar()
        jar.update_from_header("a=1; b=2; c=3")
        assert jar.cookies["a"] == "1"
        assert jar.cookies["b"] == "2"
        assert jar.cookies["c"] == "3"

    def test_to_header(self):
        jar = CookieJar()
        jar.cookies["session"] = "abc"
        jar.cookies["csrf"] = "xyz"
        header = jar.to_header()
        assert "session=abc" in header
        assert "csrf=xyz" in header

    def test_to_header_empty(self):
        jar = CookieJar()
        assert jar.to_header() == ""


class TestCookieJarDictImportExport:
    """Plain-dict cookie hand-off (reference-client get/set_cookies parity)."""

    def test_export_returns_defensive_copy(self):
        jar = CookieJar()
        jar.set("session", "abc")
        exported = jar.export_dict()
        exported["session"] = "MUTATED"
        assert jar.cookies["session"] == "abc"
        assert jar.export_dict() == {"session": "abc"}

    def test_import_round_trip(self):
        jar = CookieJar()
        source = {"session_id": "s1", "_piazza_s": "p1"}
        count = jar.import_dict(source)
        assert count == 2
        assert jar.export_dict() == source

    def test_import_skips_blank_and_non_string(self):
        jar = CookieJar()
        count = jar.import_dict(
            {
                "good": "v",
                "blank_name": "",
                "": "orphan",
                "num": 5,  # type: ignore[dict-item]
            }
        )
        assert count == 1
        assert jar.cookies == {"good": "v"}

    def test_import_does_not_touch_csrf_token(self):
        jar = CookieJar(csrf_token="keep-me")
        jar.import_dict({"a": "1"})
        assert jar.csrf_token == "keep-me"


class TestCookieJarStorageAndEncryption:
    """Verify CookieJar serialization to disk (plaintext and Fernet encrypted)."""

    @pytest.fixture
    def fernet_key(self) -> str:
        return Fernet.generate_key().decode()

    @pytest.mark.asyncio
    async def test_save_load_encrypted(self, tmp_path: Path, fernet_key: str):
        path = tmp_path / "encrypted_cookies.json"
        original = CookieJar(
            cookies={"session_id": "abc123", "csrf": "xyz789"}, encryption_key=fernet_key
        )
        await original.save(path)

        loaded = CookieJar(cookies={}, encryption_key=fernet_key)
        result = await loaded.load(path)
        assert result is True
        assert loaded.cookies == original.cookies

    @pytest.mark.asyncio
    async def test_save_load_plaintext(self, tmp_path: Path):
        path = tmp_path / "plain_cookies.json"
        original = CookieJar(cookies={"session_id": "abc123"})
        await original.save(path)

        loaded = CookieJar()
        result = await loaded.load(path)
        assert result is True
        assert loaded.cookies == {"session_id": "abc123"}

    @pytest.mark.asyncio
    async def test_load_encrypted_file_without_key_falls_back(
        self, tmp_path: Path, fernet_key: str
    ):
        """An encrypted file loaded without a key should fail gracefully."""
        path = tmp_path / "encrypted.json"
        original = CookieJar(cookies={"x": "y"}, encryption_key=fernet_key)
        await original.save(path)

        loaded = CookieJar()
        result = await loaded.load(path)
        assert result is False

    @pytest.mark.asyncio
    async def test_load_plaintext_file_with_key_fails(self, tmp_path: Path, fernet_key: str):
        """A plaintext file loaded with a key should raise, not silently fall back."""
        path = tmp_path / "plain.json"
        original = CookieJar(cookies={"a": "b"})
        await original.save(path)

        loaded = CookieJar(cookies={}, encryption_key=fernet_key)
        with pytest.raises(PiazzaSDKError, match="could not be decrypted"):
            await loaded.load(path)

    def test_encryption_key_excluded_from_dump(self, fernet_key: str):
        jar = CookieJar(cookies={"x": "y"}, encryption_key=fernet_key)
        dumped = jar.model_dump()
        assert "encryption_key" not in dumped

    @pytest.mark.asyncio
    async def test_csrf_token_persists_round_trip(self, tmp_path: Path, fernet_key: str):
        """csrf_token survives save → load cycle (encrypted)."""
        path = tmp_path / "csrf_encrypted.json"
        original = CookieJar(
            cookies={"session_id": "abc"}, csrf_token="tok_123_secret", encryption_key=fernet_key
        )
        await original.save(path)

        loaded = CookieJar(cookies={}, encryption_key=fernet_key)
        await loaded.load(path)
        assert loaded.csrf_token == "tok_123_secret"
        assert loaded.cookies == {"session_id": "abc"}

    @pytest.mark.asyncio
    async def test_csrf_token_persists_plaintext(self, tmp_path: Path):
        """csrf_token survives save → load cycle (plaintext)."""
        path = tmp_path / "csrf_plain.json"
        original = CookieJar(cookies={"s": "v"}, csrf_token="plain_tok")
        await original.save(path)

        loaded = CookieJar()
        await loaded.load(path)
        assert loaded.csrf_token == "plain_tok"

    @pytest.mark.asyncio
    async def test_csrf_token_backward_compat_no_field(self, tmp_path: Path):
        """Loading an old file without csrf_token leaves csrf_token as None."""
        path = tmp_path / "old_format.json"
        path.write_text('{"cookies": {"session_id": "abc"}}')

        loaded = CookieJar()
        await loaded.load(path)
        assert loaded.csrf_token is None
        assert loaded.cookies == {"session_id": "abc"}

    def test_clear_resets_csrf_token(self):
        """clear() wipes both cookies dict and csrf_token."""
        jar = CookieJar(cookies={"s": "v"}, csrf_token="tok_xyz")
        jar.clear()
        assert jar.cookies == {}
        assert jar.csrf_token is None
