# API Reference

## Quick Start

```python
from piazza_sdk import SessionConfig, SessionStateManager, Piazza

config = SessionConfig(course_id="your_course_id")

async with SessionStateManager(config) as session:
    await session.login(email="you@university.edu", password="password")

    piazza = Piazza(session)
    classes = await piazza.get_user_classes()
    network = piazza.network(classes[0]["nid"])

    # Fetch and display the feed
    feed = await network.get_feed(limit=10)
    for item in feed.feed:
        print(f"[{item.type}] {item.subject}")
```

---

## SessionConfig

```python
from piazza_sdk import SessionConfig

config = SessionConfig(
    course_id="your_course_id",
    user_agent="my-app/1.0",
    timeout=30.0,
    retries=3,
    retry_delay=1.0,
    cookie_path=Path("~/.piazza/cookies.json"),
)
```

`SessionConfig` extends Pydantic `BaseSettings` — all fields accept environment variables with the `PIAZZA_` prefix:

```bash
export PIAZZA_COURSE_ID="your_course_id"
export PIAZZA_TIMEOUT="60"
```

::: piazza_sdk.auth.SessionConfig
    options:
      show_source: false

---

## SessionStateManager

The async context manager that owns the HTTP client lifecycle:

```python
async with SessionStateManager(config) as session:
    await session.login(email="user@example.com", password="pass")

    # Session auto-refreshes when nearing expiration
    piazza = Piazza(session)
    classes = await piazza.get_user_classes()
```

### Health Check

Check if the session is still alive without a full refresh:

```python
async with SessionStateManager(config) as session:
    await session.login(email="user@example.com", password="pass")

    # Lightweight liveness check (calls memo.get_unread_message_count)
    alive = await session.is_session_alive()
    if not alive:
        await session.refresh()
```

### Authentication Headers

Get CSRF headers for custom requests:

```python
headers = session.get_auth_headers()
# Returns: {"x-csrf-token": "..."} or {}
```

### Logout

Terminate the session and release resources:

```python
await session.logout()  # Alias for session.close()
```

::: piazza_sdk.adapters.session.SessionStateManager
    options:
      show_source: false
      members:
        - login
        - logout
        - close
        - refresh
        - is_session_alive
        - get_auth_headers
        - needs_refresh
        - client
        - config

---

## Piazza

Top-level client that provides user-level operations and creates `Network` instances:

```python
piazza = Piazza(session)

# List all enrolled classes
classes = await piazza.get_user_classes()

# Get user profile
profile = await piazza.get_user_profile()

# Create a Network for a specific class
network = piazza.network(classes[0]["nid"])
```

::: piazza_sdk.api.piazza.Piazza
    options:
      show_source: false

---

## Network

Per-class operations — feed retrieval, post management, users, search, and statistics.

### Feed

```python
network = piazza.network(nid)

# Get all posts
feed = await network.get_feed(limit=20)

# Get unread posts
unread = await network.get_user_unread_feed(limit=10)

# Get posts by folder
hw_posts = await network.get_folder_contents("Homework 1")

# Get similar posts to an existing one
similar = await network.get_similar_posts(post_id="abc123")
```

### Posts

```python
# Create a new question
result = await network.create_post(
    title="How does async/await work in Python?",
    content="<p>I'm confused about the event loop...</p>",
    post_type="question",
    anonymous=False,
)

# Get full post details
post = await network.get_post(post_id="abc123")
print(post.title, post.author, post.nr)

# Answer a question
await network.answer_post(
    post_id="abc123",
    content="<p>Async/await uses an event loop...</p>",
    instructor_answer=True,
)

# Endorse a post
updated_post = await network.endorse_post(post_id="abc123")

# Resolve a post
await network.resolve_post(post_id="abc123")

# Manage tags
await network.add_tag(post_id="abc123", tag="important")
await network.remove_tag(post_id="abc123", tag="urgent")

# Pin/lock a post
pinned = await network.pin_post(post_id="abc123")
locked = await network.lock_post(post_id="abc123")

# Mark as unread
await network.mark_as_unread(post_id="abc123")

# Delete a post
deleted = await network.delete_post(post_id="abc123")
```

### Users

```python
users = await network.get_users()
online = await network.get_online_users()
stats = await network.get_instructor_stats()
```

### Search & Statistics

```python
# Search posts
results = await network.search(query="exam review")
for item in results.items:
    print(item.title)

# Get network statistics
stats = await network.get_statistics()
print(f"Posts: {stats.posts}, Resolved: {stats.resolved}")
print(f"Resolution rate: {stats.resolution_rate:.0%}")
```

### Drafts & Uploads

```python
# Save a draft
draft_id = await network.save_draft(
    subject="Draft question",
    content="Still working on this...",
    post_type="question",
)

# Upload a file
asset = await network.upload_asset(
    filename="slides.pdf",
    file_data=open("slides.pdf", "rb").read(),
    content_type="application/pdf",
)
print(asset["url"])
```

::: piazza_sdk.api.network.Network
    options:
      show_source: false

---

## Exceptions

All exceptions inherit from `PiazzaSDKError`:

```python
from piazza_sdk import (
    PiazzaSDKError,
    AuthenticationError,
    ContentError,
    FeedError,
    NetworkError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    SearchError,
    StatisticsError,
    UploadError,
    UserError,
    ValidationError,
)

try:
    post = await network.get_post(post_id="invalid")
except NotFoundError:
    print("Post not found")
except RateLimitError:
    print("Rate limited — slow down")
except AuthenticationError:
    print("Session expired — re-authenticate")
except PiazzaSDKError as e:
    print(f"SDK error: {e}")
```

::: piazza_sdk.exceptions
    options:
      show_source: false

---

## Models

### Feed Models

```python
feed = await network.get_feed()
print(f"Total items: {len(feed.items)}")

for item in feed.items:
    print(f"[{item.type}] {item.title} — {item.author}")
```

::: piazza_sdk.models.feed.Feed
    options:
      show_source: false

::: piazza_sdk.models.feed.FeedItem
    options:
      show_source: false

### Post Models

```python
post = await network.get_post(post_id="abc123")

print(f"Title: {post.title}")
print(f"Type: {post.type}")
print(f"Author: {post.author}")
print(f"Views: {post.views}")
print(f"Tags: {post.tags}")

# On-demand normalization: convert HTML content to Markdown
normalized_post = post.normalized()
print(normalized_post.title)  # Clean Markdown text

# Access raw API data
raw_children = post.raw.get("children", [])
```

::: piazza_sdk.models.post.Post
    options:
      show_source: false

::: piazza_sdk.models.post.ChangeLogEntry
    options:
      show_source: false

::: piazza_sdk.models.post.Endorsement
    options:
      show_source: false

### User Models

::: piazza_sdk.models.user.User
    options:
      show_source: false

::: piazza_sdk.models.user.UserPreferences
    options:
      show_source: false

### Network Models

::: piazza_sdk.models.network.NetworkInfo
    options:
      show_source: false

::: piazza_sdk.models.network.Statistics
    options:
      show_source: false

### Enums

::: piazza_sdk.models.enums
    options:
      show_source: false
