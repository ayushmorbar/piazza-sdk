# Piazza SDK — Agent Instructions

Modern async Python SDK for Piazza's internal API. Apache-2.0 licensed.

## Quick Commands

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint + typecheck
ruff check src/ tests/
mypy src/

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src/piazza_sdk --cov-report=term-missing
```

## Project Structure

```
src/piazza_sdk/
  __init__.py          # Public API re-exports
  _version.py          # Version string
  auth.py              # SessionConfig, CookieJar, SessionStateManager
  exceptions.py        # Exception hierarchy rooted at PiazzaSDKError
  api/
    rpc.py             # Low-level HTTP client (tenacity retries, error mapping)
    piazza.py          # High-level Piazza client (get_user_classes, etc.)
    network.py         # Network-level operations (feed, posts, search)
  models/
    enums.py           # StrEnum types (UserRole, PostType, FeedItemType, etc.)
    feed.py            # FeedItem, FeedFilter, Feed, filter models
    post.py            # Post, ChangeLogEntry, Endorsement
    network.py         # NetworkInfo, Statistics
    user.py            # User
  utils/
    normalization.py   # HTML/text normalization
    image.py           # Image processing
    classification.py  # Content classification

tests/
  conftest.py          # Shared fixtures (session_config, sample_*, mock_*)
  test_basic.py        # Import and model validation tests
  test_auth_unit.py    # Auth unit tests
  test_exceptions.py   # Exception hierarchy tests
  test_smoke.py        # Smoke tests
  test_utils.py        # Utility tests
  test_validation.py   # Validation edge case tests
```

## Architecture

- **SessionStateManager** — async context manager; owns httpx client lifecycle. Call `.login()` then use `Piazza(session)` for API calls.
- **RPC** — low-level HTTP via httpx. Retries on 429/5xx with exponential backoff. Maps HTTP errors to typed exceptions.
- **Models** — Pydantic v2 `BaseModel` with `model_config = ConfigDict(strict=True, extra="forbid")`. All fields typed.
- **Exceptions** — `PiazzaSDKError` base. Subclasses: `AuthenticationError`, `RateLimitError`, `NotFoundError`, `PermissionError`, `ValidationError`, `NetworkError`, `ContentError`, `FeedError`, `UserError`, `SearchError`, `StatisticsError`.

## Coding Rules

1. **Python ≥3.11** — use `type X = ...` type aliases, `X | None` unions, `match` statements where clear.
2. **Async-first** — all I/O is `async def`. Never block in async context.
3. **Pydantic v2** — `BaseModel`, `ConfigDict`, `Field`. No v1 patterns.
4. **Type hints** — `mypy --strict`-compatible. `disallow_untyped_defs = true`.
5. **Ruff** — line length 100, double quotes, isort with `split-on-trailing-comma = false`.
6. **No magic numbers** — extract constants to module level.
7. **Error handling** — always raise typed SDK exceptions, not bare `Exception`.
8. **Tests** — `pytest-asyncio` with `asyncio_mode = "auto"`. Use fixtures from `conftest.py`.

## Before Committing

```bash
ruff check src/ tests/
mypy src/
pytest tests/ -v
```

All three must pass cleanly.
