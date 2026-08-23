"""Auth module — re-exports from adapters for backward compatibility."""

from piazza_sdk.adapters.auth import CookieJar, SessionConfig, SessionState
from piazza_sdk.adapters.session import SessionStateManager

__all__ = ["CookieJar", "SessionConfig", "SessionState", "SessionStateManager"]
