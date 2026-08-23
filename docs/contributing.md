# Contributing

Thanks for your interest in contributing to Piazza SDK!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/ayushmorbar/piazza-sdk.git
cd piazza-sdk

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Code Quality

All contributions must pass:

```bash
ruff check src/ tests/         # Linting
ruff format --check src/ tests/ # Formatting
mypy src/                       # Type checking
pytest                          # Tests
```

### Style Guidelines

- **Line length**: 100 characters max
- **Quotes**: Double quotes
- **Imports**: Sorted via `isort` (through ruff)
- **Type hints**: Required on all function signatures (`mypy --strict` compatible)
- **Trailing commas**: Required on `__all__` and multi-line structures
- **Union syntax**: `X | None`, not `Optional[X]`

## Testing

- Tests live in `tests/`
- Use `pytest` with `asyncio_mode = "auto"` (no `@pytest.asyncio` needed)
- Mock external network calls — no live API requests in tests
- Aim for fast, isolated, deterministic tests

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=piazza_sdk --cov-report=term-missing
```

## Project Structure

```
src/piazza_sdk/
  __init__.py          # Public API re-exports
  _version.py          # Version string (CalVer)
  auth.py              # Re-exports from adapters (backward compat)
  exceptions.py        # Exception hierarchy rooted at PiazzaSDKError
  adapters/            # Concrete implementations (hexagonal architecture)
    auth.py            # CookieJar, SessionConfig, SessionState
    http.py            # RPC adapter — httpx-backed HTTP client
    session.py         # SessionStateManager (async context manager)
  ports/               # Protocol definitions (hexagonal architecture)
    auth.py            # AuthProtocol, SessionConfigProtocol, TokenStorageProtocol
    http.py            # HTTPClientProtocol, RPCProtocol
    session.py         # SessionManagerProtocol
  api/                 # High-level API layer
    piazza.py          # Piazza client (get_user_classes, network)
    network.py         # Network operations (feed, posts, search, users)
    rpc.py             # Low-level HTTP transport (retries, error mapping)
  domain/              # Standalone business logic
    feed.py            # get_feed, get_similar_posts
    posts.py           # create_post, answer_post, endorse, add_tag
    search.py          # search
    users.py           # get_all_users, get_instructor_stats
    statistics.py      # get_statistics
    preferences.py     # get_preferences, update_preferences
  models/
    __init__.py        # All model exports
    enums.py           # PostType, UserRole, FeedItemType, etc.
    feed.py            # Feed, FeedItem, filter classes
    post.py            # Post and sub-models (Answer, FollowUp, etc.)
    network.py         # NetworkInfo, Statistics
    user.py            # User, UserPreferences
  utils/
    normalization.py   # HTML/text normalization
    image.py           # Image processing
    classification.py  # Content classification
tests/
  conftest.py          # Shared fixtures
  test_*.py            # Test modules
```

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure all checks pass
5. Submit a pull request with a clear description

## Reporting Issues

Open an issue on GitHub with:

- A clear title and description
- Steps to reproduce (if applicable)
- Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
