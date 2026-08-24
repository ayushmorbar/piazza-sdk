# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [CalVer](https://calver.org/) (`YYYY.MM.DD`).

## [Unreleased]

## [2026.08.24.2] - 2026-08-24

### Added
- Added fail-fast credential validation in `PiazzaConfig` (`course_id`) and `SessionStateManager.login()` (`email` and `password`).
- Configured connection pool limits for `httpx.AsyncClient` (`max_connections=20`, `max_keepalive_connections=5`).
- Injected uniform random jitter into the exponential retry backoff mechanism to prevent thundering herd effects.
- Enhanced embedded error detection (`RPC._check_embedded_error`) to strictly inspect JSON fields (`error`, `status`, `detail`, `message`) before falling back, preventing false-positives on post content.

## [2026.08.24.1] - 2026-08-24

### Added

- Opt-in stealth mode request throttling to mimic human pacing:
  - `PiazzaConfig` fields: `throttle_enabled` (default `False`), `throttle_min_delay` (default `1.0s`), `throttle_max_delay` (default `3.0s`), and `throttle_idle_timeout` (default `30.0s`).
  - Model validator enforcing `throttle_min_delay <= throttle_max_delay`.
  - `RPC._throttle()` with uniform-random delays within the configured bounds, idle reset on browsing gaps (`>= throttle_idle_timeout`), and zero-overhead fast-path when disabled.
- Proactive embedded error detection:
  - `RPC._check_embedded_error()` detects HTTP 200 responses containing embedded error strings (`"not found"`, `"does not exist"`, `"cannot be found"`) in dictionary and stringified payloads, raising typed `NotFoundError`.
  - Normalized error handling in `RPC.call()` across raw error envelopes and nested payload results.
- Comprehensive test coverage for throttling state transitions, idle reset behavior, config validation, and embedded error patterns in unit and live suites.

### Fixed

- `content.answer` now sends the correct wire types — `"i_answer"` for
  instructor answers, `"s_answer"` for student answers — plus the required
  `revision` parameter (previously both branches sent invalid types).
- Pinning uses Piazza's dedicated `content.pin` / `content.unpin` endpoints
  instead of tag manipulation; added `Network.unpin_post`.
- HTTP 429 and 5xx responses are now actually retried with exponential
  backoff honoring `Retry-After` (the documented behavior previously never
  executed); typed exceptions survive retries, preserving `retry_after_ms`
  and `status_code`. Retry attempts/delay are wired to the existing
  `PIAZZA_RETRIES` / `PIAZZA_RETRY_DELAY` config knobs.
- Transport-level typed errors (`RateLimitError`, `AuthenticationError`,
  `NetworkError`) no longer get re-wrapped into domain errors by `_safe_call`,
  so callers retain actionable attributes.
- Double JSON-RPC envelope unwrapping in `Piazza.get_user_classes`,
  `Piazza.get_user_profile`, `Network.get_hall_of_fame`, and unread-count
  parsing (list results were silently coerced to empty).
- `create_post` sends `subject` + string anonymity + default `folders`,
  matching live API requirements (bool anonymity and missing folders were
  rejected server-side).
- Post deletion/resolve success detection handles sparse `{}` responses.
- User classes now derive from `user_profile.get_profile.all_classes` after
  the legacy REST endpoint began returning 404.
- Embedded "Method not found" RPC errors normalize to `NotFoundError`;
  preference reads only fall back to `{}` on that specific condition.
- Server-fed models (`PostConfig`, `Answer`, `PostRevision`) tolerate unknown
  keys present in real payloads (e.g. `config.feed_groups`).
- Cookie jar ignores Set-Cookie attributes when parsing headers; Fernet paths
  raise typed errors instead of asserts; refreshed clients keep identical
  browser-fingerprint headers.
- `iter_all_posts` performs real offset pagination with a stall guard;
  `listen_for_events` bounds remembered event IDs.
- HTML normalization no longer unescapes entities before tag stripping
  (escaped code samples were being corrupted).
- Live tests gated behind a registered `live` marker (deselected by default)
  with credentials read from environment/`.env` instead of hardcoded values.

### Changed

- Hexagonal seams wired: `RPC` accepts `SessionManagerProtocol`, session
  exposes public `handle_auth_error()` recovery hook, protocol docstrings
  corrected (`csrf-token` header name).
- Removed dead code: empty `FernetTokenStorage` class, SearchBuilder compile
  tautologies. Exported `UploadError` and `SessionClosedError` from the
  package root.
- Declared optional `normalization` extra providing `html2text`.
- Documentation synced with implementation: model strictness reality,
  retry semantics, exception list, shim modules, test counts, CalVer scheme.
  Added "Live-Verified Wire Contracts" section to `docs/data-dictionary.md`.

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
- CI pipeline with ruff, mypy, and pytest (Python 3.11-3.14)
