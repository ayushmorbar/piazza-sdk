---
title: Testing Patterns
description: Test structure, fixtures, async test patterns, and mock patterns
tags: [testing, pytest, fixtures, mocks, async]
lastUpdated: "2026-06-22"
---

# Testing Patterns

## Test Structure

```
tests/
  conftest.py          # Shared fixtures — import these, don't duplicate
  test_basic.py        # Import smoke tests, model construction
  test_auth_unit.py    # Auth unit tests (mock httpx)
  test_exceptions.py   # Exception hierarchy and repr
  test_smoke.py        # Smoke tests for public API
  test_utils.py        # Utility function tests
  test_validation.py   # Pydantic validation edge cases
```

## Available Fixtures

From `conftest.py`:

| Fixture | Returns | Purpose |
|---------|---------|---------|
| `session_config` | `SessionConfig` | Test credentials |
| `sample_user` | `User` | Pre-built user instance |
| `sample_feed_item` | `FeedItem` | Pre-built feed item |
| `sample_post` | `Post` | Pre-built post |
| `mock_session` | `MagicMock` | Mock session with client, config, needs_refresh, refresh |
| `mock_rpc` | `MagicMock` | Mock RPC with `_request` as AsyncMock |

## Async Tests

```python
# No @pytest.mark.asyncio needed — asyncio_mode = "auto"
async def test_something_async():
    result = await some_async_function()
    assert result is not None
```

## Mock Pattern

```python
from unittest.mock import AsyncMock, MagicMock, patch

async def test_api_call():
    mock_session = MagicMock()
    mock_session.client = AsyncMock()
    mock_session.client.post.return_value = MagicMock(
        status_code=200,
        json=lambda: {"result": "ok"},
    )
    # Test code here
```

## Model Validation Tests

```python
import pytest
from pydantic import ValidationError

def test_model_rejects_bad_data():
    with pytest.raises(ValidationError):
        BadModel(invalid_field="value")
```

## Exception Tests

```python
def test_exception_hierarchy():
    assert issubclass(AuthenticationError, PiazzaSDKError)
    assert issubclass(RateLimitError, PiazzaSDKError)

def test_exception_repr():
    err = AuthenticationError("bad credentials")
    assert "AuthenticationError" in repr(err)
    assert "bad credentials" in repr(err)
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/piazza_sdk --cov-report=term-missing

# Single file
pytest tests/test_basic.py -v

# By keyword
pytest tests/ -k "auth" -v
```

## Coverage Targets

- Minimum: 90% line coverage
- All public API methods must have tests
- All exception classes must have tests
- Error paths must be tested, not just happy paths
