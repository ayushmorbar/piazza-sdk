# Skill: piazza-test

## Purpose

Write, run, and fix tests for the Piazza SDK. All tests use pytest with `asyncio_mode = "auto"`.

## When to Use

- Writing new unit or integration tests
- Fixing failing tests
- Adding test fixtures to `conftest.py`
- Increasing coverage

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

## Writing Tests

### Use fixtures from conftest.py

```python
# Available fixtures:
# session_config  → SessionConfig with test credentials
# sample_user     → User instance
# sample_feed_item → FeedItem instance
# sample_post     → Post instance
# mock_session    → MagicMock with client, config, needs_refresh, refresh
# mock_rpc        → MagicMock with _request AsyncMock
```

### Async test pattern

```python
# No @pytest.mark.asyncio needed — asyncio_mode = "auto"
async def test_something_async():
    result = await some_async_function()
    assert result is not None
```

### Mock pattern

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

### Model validation tests

```python
import pytest
from pydantic import ValidationError

def test_model_rejects_bad_data():
    with pytest.raises(ValidationError):
        BadModel(invalid_field="value")
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

## Checklist

- [ ] Tests use fixtures from `conftest.py` (no duplication)
- [ ] Async tests don't use `@pytest.mark.asyncio` (auto mode)
- [ ] Mocks use `AsyncMock` for async methods
- [ ] Both happy path and error cases covered
- [ ] `pytest tests/ -v` passes
