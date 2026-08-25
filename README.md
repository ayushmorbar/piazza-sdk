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
- **Feed operations** - get, filter (unread, following, folder), search
- **Post lifecycle** - create, read, update, delete, follow-ups, answers, replies
- **Scheduled posts** - queue questions/notes for future publishing
- **Private posts** - instructor-only visibility via `feed_groups`
- **Instructor-only follow-ups** and student-perspective (`student_view`) reads
- **Global email preferences** - per-course notification control + bulk opt-out
- **Role permission matrix** - pre-flight capability checks from `user.status`
- **Flexible auth** - interactive prompt login, cookie hand-off, demo (share-link) login
- **User management** - profiles, classes, permissions, `is_ta` enrichment
- **Polymorphic `cid`** - pass `str`, `int`, or `Post` to post operations
- **Announcement & bypass-email posts** - `announcement` + `bypass_email` flags
- **RPC escape hatch** - `RPC.invoke()` for arbitrary API methods
- **Rate limiting** with automatic retry and exponential backoff
- **Comprehensive exception hierarchy** including `NotAuthenticatedError`

## Installation

```bash
pip install piazza-sdk
```

## Quick Start

We have provided a set of comprehensive, runnable tutorials in the `docs/_tutorials/` directory. These scripts are fully documented and show exactly how to use the SDK.

- [01: Getting Started](docs/_tutorials/01_getting_started.py) — Authentication and basic profiles
- [02: Reading the Feed](docs/_tutorials/02_reading_the_feed.py) — Fetching posts and using filters
- [03: Creating & Answering](docs/_tutorials/03_creating_and_answering_posts.py) — Interacting with posts
- [04: Advanced User Stats](docs/_tutorials/04_advanced_user_stats.py) — Course analytics and online users

Here is a quick snippet to fetch your class feed:

```python
import asyncio
from piazza_sdk import Piazza, SessionConfig, SessionStateManager

async def main():
    config = SessionConfig(user_agent="my-app/1.0")
    async with SessionStateManager(config) as session:
        await session.login(email="your@email.com", password="your_password")

        piazza = Piazza(session)
        classes = await piazza.get_user_classes()
        network = piazza.network(classes[0]["nid"])

        feed = await network.get_feed(limit=5)
        for item in feed.feed:
            print(f"{item.subject} ({item.type})")

if __name__ == "__main__":
    asyncio.run(main())
```

## Acknowledgements

Piazza SDK is deeply grateful to the open-source community. Special thanks to [hfaran/piazza-api](https://github.com/hfaran/Piazza-API) for earlier inspirations in navigating the complex Piazza undocumented API layer.

## API

### Core Classes

| Class                | Description                                  |
| -------------------- | -------------------------------------------- |
| `Piazza`             | Entry point - user profile, classes, email preferences |
| `Network`            | Per-class operations - feed, posts, users, scheduling |
| `SessionConfig`      | Configuration (course ID, timeouts, retries) |
| `SessionStateManager`| Async context manager - session lifecycle    |

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

### Scheduling & Private Posts

```python
from datetime import datetime, UTC

# Queue a post for future publishing (returns ScheduledPostConfirmation)
conf = await network.schedule_post(
    title="HW2 released",
    content="<p>Due next Friday.</p>",
    at=datetime(2030, 5, 1, tzinfo=UTC),
    folders=["hw1"],
)
print(conf.draft_id, conf.scheduled)

# Instructor-only post (config.feed_groups)
await network.create_post(
    title="Staff notes",
    content="<p>Internal.</p>",
    folders=["logistics"],
    private_to_staff=True,
)

# Instructor-only follow-up + student-perspective read
await network.create_followup(post_cid, "Staff note", instructor=True)
student_view = await network.get_post(post_cid, student_view=True)
```

### Email Preferences & Capabilities

```python
# Bulk opt-out across every enrolled course
prefs = await piazza.opt_out_of_emails(exclude_nids=["keep_this_nid"])

# Flip a single course; unknown flags preserved via lossless merge
await piazza.set_email_notification(nid, new="no-emails")

# Pre-flight capability checks from the role matrix
info = await network.info()
if await network.can("instructor", "new_post"):
    ...
print(info.resources_url)  # https://piazza.com/{school_ext}/{term}/{num}/home
```

### Authentication Patterns

```python
# Interactive prompt login — omit either argument to be prompted
await session.login()                      # prompts for email + password
await session.login(email="you@x.com")     # prompts for password only

# Cookie hand-off between sessions/processes (plain dict, JSON-safe)
cookies = session.export_cookies()
# ... later, in a fresh process:
async with SessionStateManager(config) as s2:
    s2.import_cookies(cookies)
    alive = await s2.is_session_alive()

# Demo login via "Share Your Class" link (instructors can discover theirs)
info = await piazza.network(nid).info()
print(info.demo_login_url)  # https://piazza.com/demo_login?nid=...&auth=...
async with SessionStateManager(config) as demo:
    await demo.demo_login(auth=info.auth)          # token or full URL
    await demo.demo_login(url=str(share_url))      # exactly one of the two
    feed = await Piazza(demo).network(nid).get_feed(limit=5)
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
