# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [CalVer](https://calver.org/) (`YYYY.MM.PATCH`).

## [2026.06.22] - 2026-06-22

### Added

- Initial release of Piazza SDK
- Async Python client for Piazza's internal API
- Pydantic v2 models with dot-notation access
- Feed operations: get, filter (unread, following, folder), search
- Post lifecycle: create, read, update, delete, follow-ups, answers, replies
- User management: profiles, classes, permissions
- Network operations: statistics, user management
- Comprehensive exception hierarchy
- Rate limiting detection and retry with exponential backoff
- SessionConfig with Pydantic Settings
- PEP 561 type stub support (`py.typed` marker)
- CI pipeline with ruff, mypy, and pytest (Python 3.11-3.13)
