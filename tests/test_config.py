"""Unit tests for configuration management (PiazzaConfig & SessionConfig)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from pydantic import ValidationError

if TYPE_CHECKING:
    from pathlib import Path

from piazza_sdk.config import PIAZZA_BASE_URL, PiazzaConfig, SessionConfig


class TestPiazzaConfigDefaults:
    """Verify PiazzaConfig instantiation, default values, and aliases."""

    def test_default_values(self):
        """PiazzaConfig initializes with expected default values."""
        config = PiazzaConfig(course_id="c_test_123")
        assert config.course_id == "c_test_123"
        assert "Chrome" in config.user_agent
        assert config.base_url == PIAZZA_BASE_URL
        assert config.timeout == 30.0
        assert config.retries == 3
        assert config.retry_delay == 1.0
        assert config.cookie_path is None
        assert config.encryption_key is None
        assert config.log_level == "INFO"
        assert config.enable_caching is False

    def test_session_config_alias(self):
        """SessionConfig is an alias for PiazzaConfig."""
        assert SessionConfig is PiazzaConfig
        config = SessionConfig(course_id="c_test_alias")
        assert isinstance(config, PiazzaConfig)
        assert config.course_id == "c_test_alias"

    def test_custom_user_agent(self):
        """Custom user_agent is properly respected."""
        config = PiazzaConfig(course_id="c_test", user_agent="CustomBot/1.0")
        assert config.user_agent == "CustomBot/1.0"

    def test_url_properties(self):
        """Derived URL properties generate valid endpoint strings."""
        config = PiazzaConfig(course_id="c_test", base_url="https://piazza.com")
        assert config.login_page_url == "https://piazza.com/account/login"
        assert config.login_url == "https://piazza.com/class"
        assert config.network_base_url == "https://piazza.com/network"


class TestPiazzaConfigValidation:
    """Verify validation rules on config fields."""

    def test_missing_course_id_raises(self):
        """Omitting required course_id raises ValidationError if not in env."""
        with patch.dict(os.environ, {}, clear=True), pytest.raises(ValidationError):
            PiazzaConfig(_env_file=None)  # type: ignore[call-arg]

    def test_http_upgraded_to_https(self):
        """HTTP base_url is automatically rewritten to HTTPS."""
        config = PiazzaConfig(course_id="c_test", base_url="http://piazza.com")
        assert config.base_url.startswith("https://")

    def test_valid_fernet_key(self):
        """Valid 32-byte Fernet key passes validation."""
        valid_key = Fernet.generate_key().decode()
        config = PiazzaConfig(course_id="c_test", encryption_key=valid_key)
        assert config.encryption_key == valid_key

    def test_invalid_fernet_key_raises(self):
        """Malformed encryption key fails validation."""
        with pytest.raises(ValidationError, match="Invalid Fernet encryption key"):
            PiazzaConfig(course_id="c_test", encryption_key="not-a-valid-key")

    def test_cookie_path_as_path(self, tmp_path: Path):
        """cookie_path accepts Path or string."""
        path = tmp_path / "cookies.json"
        config = PiazzaConfig(course_id="c_test", cookie_path=path)
        assert config.cookie_path == path


class TestPiazzaConfigEnvironment:
    """Verify loading settings from environment variables."""

    def test_load_from_env_prefix(self):
        """Settings load from PIAZZA_ prefixed env vars."""
        env_vars = {
            "PIAZZA_COURSE_ID": "env_course_999",
            "PIAZZA_TIMEOUT": "45.5",
            "PIAZZA_RETRIES": "5",
            "PIAZZA_LOG_LEVEL": "DEBUG",
            "PIAZZA_ENABLE_CACHING": "true",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = PiazzaConfig()
            assert config.course_id == "env_course_999"
            assert config.timeout == 45.5
            assert config.retries == 5
            assert config.log_level == "DEBUG"
            assert config.enable_caching is True

    def test_explicit_args_override_env(self):
        """Explicit constructor arguments override environment variables."""
        with patch.dict(os.environ, {"PIAZZA_COURSE_ID": "from_env"}, clear=False):
            config = PiazzaConfig(course_id="from_code")
            assert config.course_id == "from_code"
