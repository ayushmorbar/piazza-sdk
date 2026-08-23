"""Auth module — re-exports from adapters for backward compatibility."""

from piazza_sdk.adapters.auth import CookieJar, SessionState
from piazza_sdk.adapters.session import SessionStateManager
from piazza_sdk.config import SessionConfig

__all__ = ["CookieJar", "SessionConfig", "SessionState", "SessionStateManager"]
