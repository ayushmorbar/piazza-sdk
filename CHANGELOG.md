# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [CalVer](https://calver.org/) (`YYYY.MM.DD`).

## [2026.08.26.1] - 2026-08-26

Reference-client parity wave: features ported from `d4l3k/piazza-api` (Go)
and `hfaran/Piazza-API` (Python), each verified against the live Piazza API.

### Added — (2026-08)
- **NotAuthenticatedError + pre-login guard** (`88d3d40`):
  New `NotAuthenticatedError` exception raised when `SessionStateManager.client`
  is accessed before login completes. Replaces the former `SessionClosedError`
  for the `UNAUTHENTICATED` state; `SessionClosedError` is now reserved for
  post-close access only. Guard prevents cryptic httpx "No connection" errors
  at call time.
- **Polymorphic cid** (`fe8938c`): `_coerce_cid()` accepts `str | int | Post`
  and is wired into all four domain content functions that take a thread ID
  (`resolve_post`, `unresolve_post`, `add_endorsement`, `add_tag`). Booleans
  are explicitly rejected with `TypeError`.
- **is_ta enrichment in get_user_classes** (`7034b42`):
  `get_user_classes()` now enriches each class dict with an `is_ta` boolean
  derived from the user's `prof_hash` in `user.status`. Enrichment is
  silently skipped on API failure; returns no classes when profile unavailable.
- **Interactive prompt login** (`8c7bf44`): `login()` now accepts
  `email=None`/`password=None` and prompts on the terminal (`input`,
  `getpass`) — hfaran-client CLI parity for REPLs and scripts.
- **Demo login** (`0bf3bfa`): `SessionStateManager.demo_login(auth=|url=)`
  authenticates via "Share Your Class" links (XOR contract; `ValidationError`
  when both/neither given).
  - Live-discovered wire contract: invalid/expired share links return
    **HTTP 404** while still setting an anonymous `session_id` cookie —
    non-200 responses raise `AuthenticationError`.
  - Positive path live-verified: real token grants `piazza_session`
    cookies, CSRF is acquired, and the demo session reads the feed via
    `network.get_my_feed`.
  - `NetworkInfo.auth` + `NetworkInfo.demo_login_url` surface the share
    token parsed from `user.status networks[]`, closing the loop:
    instructor discovers link → anonymous session adopts it.
  - Known limitation: `is_session_alive()` returns `False` for demo users
    — `memo.get_unread_message_count` is outside demo scope.
- **Cookie dict export/import** (`b28c69b`):
  `CookieJar.export_dict()/import_dict()` +
  `SessionStateManager.export_cookies()/import_cookies()` for plain-dict
  hand-off between sessions/processes; import transitions an active
  UNAUTHENTICATED session to AUTHENTICATED. Live-verified: export → fresh
  session → import → class page reachable without re-login.
- **Login hardening** (`892f1ec`):
  - CSRF token now acquired from the dedicated `GET /main/csrf_token`
    endpoint (JS-assignment parse), with the legacy login-page `<meta>`
    scrape kept as automatic fallback.
  - Failed logins surface the server's inline `var ERROR_MSG` text
    verbatim in `AuthenticationError` (e.g. "Email or password incorrect").
- **Scheduled posts** (`dfbf3f3`): two-step wire flow via
  `network.save_draft` → `content.create(draftId, config.schedule_later*)`.
  - New `RPC.network_save_draft` (scalar-preserving: the endpoint returns
    the draft ID as a *bare string*).
  - New domain `schedule_post()` + `Network.schedule_post()` accepting
    `datetime` or unix-millisecond targets; polls rejected upstream.
  - New `ScheduledPostConfirmation` model — live API confirms
    `{"scheduled": true}` with **no post ID** until publish time.
- **Private posts to staff** (`7f867bf`):
  `create_post(private_to_staff=True)` resolves your user ID and injects
  `config.feed_groups = "instr_{nid},{uid}"`; pass `author_uid=` to skip
  the profile round-trip. Caller-supplied `config` keys are preserved.
  - `RPC.network_id` property added (declared by `RPCProtocol` but
    previously unimplemented on the adapter — caught by live read-back).
- **Instructor-only follow-ups** (`6970384`):
  `add_followup(instructor=True)` injects `config.ionly=true` plus the
  rich-text editor marker; caller `config` keys win over defaults.
- **student_view reads** (`6970384`):
  `RPC.content_get(student_view=)` / `Network.get_post(student_view=True)`
  render the student-visible view from staff accounts; param omitted when
  unset.

### Added — (2026-08)
- **Global email preferences** (`d1b35a5`): `user.update` support with
  lossless raw-dict read-modify-write.
  - New models: `EmailPrefEntry` (`auto_follow` is bool-or-string on the
    wire); new RPC `user_update`; domain `get_email_preferences`,
    `set_email_notification`, `opt_out_of_emails(exclude_nids, keep_careers)`;
    facade equivalents on `Piazza`.
- **Network info + role permission matrix** (`93457ea`):
  - New server-fed models `RolePermissions`, `NetworkRoles`,
    `ClassSections`, `NetworkConfig`; `NetworkInfo` relaxed to
    `extra="ignore"` and extended with `school_ext`, `short_number`,
    `anonymity`, `auto_join`, `config`, a `resources_url` property, and a
    `can(role, action)` pre-flight capability check.
  - Domain `parse_network_entry` / `get_network_info`;
    `Network.info()` (cached) + `Network.can()`.
- **Content utilities** (`621fc7e`):
  - `Post.iter_content()` — iterative depth-first walk yielding every
    revision body across the whole child tree; live-corrected fallback
    chain history → content → subject (children carry no history;
    follow-ups store text in `subject`).
  - `utils.extract_urls()` — order-preserving xurls-equivalent extraction.

### Fixed
- Network-scoped RPC payloads normalized (`7e2f38b`): late-added helpers
  (`content.bookmark/unbookmark/mark_favorite/mark_unfavorite/view/edit/
  remove_feedback/del_item/get_users`) now carry `nid` + `aid` like legacy
  methods; `content.cancel_edit` nid is optional (defaults to instance);
  parametrized payload-shape test table added.
- `update_user_preferences` no longer launders typed SDK errors into
  `UserError` — `status_code`/`retry_after_ms` survive (`7e2f38b`).

### Documented
- Live-verified wire contracts recorded in `docs/data-dictionary.md`
  (`336d1d1`, this release): global email prefs map + `career` key,
  five-role matrix incl. `student.can_post_anonymous_all`, resources URL
  shape, child payload shapes, scheduled-post flow failure modes ("Missing
  parameter: draft", "Save as draft first"), private-post `feed_groups`
  contract, instructor follow-up `ionly`, and `student_view`.

## [2026.08.25.1] - 2026-08-25

### Added
- `Network.unresolve_post(post_id)` — reverse a post's resolved status via `content.update(status="active")`.
- `Post.is_upvoted` property — returns `True` when `is_tag_good` or `is_tag_endorse` is truthy in the raw payload.
- Fixed `domain/posts.py` `__all__` — now exports all 26 domain functions (was missing 9 + the new `unresolve_post`).
- Enriched docstrings with runnable ```` ```python ```` code examples for `resolve_post`, `unresolve_post`, `is_upvoted`, `content_mark_resolved`, and `content_resolve`.
- Live verification: `test_dual_role_complete_lifecycle` now exercises `unresolve_post` and `is_upvoted` against the real Piazza API.
- Extensive HAR forensic parity alignments across data models:
  - `Child` model expanded to track answer-level endorsements (`is_tag_endorse`, `tag_endorse`, `tag_endorse_arr`).
  - `FeedItem` model now tracks answer presence booleans (`has_i` for instructor, `has_s` for student).
  - 6 newly typed feed filter subclasses added: `UnansweredFilter`, `UnresolvedFilter`, `HideGroupPostsFilter`, `InstructorsFilter`, `MyPostsFilter`, `DueFilter`.
  - `User` model now strictly auto-coerces `all_classes` network ID dictionary payloads to standardized `list[dict]`.

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
