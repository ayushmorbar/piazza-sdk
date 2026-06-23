# Configuration

All configuration is handled through `SessionConfig`, a Pydantic `BaseSettings` model.

## SessionConfig

```python
from piazza_sdk import SessionConfig

config = SessionConfig(
    course_id="your_course_id",       # Required
    user_agent="my-app/1.0",          # Custom User-Agent header
    timeout=30.0,                     # HTTP request timeout (seconds)
    retries=3,                        # Max retry attempts on failure
    retry_delay=1.0,                  # Base delay between retries (seconds)
)
```

### Fields

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `course_id` | `str` | — | `PIAZZA_COURSE_ID` | Piazza course/network ID (required) |
| `user_agent` | `str` | `"piazza-sdk-python/2026.06.22"` | `PIAZZA_USER_AGENT` | HTTP User-Agent header |
| `base_url` | `str` | `"https://piazza.com"` | `PIAZZA_BASE_URL` | Base URL for the Piazza API |
| `timeout` | `float` | `30.0` | `PIAZZA_TIMEOUT` | Request timeout in seconds |
| `retries` | `int` | `3` | `PIAZZA_RETRIES` | Maximum retry attempts |
| `retry_delay` | `float` | `1.0` | `PIAZZA_RETRY_DELAY` | Base delay between retries |
| `cookie_path` | `Path \| None` | `None` | `PIAZZA_COOKIE_PATH` | Path for persisting cookies to disk |
| `encryption_key` | `str \| None` | `None` | `PIAZZA_ENCRYPTION_KEY` | Fernet key for encrypting persisted cookies |

### Environment Variables

`SessionConfig` extends Pydantic's `BaseSettings`, so all fields can be set via environment variables with the `PIAZZA_` prefix. Explicit constructor arguments always take precedence over environment variables.

```bash
# Set environment variables
export PIAZZA_COURSE_ID="your_course_id"
export PIAZZA_TIMEOUT="60"
export PIAZZA_USER_AGENT="my-app/1.0"
```

```python
# Config loads from env vars automatically
from piazza_sdk import SessionConfig

config = SessionConfig()  # course_id picked up from PIAZZA_COURSE_ID
```

## Cookie Persistence

Cookies are saved to and loaded from disk when `cookie_path` is set:

```python
from pathlib import Path
from piazza_sdk import SessionConfig, SessionStateManager

config = SessionConfig(
    course_id="your_course_id",
    cookie_path=Path("~/.piazza/cookies.json"),
)

async with SessionStateManager(config) as session:
    # Cookies are saved to the specified path on close
    # and restored on next session open
    ...
```

Without `cookie_path`, cookies are held in memory only for the session lifetime.

### CSRF Token Persistence

The CSRF token is automatically persisted alongside session cookies. On session restore:

1. The CSRF token is loaded from the cookie jar
2. The `x-csrf-token` header is re-applied to the HTTP client
3. Subsequent API calls carry the restored token

This avoids re-fetching the login page when resuming a session from disk.

### Cookie Encryption

Cookies are encrypted at rest using Fernet symmetric encryption (AES-128-CBC):

```python
from piazza_sdk.adapters.auth import SessionConfig

config = SessionConfig(
    course_id="your_course_id",
    cookie_path=Path("~/.piazza/cookies.json"),
    encryption_key="your-fernet-key",  # Optional, enables encryption
)
```

Generate a key:

```python
from cryptography.fernet import Fernet
key = Fernet.generate_key().decode()
print(key)
```

## Session Lifetime

Sessions auto-refresh before expiration. Default lifetime is 4 hours:

```python
from piazza_sdk import Piazza, SessionConfig, SessionStateManager

config = SessionConfig(course_id="your_course_id")

async with SessionStateManager(config) as session:
    await session.login(email="...", password="...")

    # Session auto-refreshes when nearing expiration
    piazza = Piazza(session)
    classes = await piazza.get_user_classes()
```
