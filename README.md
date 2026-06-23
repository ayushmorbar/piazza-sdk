# Piazza SDK

> Modern async Python SDK for Piazza's internal API.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![CI](https://img.shields.io/badge/CI-passing-brightgreen.svg)](https://github.com/ayushmorbar/piazza-sdk/actions)

**Disclaimer:** Piazza SDK is an unofficial, community-driven open-source project. It is not affiliated with, endorsed by, or associated with Piazza Technologies, Inc. "Piazza" is a registered trademark of Piazza Technologies, Inc.

## Features

- **Async/await** throughout with `httpx`
- **Pydantic v2** models with dot-notation access
- **Type hints** and PEP 561 `py.typed` marker
- **Feed operations** — get, filter (unread, following, folder), search
- **Post lifecycle** — create, read, update, delete, follow-ups, answers, replies
- **User management** — profiles, classes, permissions
- **Rate limiting** with automatic retry and exponential backoff
- **Comprehensive exception hierarchy** for fine-grained error handling

## Installation

```bash
pip install piazza-sdk
```

## Quick Start

```python
from piazza_sdk import Piazza, SessionConfig, PiazzaSession

async def main():
    config = SessionConfig(
        course_id="your_course_id",
        user_agent="my-app/1.0",
    )

    async with PiazzaSession(config) as session:
        await session.login(email="your@email.com", password="your_password")
        piazza = Piazza(session)

        classes = await piazza.get_user_classes()
        network = piazza.network(classes[0]["nid"])

        feed = await network.get_feed(limit=10)
        for item in feed.feed:
            print(f"{item.subject} ({item.type})")

        post = await network.get_post(feed.feed[0].id)
        print(f"Author: {post.user_name}")

        await network.create_followup(
            post=post,
            content="Great question!",
            anonymous=False,
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

## API

### Core Classes

| Class                | Description                                  |
| -------------------- | -------------------------------------------- |
| `Piazza`             | Entry point — user profile, classes          |
| `Network`            | Per-class operations — feed, posts, users    |
| `SessionConfig`      | Configuration (course ID, timeouts, retries) |
| `SessionStateManager`| Async context manager — session lifecycle    |

### Models

All models support dot-notation access:

```python
post = await network.get_post(cid)
post.id          # str
post.subject     # str
post.type        # PostType
post.created     # datetime
post.user_name   # str
post.tags        # list[str]

# On-demand HTML-to-Markdown normalization
normalized = post.normalized()
print(normalized.subject)  # Clean Markdown text
```

### Filters

```python
from piazza_sdk import UnreadFilter, FollowingFilter, FolderFilter

feed = await network.get_filtered_feed(UnreadFilter())
feed = await network.get_filtered_feed(FolderFilter("homework"))
```

### Error Handling

```python
from piazza_sdk import AuthenticationError, RateLimitError, PiazzaSDKError

try:
    await network.get_post("invalid")
except AuthenticationError:
    print("Check your credentials")
except RateLimitError as e:
    print(f"Rate limited — retry after {e.retry_after_ms}ms")
except PiazzaSDKError as e:
    print(f"SDK error: {e}")
```

### Domain Modules (Advanced)

For hexagonal architecture or standalone use, the `domain` package provides async functions that operate directly on RPC/session objects:

```python
from piazza_sdk.domain import get_feed, create_post, search

feed = await get_feed(rpc, network_id="abc123", limit=10)
post = await create_post(rpc, network_id="abc123", subject="Question", content="...")
results = await search(rpc, network_id="abc123", query="homework")
```

## Development

```bash
git clone https://github.com/ayushmorbar/piazza-sdk.git
cd piazza-sdk
pip install -e ".[dev]"

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/

# Test
pytest
```

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
