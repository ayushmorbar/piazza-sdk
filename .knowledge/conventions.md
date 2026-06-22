---
title: Coding Conventions
description: Python style, Pydantic v2 patterns, async patterns, and exception handling
tags: [conventions, style, pydantic, async, exceptions]
lastUpdated: "2026-06-22"
---

# Coding Conventions

## Python Style

- **Version**: Python ≥3.11
- **Line length**: 100
- **Quotes**: double
- **Imports**: isort with `split-on-trailing-comma = false`
- **Type hints**: always, `mypy --strict` compatible
- **Union syntax**: `X | None`, not `Optional[X]`
- **Type aliases**: `type X = ...` (Python 3.12 syntax)

## Pydantic v2 Patterns

```python
from pydantic import BaseModel, ConfigDict, Field

class MyModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    name: str = Field(..., description="The name")
    count: int = Field(default=0, ge=0)
```

- Always `ConfigDict`, never `model_config = {"extra": "forbid"}`
- Always `Field(...)` with description for required fields
- No v1 patterns (`validator`, `root_validator`, `Optional[X]`)

## Async Patterns

```python
# Async context manager for session lifecycle
async with SessionStateManager(config) as session:
    client = Piazza(session)
    result = await client.get_user_classes()

# All I/O is async def
async def get_user(self, user_id: str) -> User: ...

# Never block in async context
# Use asyncio.to_thread for sync I/O
result = await asyncio.to_thread(sync_function, arg)
```

## Exception Handling

```python
# Always raise typed SDK exceptions
from piazza_sdk.exceptions import AuthenticationError, RateLimitError

if response.status_code == 401:
    raise AuthenticationError(f"Login failed: {response.text}")
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", "5")) * 1000
    raise RateLimitError(retry_after_ms=retry_after)

# Never catch bare Exception
# Bad:  except Exception:
# Good: except AuthenticationError:
```

## Constants

```python
# Module-level, not inline
MAX_RETRIES = 3
_RETRY_WAIT_MIN = 1.0
_RETRY_WAIT_MAX = 30.0
_DEFAULT_TIMEOUT = 30.0
```

## Naming

- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`
- Type aliases: `PascalCase` or `snake_case` (follow existing pattern)

## Docstrings

- Google-style docstrings
- Required for all public methods
- Include Args, Returns, Raises sections

```python
async def get_user(self, user_id: str) -> User:
    """Fetch a user by ID.

    Args:
        user_id: The Piazza user ID.

    Returns:
        User object with profile data.

    Raises:
        NotFoundError: If user does not exist.
        AuthenticationError: If session is invalid.
    """
```
