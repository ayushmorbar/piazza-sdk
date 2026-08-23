"""Configuration management for Piazza SDK.

Provides the global configuration object (PiazzaConfig) used to configure
the SDK's network, authentication, caching, and logging behavior.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = ["PiazzaConfig", "SessionConfig"]


PIAZZA_BASE_URL = "https://piazza.com"
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


class PiazzaConfig(BaseSettings):
    """Global configuration settings for Piazza SDK.

    Can be instantiated directly or configured via environment variables
    prefixed with PIAZZA_.
    """

    model_config = SettingsConfigDict(
        env_prefix="PIAZZA_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    course_id: str = Field(description="The Piazza course/network ID (e.g. 'j1b2c3d4e5f6')")
    user_agent: str = Field(default=_DEFAULT_USER_AGENT, description="Custom User-Agent string")
    sec_ch_ua_platform: str = Field(default="Windows")
    base_url: str = Field(default=PIAZZA_BASE_URL, description="Base URL for the Piazza API")
    timeout: float = Field(default=30.0, description="HTTP request timeout in seconds")
    retries: int = Field(default=3, description="Number of retry attempts for transient failures")
    retry_delay: float = Field(default=1.0, description="Base delay between retries in seconds")
    cookie_path: Path | None = Field(
        default=None, description="Path for persisting cookies to disk"
    )
    encryption_key: str | None = Field(
        default=None, description="Fernet key for encrypting persisted cookies"
    )
    log_level: str = Field(default="INFO", description="Global logging level for SDK operations")
    enable_caching: bool = Field(
        default=False, description="Enable local caching of immutable endpoints"
    )

    @field_validator("encryption_key")
    @classmethod
    def _validate_fernet_key(cls, v: str | None) -> str | None:
        """Validate that the encryption key is a valid Fernet key."""
        if v is None:
            return v
        try:
            Fernet(v.encode() if isinstance(v, str) else v)
        except Exception as e:
            raise ValueError(
                f"Invalid Fernet encryption key: {e}. "
                "Generate a valid key with: from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())"
            ) from e
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate and enforce HTTPS on base_url."""
        if self.base_url:
            parsed = urlparse(self.base_url)
            if parsed.scheme != "https":
                # Rebuild URL with HTTPS scheme
                self.base_url = parsed._replace(scheme="https").geturl()

        # Automatically configure the python logger when instantiated
        logging.getLogger("piazza_sdk").setLevel(
            getattr(logging, self.log_level.upper(), logging.INFO)
        )

    @property
    def login_page_url(self) -> str:
        """Full URL for the login page (GET to capture CSRF token)."""
        return f"{self.base_url.rstrip('/')}/account/login"

    @property
    def login_url(self) -> str:
        """Full login POST URL for credential submission."""
        return f"{self.base_url.rstrip('/')}/class"

    @property
    def network_base_url(self) -> str:
        """Base URL for network API calls."""
        return f"{self.base_url.rstrip('/')}/network"


# Alias for backward compatibility
SessionConfig = PiazzaConfig
