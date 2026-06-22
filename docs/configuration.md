# Configuration

All configuration is handled through `SessionConfig`, a Pydantic Settings model.

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

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `course_id` | `str` | — | Piazza course/network ID (required) |
| `user_agent` | `str` | `"piazza-sdk/2026.06.22"` | HTTP User-Agent header |
| `timeout` | `float` | `30.0` | Request timeout in seconds |
| `retries` | `int` | `3` | Maximum retry attempts |
| `retry_delay` | `float` | `1.0` | Base delay between retries |

## Cookie Persistence

Cookies are automatically saved to and loaded from disk when using `SessionState`:

```python
from piazza_sdk import SessionState

async with SessionState(config) as session:
    # Cookies are saved to ~/.piazza/cookies.json on close
    # and restored on next session open
    ...
```

### Cookie Encryption

Cookies are encrypted at rest using Fernet symmetric encryption (AES-128-CBC):

```python
from piazza_sdk.auth import SessionConfig, SessionState

config = SessionConfig(
    course_id="your_course_id",
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
from piazza_sdk.auth import SessionConfig, SessionState

async with SessionState(config) as session:
    await session.login(email="...", password="...")

    # Session auto-refreshes when nearing expiration
    piazza = Piazza(session)
    classes = await piazza.get_user_classes()
```

## Environment Variables

`SessionConfig` supports environment variable overrides via Pydantic Settings:

```bash
export PIAZZA_COURSE_ID="your_course_id"
export PIAZZA_USER_AGENT="my-app/1.0"
```
