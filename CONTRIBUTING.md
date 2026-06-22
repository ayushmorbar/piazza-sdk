# Contributing to Piazza SDK

Thanks for your interest in contributing! This document covers the basics for getting started.

## Development Setup

```bash
# Clone the repo
git clone https://github.com/ayushmorbar/piazza-sdk.git
cd piazza-sdk

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

## Code Quality

All contributions must pass the following checks:

```bash
# Linting
ruff check src/ tests/

# Formatting
ruff format --check src/ tests/

# Type checking
mypy src/

# Tests
pytest
```

### Style Guidelines

- **Line length**: 100 characters max
- **Quotes**: Double quotes
- **Imports**: Sorted via `isort` (through ruff)
- **Type hints**: Required on all function signatures (`disallow_untyped_defs = true`)
- **Trailing commas**: Required on `__all__` arrays and multi-line structures

## Testing

- Tests live in `tests/`
- Use `pytest` with `asyncio_mode = "auto"` (no need to mark `@pytest.asyncio`)
- Mock external network calls — no live API requests in tests
- Aim for tests that are fast, isolated, and deterministic

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure all checks pass (ruff, mypy, pytest)
5. Submit a pull request with a clear description

## Reporting Issues

Open an issue on GitHub with:

- A clear title and description
- Steps to reproduce (if applicable)
- Expected vs actual behavior

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
