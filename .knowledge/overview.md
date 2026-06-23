---
title: Project Overview
description: Architecture, public API surface, and key models for the Piazza SDK
tags: [overview, architecture, api, models]
lastUpdated: "2026-06-22"
---

# Piazza SDK — Project Overview

## What It Is

A modern async Python SDK for Piazza's internal API. Provides typed access to Piazza classes, posts, feeds, user profiles, and search — all with automatic retries, rate-limit handling, and Pydantic-validated responses.

## Architecture

```
SessionStateManager (async context manager)
  ├── SessionConfig (credentials, base URL)
  ├── SessionState (Enum: logged_out → needs_refresh → logged_in → closed)
  ├── CookieJar (Fernet-encrypted cookie persistence)
  └── Piazza (high-level client)
        ├── get_user_classes()
        ├── get_feed()
        ├── search()
        └── Network (network-level operations)
              ├── get_post()
              ├── create_post()
              ├── get_statistics()
              └── RPC (low-level HTTP)
                    ├── httpx.AsyncClient
                    ├── tenacity retries (429, 5xx)
                    └── Exception mapping
```

## Public API Surface

All re-exported from `src/piazza_sdk/__init__.py`:

- **Auth**: `SessionConfig`, `SessionState`, `SessionStateManager`, `CookieJar`
- **Clients**: `Piazza`, `Network`, `RPC`
- **Models**: `User`, `Post`, `FeedItem`, `FeedFilter`, `Feed`, `NetworkInfo`, `Statistics`
- **Enums**: `UserRole`, `PostType`, `FeedItemType`, `PostTag`, `PostStatus`
- **Exceptions**: `PiazzaSDKError` + 12 subclasses

## Key Models

| Model | Fields | Purpose |
|-------|--------|---------|
| `User` | id, name, email, role, class_ids | Piazza user profile |
| `Post` | id, network_id, type, title, content, author, tags, endorsements, comments | Discussion post |
| `FeedItem` | id, type, post, network_name, course_name, unread | Feed entry |
| `FeedFilter` | network, course, folder, type, tag, unread_only | Feed query filter |
| `NetworkInfo` | id, name, course_number, school, term | Network metadata |
| `Statistics` | posts, resolved, unresolved, users, instructors, students, total_views, total_endorsements, resolution_rate | Network stats |

## Error Hierarchy

```
PiazzaSDKError (base)
├── AuthenticationError
├── NetworkError
├── ValidationError
├── NotFoundError
├── PermissionError
├── RateLimitError
├── ContentError
├── FeedError
├── UserError
├── SearchError
├── StatisticsError
├── SessionClosedError
└── UploadError
```
