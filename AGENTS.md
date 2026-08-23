# Agents — Piazza SDK

Instructions for coding agents working on this repository. For Claude-specific guidance, see `CLAUDE.md`.

## Setup

```bash
pip install -e ".[dev]"
```

## Project Overview

Modern async Python SDK for Piazza's internal API. Apache-2.0 licensed.

- **Language**: Python ≥3.11
- **Build**: hatchling (src layout)
- **Runtime deps**: httpx, pydantic v2, cryptography, tenacity, pydantic-settings
- **Dev tools**: ruff, mypy, pytest, pre-commit

## Project Structure

```
src/piazza_sdk/
  __init__.py          # Public API re-exports
  _version.py          # Version string (CalVer)
  auth.py              # Backward-compat shim → adapters.auth + adapters.session
  exceptions.py        # Exception hierarchy rooted at PiazzaSDKError
  api/
    rpc.py             # Backward-compat shim → adapters.http.RPC
    piazza.py          # High-level Piazza client (classes via profile, network factory)
    network.py         # Network-level operations (feed, posts, search)
  adapters/            # Concrete implementations (hexagonal architecture)
    auth.py            # CookieJar, SessionConfig, SessionState
    http.py            # RPC adapter — httpx client, tenacity retries, envelope unwrap
    session.py         # SessionStateManager adapter (CSRF login, refresh, heartbeat)
  ports/               # Protocol definitions (structural contracts)
    auth.py            # AuthProtocol, SessionConfigProtocol, TokenStorageProtocol
    http.py            # HTTPClientProtocol, RPCProtocol
    session.py         # SessionManagerProtocol (incl. handle_auth_error hook)
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
  conftest.py                  # Shared fixtures & env loader
  test_config.py               # PiazzaConfig and SessionConfig tests
  test_exceptions.py           # Exception hierarchy tests
  test_models.py               # Pydantic models, filters, enums, builders
  test_adapters_auth.py        # CookieJar, token storage, encryption
  test_adapters_session.py     # SessionStateManager lifecycle, login, refresh
  test_adapters_http.py        # RPC adapter tests (transport, retries, wrappers)
  test_domain.py               # Pure domain module tests
  test_api_piazza.py           # Piazza client tests (caching, profile, classes)
  test_api_network.py          # Network facade tests (feed, posts, users, search)
  test_utils_normalization.py  # Text and HTML normalization tests
  test_utils_classification.py # ActivityClassifier tests
  test_utils_image.py          # Image processing utility tests
  test_validation.py           # Input validation edge case tests
  test_live.py                 # LIVE tests (-m live; instructor, student, cross-role)
```

## Code Style

- Line length: 100
- Quotes: double
- Imports: isort with `split-on-trailing-comma = false`
- Type hints: always, `mypy --strict` compatible
- Union syntax: `X | None`, not `Optional[X]`
- No bare `except` — catch specific SDK exceptions

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
