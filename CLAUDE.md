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
  _version.py          # Version string (CalVer)
  auth.py              # Backward-compat shim → adapters.auth + adapters.session
  exceptions.py        # Exception hierarchy rooted at PiazzaSDKError
  api/
    rpc.py             # Backward-compat shim → adapters.http.RPC
    piazza.py          # High-level Piazza client (get_user_classes, etc.)
    network.py         # Network-level operations (feed, posts, search)
  adapters/            # Concrete implementations (hexagonal architecture)
    auth.py            # CookieJar, SessionConfig, SessionState
    http.py            # RPC adapter — httpx-backed HTTP client
    session.py         # SessionStateManager adapter
  ports/               # Protocol definitions (hexagonal architecture)
    auth.py            # AuthProtocol, SessionConfigProtocol, TokenStorageProtocol
    http.py            # HTTPClientProtocol, RPCProtocol
    session.py         # SessionManagerProtocol
  domain/              # Standalone business logic (extracted from Network)
    feed.py            # get_feed, get_similar_posts
    posts.py           # create_post, answer_post, endorse, add_tag, etc.
    preferences.py     # get_preferences, update_preferences
    search.py          # search
    statistics.py      # get_statistics
    users.py           # get_all_users, get_instructor_stats, get_online_users
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
  test_network.py      # Network class tests (feed, posts, users, errors)
  test_domain.py       # Domain module tests
  test_adapters_http.py # RPC adapter tests
  test_utils.py        # Utility tests
  test_utils_classification.py  # ActivityClassifier tests
  test_utils_image.py  # Image utility tests
  test_validation.py   # Validation edge case tests
  test_advanced_features.py  # Advanced feature tests
  test_feature_parity.py     # Feature parity tests
```

## Architecture

- **SessionStateManager** — async context manager; owns httpx client lifecycle. Call `.login()` then use `Piazza(session)` for API calls.
- **RPC** — low-level HTTP via httpx. Retries on 429/5xx/timeouts with exponential backoff honoring `Retry-After`; maps HTTP errors to typed exceptions that survive retries (reraise).
- **Models** — Pydantic v2 `BaseModel`. Server-fed models tolerate unknown keys (`extra="ignore"` — live payloads carry extras like `config.feed_groups`); client-side option models stay strict (`extra="forbid"`).
- **Exceptions** — `PiazzaSDKError` base. Subclasses: `AuthenticationError`, `RateLimitError`, `NotFoundError`, `PermissionError`, `ValidationError`, `NetworkError`, `ContentError`, `FeedError`, `UserError`, `SearchError`, `StatisticsError`, `UploadError`, `SessionClosedError`.

## Live API Contracts (verified 2026-08)

See `docs/data-dictionary.md` § "Live-Verified Wire Contracts" before changing
RPC payloads: `content.create` needs `subject` + existing `folders` + string
anonymity; answers use `"i_answer"`/`"s_answer"` + `revision`; deletion returns
`{}` on success; user classes come from `user_profile.get_profile.all_classes`;
unknown methods surface as embedded errors normalized to `NotFoundError`.
- **Hexagonal architecture** — `ports/` defines Protocol interfaces; `adapters/` provides concrete httpx/Fernet/cookie implementations; `domain/` holds standalone async business logic functions extracted from Network.

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
