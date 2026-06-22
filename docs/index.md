# Piazza SDK

Modern async Python SDK for Piazza's internal API.

## Features

- **Async-first** — built on `httpx` and `asyncio`
- **Pydantic v2 models** — dot-notation access, full type safety
- **Rich exceptions** — specific error types for every failure mode
- **Automatic retry** — exponential backoff with rate limit detection
- **Session management** — auto-refresh, cookie persistence, Fernet encryption
- **Zero optional dependencies** — everything you need is in `dependencies`

## Quick Start

```bash
pip install piazza-sdk
```

```python
import asyncio
from piazza_sdk import Piazza, SessionConfig, SessionState


async def main():
    config = SessionConfig(course_id="your_course_id")

    async with SessionState(config) as session:
        await session.login(email="you@example.com", password="secret")

        piazza = Piazza(session)
        classes = await piazza.get_user_classes()

        for cls in classes:
            print(cls.name, cls.id)


asyncio.run(main())
```

## Installation

```bash
# From PyPI
pip install piazza-sdk

# From source
git clone https://github.com/ayushmorbar/piazza-sdk.git
cd piazza-sdk
pip install -e ".[dev]"
```

## Links

- [API Reference](api.md)
- [Configuration](configuration.md)
- [Contributing](contributing.md)
- [Changelog](https://github.com/ayushmorbar/piazza-sdk/blob/main/CHANGELOG.md)
- [Security Policy](https://github.com/ayushmorbar/piazza-sdk/blob/main/SECURITY.md)
