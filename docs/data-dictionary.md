# Data Dictionary — Piazza SDK

Complete reference for all data models, enumerations, exceptions, protocols, and their relationships.

---

## Table of Contents

- [Enumerations](#enumerations)
- [Post Models](#post-models)
- [Feed Models](#feed-models)
- [User Models](#user-models)
- [Network Models](#network-models)
- [Session & Auth Models](#session--auth-models)
- [Exception Hierarchy](#exception-hierarchy)
- [Protocol Definitions](#protocol-definitions)
- [Parsing Model (JSON → Pydantic)](#parsing-model-json--pydantic)

---

## Enumerations

All enumerations inherit from `StrEnum` (string-valued) unless noted. Defined in `src/piazza_sdk/models/enums.py`.

### PostType

| Value | String | Description |
|-------|--------|-------------|
| `NOTE` | `"note"` | Informational post |
| `QUESTION` | `"question"` | Question post (answerable) |
| `POLL` | `"poll"` | Poll post |

### PostStatus

| Value | String | Description |
|-------|--------|-------------|
| `ACTIVE` | `"active"` | Post is open and active |
| `RESOLVED` | `"resolved"` | Post has been resolved |
| `SUPERSEDED` | `"superseded"` | Post has been superseded by another |

### ChangeType

| Value | String | Description |
|-------|--------|-------------|
| `CREATE` | `"create"` | Post was created |
| `FOLLOWUP` | `"followup"` | Follow-up was added |
| `FEEDBACK` | `"feedback"` | Feedback was given |
| `INSTRUCTOR_ANSWER` | `"i_answer"` | Instructor posted an answer |
| `STUDENT_ANSWER` | `"s_answer"` | Student posted an answer |

### Visibility

| Value | String | Description |
|-------|--------|-------------|
| `PUBLIC` | `"public"` | Visible to everyone |
| `PRIVATE` | `"private"` | Visible only to author |
| `GROUP` | `"group"` | Visible to a group |
| `INSTRUCTORS_ONLY` | `"instructors_only"` | Visible only to instructors |

### AnonymityLevel

| Value | String | Description |
|-------|--------|-------------|
| `NO` | `"no"` | Not anonymous |
| `YES` | `"yes"` | Anonymous to students |
| `FULL` | `"full"` | Fully anonymous |

### UserRole

| Value | String | Description |
|-------|--------|-------------|
| `STUDENT` | `"student"` | Student role |
| `INSTRUCTOR` | `"instructor"` | Instructor role |
| `TA` | `"ta"` | Teaching assistant role |
| `ADMIN` | `"admin"` | Administrator role |

### FeedItemType

| Value | String | Description |
|-------|--------|-------------|
| `NOTE` | `"note"` | Note-type feed item |
| `QUESTION` | `"question"` | Question-type feed item |
| `POLL` | `"poll"` | Poll-type feed item |
| `UNKNOWN` | `"unknown"` | Unrecognized type |

### FeedItemDefaultAnonymity

| Value | String | Description |
|-------|--------|-------------|
| `NO` | `"no"` | Not anonymous by default |
| `YES` | `"yes"` | Anonymous by default |
| `FULL` | `"full"` | Fully anonymous by default |
| `UNKNOWN` | `"unknown"` | Unknown default |

### FeedSortOrder

| Value | String | Description |
|-------|--------|-------------|
| `UPDATED` | `"updated"` | Sort by last updated |
| `CREATED` | `"created"` | Sort by creation time |

### NotificationType

| Value | String | Description |
|-------|--------|-------------|
| `FOLLOWUP` | `"followup"` | New follow-up notification |
| `ANSWER` | `"answer"` | New answer notification |
| `ENDORSEMENT` | `"endorsement"` | Endorsement notification |
| `MENTION` | `"mention"` | Mention notification |

### FolderType

| Value | String | Description |
|-------|--------|-------------|
| `INBOX` | `"inbox"` | Inbox folder |
| `OUTBOX` | `"outbox"` | Outbox folder |
| `STUDENT` | `"student"` | Student folder |
| `PINNED` | `"pinned"` | Pinned folder |
| `FOLDERS` | `"folders"` | All folders |

### SortField

| Value | String | Description |
|-------|--------|-------------|
| `UPDATED` | `"updated"` | Sort by update time |
| `CREATED` | `"created"` | Sort by creation time |
| `ACTIVITY` | `"activity"` | Sort by activity level |

### ResponseFormat

| Value | String | Description |
|-------|--------|-------------|
| `JSON` | `"json"` | JSON response format |
| `HTML` | `"html"` | HTML response format |
| `TEXT` | `"text"` | Plain text response format |

---

## Post Models

### Post

The central model representing a Piazza post. Defined in `src/piazza_sdk/models/post.py`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | **required** | Unique post identifier (e.g. `j5yj4g5d4p2qg3`) |
| `type` | `PostType` | `PostType.NOTE` | Post type (question, note, poll) |
| `title` | `str` | `""` | Post title/subject line |
| `subject` | `str` | `""` | Alternative subject text |
| `author` | `str` | `""` | Author's email or user identifier |
| `created_at` | `datetime \| None` | `None` | Timestamp when the post was created |
| `updated_at` | `datetime \| None` | `None` | Timestamp of the last update |
| `nr` | `int` | `0` | Numeric post number within the network |
| `raw` | `dict[str, Any]` | `{}` | Raw API response dict for advanced use cases |
| `tags` | `list[str]` | `[]` | List of user-defined tags |
| `folder` | `str` | `""` | Folder name the post belongs to |
| `status` | `PostStatus` | `PostStatus.ACTIVE` | Post lifecycle status |
| `views` | `int` | `0` | Total view count |
| `unique_views` | `int \| None` | `None` | Unique viewer count |
| `students` | `list[StudentInfo]` | `[]` | Student participant info |
| `followups` | `list[FollowUp]` | `[]` | Follow-up questions/comments |
| `answers` | `list[Answer]` | `[]` | Answer posts |
| `change_log` | `list[ChangeLogEntry]` | `[]` | Edit history entries |
| `endorsements` | `list[Endorsement]` | `[]` | Endorsement/upvote records |
| `config` | `PostConfig` | `PostConfig()` | Post configuration |
| `children` | `list[Child]` | `[]` | Child items (answers, follow-ups, comments) |
| `user_name` | `str` | `""` | Display name of the author |
| `visibility` | `Visibility` | `Visibility.PUBLIC` | Access level |
| `revisions` | `list[PostRevision]` | `[]` | Full revision history |

**ConfigDict**: `slots=True, extra="forbid"`

**Computed Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `is_question` | `bool` | `True` if `type == PostType.QUESTION` |
| `is_resolved` | `bool` | `True` if `status == PostStatus.RESOLVED` |
| `total_votes` | `int` | Sum of endorsements across all answers |
| `answer_count` | `int` | Number of answers |
| `followup_count` | `int` | Number of follow-ups |
| `student_answer` | `Child \| None` | First child with `type == "s_answer"` |
| `instructor_answer` | `Child \| None` | First child with `type == "i_answer"` |

**Methods**:

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `normalized` | `() -> Post` | `Post` | Returns a new Post with HTML content normalized to Markdown |

---

### Endorsement

Represents an endorsement/upvote on a post or answer.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `role` | `str` | `""` | Endorser's role (e.g. student, instructor) |
| `name` | `str` | `""` | Endorser display name |
| `endorser` | `str \| None` | `None` | Endorser user ID, or None if anonymous |
| `admin` | `bool` | `False` | Whether the endorser is a network admin |
| `photo` | `str \| None` | `None` | Endorser photo path, if available |
| `id` | `str` | `""` | Endorsement record identifier |
| `photo_url` | `str \| None` | `None` | Full URL to the endorser's photo |
| `published` | `bool` | `False` | Whether the endorsement is published |
| `us` | `bool` | `False` | Whether the endorser is a course staff member |
| `facebook_id` | `str \| None` | `None` | Facebook ID of the endorser, if linked |

**ConfigDict**: `slots=True, extra="forbid"`

---

### Answer

Represents an answer to a post.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `""` | Unique identifier for this answer |
| `uid` | `str` | `""` | Author's user ID |
| `content` | `str` | `""` | Answer body content (HTML) |
| `created` | `datetime \| None` | `None` | Timestamp when the answer was posted |
| `updated` | `datetime \| None` | `None` | Timestamp when the answer was last edited |
| `votes` | `int` | `0` | Number of votes/endorsements on this answer |
| `endorsements` | `list[Endorsement]` | `[]` | List of endorsement records |
| `is_instructor_answer` | `bool` | `False` | Whether the author is an instructor |
| `is_student_answer` | `bool` | `False` | Whether the author is a student |
| `rated` | `bool` | `False` | Whether the current user has rated this answer |
| `folder` | `str` | `""` | Folder assignment for this answer |

**ConfigDict**: `slots=True, extra="forbid"`

---

### Child

Represents a child element (follow-up, answer, or comment) attached to a post.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `""` | Unique identifier for this child element |
| `type` | `str` | `""` | Element type (e.g. `followup`, `answer`, `i_answer`, `s_answer`) |
| `subject` | `str` | `""` | Child subject line |
| `content` | `str` | `""` | Child body content (HTML) |
| `uid` | `str` | `""` | Author's user ID |
| `created` | `datetime \| None` | `None` | Timestamp when the child was posted |
| `updated` | `datetime \| None` | `None` | Timestamp when the child was last edited |
| `anon` | `AnonymityLevel` | `AnonymityLevel.NO` | Anonymity level of the author |
| `no_answer` | `bool` | `False` | Whether this follow-up has no answer yet |
| `followed` | `bool` | `False` | Whether the current user is following this element |

**ConfigDict**: `slots=True, extra="forbid"`

---

### FollowUp

Represents a follow-up question or comment on a post.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `""` | Unique identifier for this follow-up |
| `uid` | `str` | `""` | Author's user ID |
| `subject` | `str` | `""` | Follow-up subject line |
| `content` | `str` | `""` | Follow-up body content (HTML) |
| `created` | `datetime \| None` | `None` | Timestamp when the follow-up was posted |
| `updated` | `datetime \| None` | `None` | Timestamp when the follow-up was last edited |
| `anon` | `AnonymityLevel` | `AnonymityLevel.NO` | Anonymity level of the author |

**ConfigDict**: `slots=True, extra="forbid"`

---

### ChangeLogEntry

Represents a single entry in the post's edit history.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `anon` | `AnonymityLevel` | `AnonymityLevel.NO` | Anonymity level of the change author |
| `uid` | `str` | `""` | User ID of the person who made the change |
| `data` | `str \| None` | `None` | Free-form data associated with the change |
| `to` | `str \| None` | `None` | Target value after the change, if applicable |
| `v` | `Visibility` | `Visibility.PUBLIC` | Visibility of the change record |
| `type` | `ChangeType` | `ChangeType.CREATE` | Type of change (create, update, endorse, etc.) |
| `when` | `datetime \| None` | `None` | Timestamp when the change occurred |
| `cid` | `str` | `""` | Child element ID the change relates to, if any |

**ConfigDict**: `slots=True, extra="forbid"`

---

### PostRevision

Represents a single revision of a post's content.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `revision` | `int` | `0` | Sequential revision number |
| `subject` | `str` | `""` | Subject line at this revision |
| `content` | `str` | `""` | Body content at this revision (HTML) |
| `uid` | `str` | `""` | User ID of the editor |
| `created` | `datetime \| None` | `None` | Timestamp when this revision was created |

**ConfigDict**: `slots=True, extra="forbid"`

---

### StudentInfo

Represents a student participant in a post.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `uid` | `str` | `""` | Student's user ID |
| `name` | `str` | `""` | Student display name |
| `email` | `str` | `""` | Student email address |
| `role` | `str` | `""` | Student role string |

**ConfigDict**: `slots=True, extra="forbid"`

---

### PublishingOptions

Configuration options for publishing a post.

| Field | Type | Default | Alias | Description |
|-------|------|---------|-------|-------------|
| `bypass_email` | `bool` | `False` | — | Skip sending email notifications |
| `silent_update` | `bool` | `False` | `no_up_notify` | Skip updated-post notifications |
| `anonymity` | `Literal["no", "stud", "all"]` | `"no"` | — | Anonymity level |

**ConfigDict**: `slots=True, populate_by_name=True, extra="forbid"`

**Serializers**: `bypass_email` and `silent_update` serialize `bool → int` (0/1).

**Methods**:

| Method | Returns | Description |
|--------|---------|-------------|
| `to_kwargs()` | `dict[str, Any]` | Converts to RPC parameter dict: `{"options[bypass_email]": int, "options[no_up_notify]": int, "options[anonymous]": str}` |

---

### PostConfig

Post-level configuration metadata.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `""` | Configuration name or label |
| `instructor_note` | `str` | `""` | Note from the instructor, if set |
| `created` | `str` | `""` | Timestamp when the configuration was created |

**ConfigDict**: `slots=True, extra="forbid"`

---

### PostCreatedResponse

Response from creating a new post or follow-up.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | **required** | New post or follow-up ID |

**ConfigDict**: `slots=True, extra="forbid"`

---

### AssetUploadResponse

Response from uploading an asset.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | **required** | Asset identifier |
| `url` | `str \| None` | `None` | Pre-signed upload URL |

**ConfigDict**: `slots=True, extra="forbid"`

---

## Feed Models

### FeedItem

A lightweight representation of a post in the feed listing.

| Field | Type | Default | Alias | Description |
|-------|------|---------|-------|-------------|
| `id` | `str` | **required** | — | Unique post identifier |
| `subject` | `str` | `""` | — | Post title/subject line |
| `type` | `FeedItemType \| str` | `FeedItemType.UNKNOWN` | — | Feed item type |
| `created` | `datetime \| None` | `None` | — | When the post was created |
| `updated` | `datetime \| None` | `None` | — | When the post was last updated |
| `default_anonymity` | `FeedItemDefaultAnonymity \| str` | `FeedItemDefaultAnonymity.UNKNOWN` | — | Default anonymity setting |
| `uid` | `str` | `""` | — | Author user ID |
| `folder` | `str` | `""` | — | Folder name |
| `no_answer` | `bool` | `False` | — | Whether post has no answers |
| `is_pinned` | `bool` | `False` | `pin` | Whether post is pinned |
| `follows` | `bool` | `False` | — | Whether current user is following |
| `viewed` | `bool` | `True` | — | Whether current user has viewed |
| `reputation` | `int` | `0` | — | Author reputation score |
| `badge` | `str` | `""` | — | Author badge or role indicator |
| `tags` | `list[str]` | `[]` | — | Post tags |
| `content_snippet` | `str \| None` | `None` | `content_snipet` | Short content preview |

**ConfigDict**: `slots=True, populate_by_name=True, extra="forbid"`

**Computed Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `is_question` | `bool` | `True` if `type == FeedItemType.QUESTION` |

---

### Feed

A paginated collection of feed items.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `feed` | `list[FeedItem]` | `[]` | List of feed items |
| `total` | `int` | `0` | Total number of items available |
| `page` | `int` | `1` | Current page number |
| `page_size` | `int` | `50` | Number of items per page |

**ConfigDict**: `slots=True, extra="forbid"`

---

### FeedFilter (Base Class)

Base class for feed filtering. No fields. Subclasses implement `to_kwargs()`.

---

### UnreadFilter

Filters feed to show only unread posts.

| Inherits | `FeedFilter` |
|----------|--------------|
| **Fields** | (none) |

**`to_kwargs()`** → `{"updated": True}`

---

### FollowingFilter

Filters feed to show only posts the user follows.

| Inherits | `FeedFilter` |
|----------|--------------|
| **Fields** | (none) |

**`to_kwargs()`** → `{"following": True}`

---

### FolderFilter

Filters feed by folder name.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `folder_name` | `str` | `""` | Name of the folder to filter by |

**ConfigDict**: `slots=True, extra="forbid"`

**`to_kwargs()`** → `{"folder": True, "filter_folder": self.folder_name}`

---

### SearchFilter

Filters and sorts feed by search criteria.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | `str` | `""` | Search query string |
| `folder` | `str` | `""` | Folder name to restrict the search to |
| `tag` | `str` | `""` | Tag to filter by |
| `instructor` | `str` | `""` | Instructor name to filter by |
| `student` | `str` | `""` | Student name to filter by |
| `sort` | `str` | `"relevance"` | Sort order string |
| `limit` | `int` | `50` | Maximum number of results |
| `offset` | `int` | `0` | Number of results to skip |

**ConfigDict**: `slots=True, extra="forbid"`

**`to_kwargs()`** → dict with keys: `search`, `search_query`, `filter_folder`, `filter_tag`, `filter_instructor`, `filter_student`, `sort`, `limit`, `offset` (only non-default values included)

---

### SortFilter

Sorts feed by a specific order.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `order` | `FeedSortOrder` | `FeedSortOrder.UPDATED` | Sort order (updated or created) |

**ConfigDict**: `slots=True, extra="forbid"`

**`to_kwargs()`** → `{"sort": self.order.value}`

---

### SearchBuilder

Fluent builder for constructing `SearchFilter` instances. Not a Pydantic model.

| Method | Parameter | Returns | Description |
|--------|-----------|---------|-------------|
| `with_query` | `text: str` | `SearchBuilder` | Set the search query |
| `in_folder` | `folder_name: str` | `SearchBuilder` | Restrict to folder |
| `limit` | `count: int` | `SearchBuilder` | Set result limit |
| `offset` | `count: int` | `SearchBuilder` | Set result offset |
| `compile` | — | `SearchFilter` | Build and return the filter |

---

## User Models

### User

Represents a user in a Piazza network.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | **required** | Unique user identifier |
| `name` | `str` | `""` | User's display name |
| `email` | `str` | `""` | User's email address |
| `role` | `UserRole` | `UserRole.STUDENT` | User's primary role |
| `is_instructor` | `bool` | `False` | Whether user is an instructor |
| `is_student` | `bool` | `True` | Whether user is a student |
| `is_ta` | `bool` | `False` | Whether user is a teaching assistant |
| `is_admin` | `bool` | `False` | Whether user is an admin |
| `class_roles` | `dict[str, str]` | `{}` | Mapping of network ID to role string |

**ConfigDict**: `slots=True, extra="forbid"`

**Methods**:

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `get_classes_by_role` | `(role: str) -> list[str]` | `list[str]` | Returns network IDs where the user has the specified role |

---

### UserPreferences

User notification and display preferences.

| Field | Type | Default | Validators | Description |
|-------|------|---------|------------|-------------|
| `digest_frequency` | `str` | `"daily"` | — | Email digest frequency (`real_time`, `daily`, `weekly`, `never`) |
| `digest_hour` | `int` | `9` | `ge=0, le=23` | Hour of day (0-23) to send digest emails |
| `email_new_post` | `bool` | `True` | — | Email on new posts |
| `email_new_followup` | `bool` | `True` | — | Email on new follow-ups |
| `email_new_answer` | `bool` | `True` | — | Email on new answers |
| `email_new_comment` | `bool` | `False` | — | Email on new comments |
| `push_new_post` | `bool` | `True` | — | Push-notify on new posts |
| `push_new_followup` | `bool` | `True` | — | Push-notify on new follow-ups |
| `push_new_answer` | `bool` | `True` | — | Push-notify on new answers |
| `show_student_names` | `bool` | `True` | — | Show student names publicly |

**ConfigDict**: `slots=True, populate_by_name=True, extra="forbid"`

---

## Network Models

### NetworkInfo

Metadata about a Piazza network/course.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `""` | Piazza network identifier (numeric string) |
| `nid` | `str` | `""` | Network ID used in API URLs |
| `name` | `str` | `""` | Display name for the course |
| `course_number` | `str` | `""` | Course catalog number (e.g. CS 101) |
| `course_title` | `str` | `""` | Full course title |
| `instructor` | `str` | `""` | Primary instructor name |
| `term` | `str` | `""` | Academic term (e.g. Fall) |
| `year` | `str` | `""` | Academic year string |
| `users` | `int` | `0` | Number of users enrolled |
| `posts` | `int` | `0` | Number of posts in the network |
| `folders` | `list[str]` | `[]` | Folder names available in the network |
| `instructors` | `list[str]` | `[]` | Instructor names |
| `status` | `str \| None` | `None` | Network status string (e.g. active) |

**ConfigDict**: `slots=True, extra="forbid"`

---

### Statistics

Aggregate statistics for a network.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `posts` | `int` | `0` | Total number of posts |
| `resolved` | `int` | `0` | Number of resolved questions |
| `unresolved` | `int` | `0` | Number of unresolved questions |
| `users` | `int` | `0` | Total users participating |
| `instructors` | `int` | `0` | Number of instructors |
| `students` | `int` | `0` | Number of students |
| `total_views` | `int` | `0` | Aggregate view count |
| `total_endorsements` | `int` | `0` | Aggregate endorsement count |

**ConfigDict**: `slots=True, extra="forbid"`

**Computed Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `resolution_rate` | `float` | Percentage of resolved questions: `(resolved / (resolved + unresolved)) * 100` or `0.0` if total is 0 |

---

### HallOfFameItem

Represents a top contributor in the hall of fame.

| Field | Type | Default | Alias | Description |
|-------|------|---------|-------|-------------|
| `uid` | `str \| None` | `None` | — | User ID of the student |
| `votes` | `int \| None` | `None` | `nr` | Number of upvotes/endorsements |
| `response_time_seconds` | `int \| None` | `None` | `time` | Time-to-answer in seconds |
| `snippet` | `str \| None` | `None` | `text` | Text snippet of the best answer |
| `timestamp` | `int \| None` | `None` | `when` | Unix epoch timestamp of the answer |

**ConfigDict**: `slots=True, populate_by_name=True, extra="forbid"`

---

## Session & Auth Models

### SessionState

Standard `Enum` (not StrEnum) representing the session lifecycle.

| Value | String | Description |
|-------|--------|-------------|
| `UNAUTHENTICATED` | `"unauthenticated"` | Initial state, not yet logged in |
| `AUTHENTICATING` | `"authenticating"` | Login in progress |
| `AUTHENTICATED` | `"authenticated"` | Successfully logged in |
| `CLOSED` | `"closed"` | Session has been closed |

**Lifecycle**: `UNAUTHENTICATED → AUTHENTICATING → AUTHENTICATED → CLOSED`

---

### SessionConfig

Pydantic Settings class for SDK configuration. Defined in `src/piazza_sdk/adapters/auth.py`.

| Field | Type | Default | Env Var | Description |
|-------|------|---------|---------|-------------|
| `course_id` | `str` | **required** | `PIAZZA_COURSE_ID` | The Piazza course/network ID |
| `user_agent` | `str` | `"piazza-sdk-python/2026.06.22"` | `PIAZZA_USER_AGENT` | Custom User-Agent string |
| `base_url` | `str` | `"https://piazza.com"` | `PIAZZA_BASE_URL` | Base URL for the Piazza API |
| `timeout` | `float` | `30.0` | `PIAZZA_TIMEOUT` | HTTP request timeout in seconds |
| `retries` | `int` | `3` | `PIAZZA_RETRIES` | Number of retry attempts for transient failures |
| `retry_delay` | `float` | `1.0` | `PIAZZA_RETRY_DELAY` | Base delay between retries in seconds |
| `cookie_path` | `Path \| None` | `None` | `PIAZZA_COOKIE_PATH` | Path for persisting cookies to disk |
| `encryption_key` | `str \| None` | `None` | `PIAZZA_ENCRYPTION_KEY` | Fernet key for encrypting persisted cookies |

**Parent Class**: `pydantic_settings.BaseSettings`

**Validators**:
- `encryption_key`: Validates Fernet key format; raises `ValueError` if invalid

**Post-init**: Enforces HTTPS on `base_url` by rewriting the scheme

**Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `login_url` | `str` | `"{base_url}/do_login"` |
| `network_base_url` | `str` | `"{base_url}/network"` |

---

### CookieJar

Manages session cookies and CSRF token persistence.

| Field | Type | Default | Serialized | Description |
|-------|------|---------|------------|-------------|
| `cookies` | `dict[str, str]` | `{}` | Yes | Dictionary of cookie name-value pairs |
| `csrf_token` | `str \| None` | `None` | Yes | Persisted CSRF token for session restoration |
| `encryption_key` | `str \| None` | `None` | **Excluded** | Fernet key for encrypting the cookie file |

**Methods**:

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `set` | `(name: str, value: str) -> None` | None | Set a cookie value |
| `get` | `(name: str) -> str \| None` | `str \| None` | Get a cookie value |
| `clear` | `() -> None` | None | Clear all cookies and CSRF token |
| `to_header` | `() -> str` | `str` | Serialize cookies to a Cookie header string |
| `update_from_header` | `(header: str) -> int` | `int` | Parse a Set-Cookie header, returns count of cookies updated |
| `save` | `async (path: Path) -> None` | None | Persist cookies to a JSON file (with optional Fernet encryption) |
| `load` | `async (path: Path) -> bool` | `bool` | Load cookies from a JSON file |

---

### SessionStateManager

The core session lifecycle manager. Async context manager. Defined in `src/piazza_sdk/adapters/session.py`.

**Class Attribute**: `DEFAULT_SESSION_LIFETIME: float = 14400` (4 hours)

**Constructor**: `__init__(config: SessionConfig, *, cookie_path: Path | None = None, session_lifetime: float | None = None)`

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `SessionConfig` | (arg) | Session configuration |
| `_state` | `SessionState` | `UNAUTHENTICATED` | Current lifecycle state |
| `_client` | `httpx.AsyncClient \| None` | `None` | HTTP client |
| `_cookies` | `CookieJar` | `CookieJar(...)` | Cookie jar |
| `_login_time` | `float \| None` | `None` | Timestamp of last login |
| `_cookie_path` | `Path \| None` | `config.cookie_path` | Cookie persistence path |
| `_session_lifetime` | `float` | `DEFAULT_SESSION_LIFETIME` | Seconds before refresh |
| `_email` | `str \| None` | `None` | Stored email for re-auth |
| `_password` | `str \| None` | `None` | Stored password for re-auth |

**Properties**:

| Property | Type | Description |
|----------|------|-------------|
| `state` | `SessionState` | Current session state |
| `cookies` | `CookieJar` | Cookie jar |
| `client` | `httpx.AsyncClient` | HTTP client (raises `SessionClosedError` if None) |
| `session_age` | `float \| None` | Seconds since last login, or None |
| `needs_refresh` | `bool` | True if session exceeded lifetime |

**Methods**:

| Method | Signature | Returns | Raises | Description |
|--------|-----------|---------|--------|-------------|
| `login` | `async (email: str, password: str) -> None` | None | `AuthenticationError`, `SessionClosedError` | Authenticate user |
| `refresh` | `async (email: str \| None, password: str \| None) -> None` | None | `AuthenticationError` | Re-authenticate with stored or provided credentials |
| `restore_cookies` | `async () -> bool` | `bool` | — | Load cookies from disk |
| `logout` | `async () -> None` | None | — | Alias for `close()` |
| `get_auth_headers` | `() -> dict[str, str]` | `dict` | — | Returns `{"x-csrf-token": token}` if available |
| `is_session_alive` | `async () -> bool` | `bool` | — | Lightweight liveness check via `memo.get_unread_message_count` |
| `close` | `async () -> None` | None | — | Close client, clear state, transition to CLOSED |

---

## Exception Hierarchy

All exceptions inherit from `PiazzaSDKError`. Defined in `src/piazza_sdk/exceptions.py`.

```
Exception
  └── PiazzaSDKError              (base — message, status_code, response_body)
        ├── AuthenticationError    — login/session failures
        ├── RateLimitError         — HTTP 429; additional: retry_after_ms: int | None
        ├── NotFoundError          — HTTP 404 / resource not found
        ├── PermissionError        — HTTP 403
        ├── ValidationError       — response data fails model validation
        ├── NetworkError           — connection/timeout errors
        ├── ContentError           — content processing/parsing failures
        ├── FeedError              — feed retrieval/filtering failures
        ├── UserError              — user operation failures
        ├── SearchError            — search operation failures
        ├── StatisticsError        — statistics retrieval failures
        ├── UploadError            — asset upload failures
        └── SessionClosedError     — operations on closed session
```

**Base Exception Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error message |
| `status_code` | `int \| None` | HTTP status code, if applicable |
| `response_body` | `Any` | Parsed response body, if available |

---

## Protocol Definitions

All protocols use `@runtime_checkable`. Defined in `src/piazza_sdk/ports/`.

### SessionConfigProtocol

| Required Properties |
|---------------------|
| `base_url -> str` |
| `course_id -> str` |

**Implemented by**: `SessionConfig`

---

### TokenStorageProtocol

| Required Methods |
|------------------|
| `async load(path: Path) -> bool` |
| `async save(path: Path) -> None` |
| `clear() -> None` |

**Implemented by**: `CookieJar` (structural subtyping)

---

### AuthProtocol

| Required Methods/Properties |
|----------------------------|
| `async login(email: str, password: str) -> None` |
| `async logout() -> None` |
| `async refresh(email: str \| None = None, password: str \| None = None) -> None` |
| `needs_refresh -> bool` (property) |
| `get_auth_headers() -> dict[str, str]` |

Auth headers use the `csrf-token` header name (not `x-csrf-token`).

**Implemented by**: `SessionStateManager`

---

### HTTPClientProtocol

| Required Methods |
|------------------|
| `async request(method: str, url: str, **kwargs: Any) -> httpx.Response` |
| `async aclose() -> None` |

**Implemented by**: `httpx.AsyncClient` (structural subtyping)

---

### RPCProtocol

| Required Properties/Methods |
|----------------------------|
| `client -> httpx.AsyncClient` (property) |
| `base_url -> str` (property) |
| `network_id -> str` (property) |

The transport seam is the `client` property plus the adapter's public call
methods (`content_get`, `get_my_feed`, …); the concrete `RPC` implements the
full method surface.

**Implemented by**: `RPC`

---

### SessionManagerProtocol

| Required Properties/Methods |
|----------------------------|
| `client -> httpx.AsyncClient` (property) |
| `config -> SessionConfigProtocol` (property) |
| `needs_refresh -> bool` (property) |
| `async login(email: str, password: str) -> None` |
| `async logout() -> None` |
| `async refresh() -> None` |
| `async handle_auth_error() -> None` |
| `get_auth_headers() -> dict[str, str]` |

`handle_auth_error()` is the public recovery hook that RPC adapters invoke
on HTTP 401 before retrying.

**Implemented by**: `SessionStateManager`

---

## Parsing Model (JSON → Pydantic)

The SDK parses Piazza's internal JSON API responses into Pydantic models. This section documents the parsing pipeline.

### Data Flow

```
Piazza API (JSON) → RPC._request() → Domain functions → Pydantic models → User code
```

### RPC Layer (JSON Extraction)

The `RPC` class (`adapters/http.py`) handles raw HTTP communication:

1. **HTTP Request**: Sends JSON payload to `POST /logic/api`
2. **Response Parsing**: Extracts JSON from response via `response.json()`
3. **Error Mapping**: Maps HTTP status codes to typed exceptions:
   - `401` → triggers `_AuthRetryNeededError` → refresh → retry
   - `429` → `RateLimitError`
   - `404` → `NotFoundError`
   - `403` → `PermissionError`
   - `5xx` → retry (tenacity, 3 attempts, exponential backoff)
4. **Result Extraction**: Returns `result` key from JSON response

### Domain Layer (Model Construction)

Domain functions (`domain/*.py`) construct Pydantic models from raw JSON:

```python
# Example: domain/feed.py::get_feed
async def get_feed(rpc, *, session=None, limit=50, offset=0, **kwargs):
    raw = await rpc.get_my_feed(limit=limit, offset=offset, **kwargs)
    feed_data = raw.get("result", {}).get("feed", [])
    return Feed(
        feed=[FeedItem(**item) for item in feed_data],
        total=raw.get("result", {}).get("total", 0),
        page=1,
        page_size=limit,
    )
```

### Model Validation

All models use Pydantic v2 with strict validation:

| ConfigDict Setting | Value | Effect |
|-------------------|-------|--------|
| `extra` | `"forbid"` | Raises `ValidationError` on unknown fields |
| `slots` | `True` | Uses `__slots__` for memory efficiency |
| `populate_by_name` | `True` (some models) | Allows alias or field name in construction |

### Alias Mapping

Some Piazza API fields use different names than the SDK models:

| Model | Field | API Alias | Description |
|-------|-------|-----------|-------------|
| `FeedItem` | `is_pinned` | `pin` | Whether post is pinned |
| `FeedItem` | `content_snippet` | `content_snipet` | Content preview (note misspelling in Piazza API) |
| `PublishingOptions` | `silent_update` | `no_up_notify` | Skip update notifications |
| `HallOfFameItem` | `votes` | `nr` | Vote count |
| `HallOfFameItem` | `response_time_seconds` | `time` | Response time |
| `HallOfFameItem` | `snippet` | `text` | Answer text |
| `HallOfFameItem` | `timestamp` | `when` | Timestamp |

### Type Coercion

| Field | Expected Type | API May Return | Coercion |
|-------|---------------|----------------|----------|
| `FeedItem.type` | `FeedItemType` | `str` | Union accepts raw string if enum match fails |
| `FeedItem.default_anonymity` | `FeedItemDefaultAnonymity` | `str` | Union accepts raw string if enum match fails |
| `Child.type` | `str` | — | Always string (not enum) |
| `PublishingOptions.bypass_email` | `bool` | `int` | Serializer converts `bool → int` (0/1) |

### Error Handling During Parsing

| Exception | Trigger | Example |
|-----------|---------|---------|
| `ValidationError` | Unknown field, wrong type | API adds new field not in model |
| `ContentError` | Malformed JSON, missing `result` key | API response structure changes |
| `NotFoundError` | Post/user/network not found | Invalid `post_id` |
| `PermissionError` | Insufficient access | Accessing private network |

### Example: Post Parsing Pipeline

```python
# 1. RPC sends request
raw = await rpc.content_get(post_id="j5yj4g5d4p2qg3")

# 2. RPC extracts result
content = raw["result"]["content"]

# 3. Domain constructs Post
post = Post(
    id=content["id"],
    type=content["type"],
    title=content.get("title", ""),
    subject=content.get("subject", ""),
    author=content.get("author", ""),
    created_at=parse_datetime(content.get("created")),
    updated_at=parse_datetime(content.get("updated")),
    nr=content.get("nr", 0),
    raw=content,  # preserved for advanced use
    tags=content.get("tags", []),
    folder=content.get("folder", ""),
    status=content.get("status", "active"),
    views=content.get("views", 0),
    unique_views=content.get("unique_views"),
    students=[StudentInfo(**s) for s in content.get("students", [])],
    followups=[FollowUp(**f) for f in content.get("followups", [])],
    answers=[Answer(**a) for a in content.get("answers", [])],
    change_log=[ChangeLogEntry(**e) for e in content.get("change_log", [])],
    endorsements=[Endorsement(**e) for e in content.get("endorsements", [])],
    config=PostConfig(**content.get("config", {})),
    children=[Child(**c) for c in content.get("children", [])],
    user_name=content.get("user_name", ""),
    visibility=content.get("visibility", "public"),
    revisions=[PostRevision(**r) for r in content.get("revisions", [])],
)
```

---

## Live-Verified Wire Contracts (2026-08)

The following behaviors were confirmed against the production
`piazza.com` JSON-RPC API during the audit's live-verification pass.
When code and this table disagree, trust the table and file a bug.

| Contract | Detail |
|---|---|
| **Post creation** | `content.create` requires `subject` (not `title`), an anonymity *string* (`"no"`/`"stud"`/`"full"` — boolean `false` is rejected), and at least one existing `folders` entry. Unknown folder names are rejected with "Please specify folder". |
| **Answers** | `content.answer` uses `type: "i_answer"` (instructor) / `"s_answer"` (student) plus a `revision` int. Instructors are denied `"s_answer"` with "No permission". Answers exist only on `question` posts. |
| **Pinning** | Dedicated `content.pin` / `content.unpin` methods exist; tag-based pinning is not the wire mechanism. Locking remains tag-based (no dedicated endpoint). |
| **Deletion** | `content.delete` returns an **empty dict** on success — there is no `{"result": "success"}` wrapper. Success = no embedded error and no explicitly failed result value. Same tolerance applies to resolve via `content.update`. |
| **User classes** | The legacy `/user/api/get_user_classes` REST path returns HTTP 404. Classes derive from `user_profile.get_profile` → `all_classes`, a `{nid → class dict}` mapping. |
| **Unknown methods** | Piazza reports unknown RPC methods as embedded errors ("Method not found: …") rather than HTTP 404; the RPC layer normalizes these to `NotFoundError`. |
| **Nested payloads** | Real posts carry config keys beyond the model surface (e.g. `config.feed_groups`). Server-fed nested models (`PostConfig`, `Answer`, `PostRevision`) therefore ignore unknown keys instead of rejecting them. |
| **Retries** | 429 and 5xx responses ARE retried (exponential backoff honoring `Retry-After`); typed exceptions survive retries via reraise, preserving `retry_after_ms` / `status_code`. |
| **Feed** | `network.get_my_feed` result includes `total`; Hall-of-Fame data lives at `result.hof.best_answer` after single envelope unwrap. |
| **Global email prefs** | `user.status` exposes `config.email_prefs` keyed by network ID plus a non-course `career` key; entries carry `auto_follow` as **bool-or-string**, `new`, `updates`, `no_events`, `throttle`. Writes go through global `user.update` with the full map (`{"email_prefs": {...}}`) — no nid/aid injection; partial per-entry merges must write back the whole preserved map. Flip/revert verified with live read-back. |
| **Role matrix** | `user.status` → `networks[].config.roles` carries all five roles (admin/instructor/professor/student/ta); student additionally includes `can_post_anonymous_all`. Unknown keys tolerated via server-fed models. |
| **Resources URL** | `https://piazza.com/{school_ext}/{term-lowercase-nospace}/{short_number}/home` responds HTTP 200 when slugs are present on the network entry. |
| **Child payloads** | Children in `content.get` carry **no `history`** and usually no flat `content`; follow-up text lives in `subject`. Tree walks fall back history → content → subject. |
| **Network-scoped params** | `content.bookmark/unbookmark/mark_favorite/mark_unfavorite/view/cancel_edit/remove_feedback/del_item/get_users` accept (and bookmark round-trips with) normalized `nid` + `aid` params; verified via live bookmark→read-back→unbookmark cycle. |
| **Login CSRF** | `GET /main/csrf_token` returns a JS assignment (`window.CSRF_TOKEN = "...";`) usable directly as the login token; the login-page `<meta>` scrape remains a working fallback. Failed logins return HTTP **200** with an inline `var ERROR_MSG = "...";` assignment carrying the server's reason (e.g. "Email or password incorrect"). |
| **Scheduled posts** | Two-step flow, both steps live-verified: `network.save_draft` (nested `draft{content,folders,btn{post_type_note,post_type_question,schedule_later,schedule_later_time},txt{post_summary}}`) returns the draft ID as a **bare-string** result — `_safe_call`-style dict coercion destroys it. `content.create` then takes `draftId` + `config.schedule_later/schedule_later_time` and confirms `{"scheduled": true}` with **no post ID** until publish time. Polls cannot be scheduled. Flat draft fields fail with "Missing parameter: draft"; creating without a valid `draftId` fails with "Save as draft first". |
| **Private posts** | Instructor-only visibility via `config.feed_groups = "instr_{nid},{user_id}"`; verified by create → read-back → delete. Requires an existing folder like any post. |
| **Instructor follow-ups** | Followups accept `config: {"editor": "rte", "ionly": true}` for staff-only replies; `ionly` observed verbatim on read-back. |
| **student_view** | `content.get` accepts `student_view: true` to render the student-visible view of a post from a staff account. |
| **Share-link token** | `user.status` → `networks[].auth` carries the course's "Share Your Class" token (e.g. `"fd13d72"`); absent/empty on `all_classes` entries. Feeds `demo_login` and `NetworkInfo.demo_login_url`. |
| **Demo login** | `GET /demo_login?nid=…&auth=…` grants a demo session: valid tokens return HTTP 200 and set real session cookies (`piazza_session`, `last_piaz_user`, CSRF acquirable, feed readable via `network.get_my_feed`). **Invalid/expired tokens return HTTP 404 while still setting an anonymous `session_id`** — status code must be checked before adopting cookies. Demo scope excludes `memo.get_unread_message_count` (so `is_session_alive()` is `False` for demo users). Both forms live-verified. |


---

## Live-Verified Wire Contracts (HAR Captures)

# Piazza API: Post Query Data Dictionary

This document describes the **observed post payloads** returned by Piazza’s current web app traffic captured in the supplied HAR files:

- `piazza.com_redacted(1).har`
- `piazza.com2.har`

The goal here is to document the **raw response shape** as it appears in Piazza traffic, while keeping the structure useful for SDK/model design. Where the HARs show variation, the field is marked as optional or noted as “observed on some posts”.

---

## 1) Core post object

`content.get` returns a nested dictionary for a single thread/post.

### Top-level post fields

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Unique thread/post identifier. |
| `folders` | `list[str]` | Folder path(s) for the post. Usually empty or a single folder name. |
| `nr` | `int` | Numeric post number / thread number. |
| `data` | `dict` | Legacy container; observed as `{"embed_links": []}`. |
| `created` | `str` | ISO-8601 timestamp string (`YYYY-MM-DDTHH:MM:SSZ`). |
| `bucket_order` | `int` | Feed bucket ordering. Pinned posts observed with `0`. |
| `bucket_name` | `str` | Bucket label such as `Pinned` or `Today`. |
| `no_answer_followup` | `int` | Count of unresolved / unanswered follow-ups. |
| `history_size` | `int` | Number of history entries captured for the post. |
| `history` | `list[dict]` | Full post history objects. |
| `change_log` | `list[dict]` | Change log entries for the thread. |
| `type` | `str` | Thread type: commonly `note`, `question`, or `poll`. |
| `tags` | `list[str]` | Internal tags, e.g. `pin`, `student`, instructor/category tags. |
| `tag_good` | `list[dict]` | Endorsement records for the thread. |
| `tag_good_arr` | `list[str]` | Endorser IDs associated with the thread/child items. |
| `children` | `list[dict]` | Recursive child tree (follow-ups / feedback / replies). |
| `followup_summary` | `dict` | Observed on some posts; usually a compact summary object (often empty). |
| `unique_views` | `int` | Unique viewer count. |
| `anon_map` | `dict` | Anonymous alias mapping observed in some posts. |
| `anon_icons` | `bool` | UI/metadata flag observed in some responses. |
| `uid` | `str` | Author user ID (may be omitted in some contexts, depending on visibility and client). |
| `status` | `str` | Raw status string; observed as `active` in the HARs. Older clients may also surface `inactive`. |
| `drafts` | `dict` | Draft state for the post; may be empty or contain per-editor draft data. |
| `request_instructor` | `int` | Number of instructors explicitly requested/tagged in the thread. |
| `request_instructor_me` | `bool` | Whether the current instructor account is tagged/requested. |
| `bookmarked` | `int` | Bookmark/follow count. |
| `num_favorites` | `int` | Favorite count. |
| `my_favorite` | `bool` | Whether the current user has favorited the thread. |
| `is_bookmarked` | `bool` | Whether the current user has bookmarked/followed the thread. |
| `is_pinned` | `bool` | Whether the thread is pinned. |
| `is_tag_good` | `bool` | Whether the current user has endorsed the thread. |
| `q_edits` | `list[dict]` | Legacy/empty edit list; not populated in the HARs. |
| `i_edits` | `list[dict]` | Legacy/empty instructor edit list; not populated in the HARs. |
| `s_edits` | `list[dict]` | Legacy/empty student edit list; not populated in the HARs. |
| `t` | `int` | Large integer token observed in responses; appears to be a timestamp-like internal value. |
| `default_anonymity` | `str` | Raw anonymity setting. Observed as `"no"` in the HARs. |

---

## 2) Change log entries

The `change_log` array contains per-change records.

### `ChangeLogEntry`

| Field | Type | Notes |
|---|---|---|
| `anon` | `str` | Anonymous label such as `"no"` or an alias. |
| `uid_a` | `str \| None` | Anonymous user token/alias identifier; not always present. |
| `uid` | `str` | Internal user ID of the contributor. |
| `data` | `str \| None` | Only present for initial creation entries; content hash / payload marker. |
| `to` | `str \| None` | Target thread ID (seen in some historical shapes). |
| `v` | `str` | Visibility marker; observed as `all` in the HARs. |
| `type` | `str` | Change type: `create`, `followup`, `feedback`, `i_answer`, `s_answer`. |
| `when` | `str` | ISO-8601 timestamp string. |
| `cid` | `str` | Child ID linked to the change entry. |

**Observed HAR example**
```json
{
  "anon": "no",
  "uid": "llo5jk902ie31e",
  "data": "mmj6vi4pnl05t",
  "v": "all",
  "type": "create",
  "when": "2026-03-09T13:00:26Z"
}
```

---

## 3) History entries

The `history` array stores the visible revision history of the thread content.

### `HistoryEntry`

| Field | Type | Notes |
|---|---|---|
| `anon` | `str` | Anonymous label / visibility alias. |
| `uid` | `str` | Internal user ID of the editor. |
| `subject` | `str` | Subject line at that revision. |
| `created` | `str` | ISO-8601 timestamp for the revision. |
| `content` | `str` | HTML body content at that revision. |
| `uid_a` | `str \| None` | Not observed in the sample payloads, but may appear for anonymous history records. |

**Observed HAR example**
```json
{
  "anon": "no",
  "uid": "llo5jk902ie31e",
  "subject": "Homework Re-Grade Requests",
  "created": "2026-03-09T13:00:26Z",
  "content": "<p>Hi students, ...</p>"
}
```

---

## 4) Endorsements

The `tag_good` array contains endorsement metadata.

### `Endorsement`

| Field | Type | Notes |
|---|---|---|
| `role` | `str` | Usually `student` or `instructor` (TA/admin variants can appear in related user payloads). |
| `name` | `str` | Public display name. |
| `endorser` | `dict` | Nested endorser object; observed as `{}` in some captured posts. |
| `admin` | `bool` | Whether the endorser is an admin. |
| `photo` | `str \| None` | Photo filename, if present. |
| `id` | `str` | Endorser user ID. |
| `photo_url` | `str \| None` | Public CDN URL for the profile photo. |
| `published` | `bool` | Whether the endorsement is publicly published. |
| `us` | `bool` | Internal staff/user flag (exact semantics unclear). |
| `facebook_id` | `str \| None` | Linked Facebook ID, if any. |

**Observed HAR example**
```json
{
  "role": "student",
  "name": "Peace Bakare",
  "endorser": {},
  "admin": false,
  "photo": "46dc2e68-758c-407c-96b7-0b7fa5b21cc3_200.jpg",
  "id": "lz07msebcme2si",
  "photo_url": "https://cdn-uploads.piazza.com/photos/lz07msebcme2si/46dc2e68-758c-407c-96b7-0b7fa5b21cc3_200.jpg",
  "published": true,
  "us": false,
  "facebook_id": null
}
```

---

## 5) Thread config

The `config` object varies by post and editor context. The HARs show a few concrete shapes.

### Observed keys

| Field | Type | Notes |
|---|---|---|
| `editor` | `str` | Editor mode observed as `rte`. |
| `has_emails_sent` | `int \| bool` | Flag indicating whether notification emails were sent. |
| `is_default` | `int \| bool` | Observed on one post as `1`. |
| `schedule_later_time` | `int | None` | Unix epoch milliseconds for scheduled publication. |
| `feed_groups` | `str | list[str] \| None` | Seen in older reverse-engineered docs; not observed in the two HARs here, but likely context-dependent. |
| `must_read_version` | `int | None` | Historical/legacy field from older docs. |
| `seen` | `dict[str, int] | None` | Historical/legacy read-tracking map. |

### Observed HAR examples

```json
{"is_default": 1}
```

```json
{
  "schedule_later_time": 1773061200000,
  "editor": "rte",
  "has_emails_sent": 1
}
```

---

## 6) Child tree

The `children` field is recursive. Piazza uses nested child objects for follow-ups and replies/feedback.

### `Child` (generic recursive node)

| Field | Type | Notes |
|---|---|---|
| `id` | `str \| None` | Child ID; present in some child shapes. |
| `uid` | `str` | Author user ID. |
| `anon` | `str` | Anonymous label / alias. |
| `subject` | `str` | Child subject or comment text. |
| `content` | `str \| None` | HTML body when present. |
| `created` | `str` | ISO-8601 timestamp. |
| `updated` | `str \| None` | Last update time if available. |
| `folders` | `list[str] \| None` | Usually empty in the observed historical docs. |
| `data` | `dict \| None` | Legacy embed-link container. |
| `bucket_order` | `int | None` | Inherited/attached feed bucket index. |
| `bucket_name` | `str \| None` | Inherited/attached feed bucket label. |
| `no_upvotes` | `int | None` | Upvote count for follow-up/comment-shaped nodes. |
| `tag_good` | `list[dict] \| None` | Endorsement records. |
| `tag_good_arr` | `list[str] \| None` | Endorser IDs. |
| `config` | `dict \| None` | Child-specific config payload. |
| `children` | `list[dict] \| None` | Recursive nested children. |

### Notes
- The old reverse-engineered docs split this into `followup_children_dict` and `feedback_children_dict`.
- The HARs confirm that nested child trees exist, but they do not fully expose all child shapes in the captured samples because some threads had empty `children`.

---

## 7) Post-level fields worth keeping

These are all returned by current `content.get` responses and should stay in the canonical model.

| Field | Type | Why it matters |
|---|---|---|
| `history_size` | `int` | Indicates whether the thread has revision history. |
| `no_answer_followup` | `int` | Useful for unresolved-thread triage. |
| `followup_summary` | `dict` | Helpful compact summary, present on some posts. |
| `anon_map` | `dict` | Important for anonymous-thread reconstruction. |
| `anon_icons` | `bool` | UI metadata that can help preserve display semantics. |
| `drafts` | `dict` | Signals autosave / draft recovery support. |
| `request_instructor` | `int` | Useful for staff triage and workload dashboards. |
| `request_instructor_me` | `bool` | Important when the current staff member is directly requested. |
| `bookmarked` | `int` | Bookmark popularity / follow count. |
| `num_favorites` | `int` | Favorite count. |
| `my_favorite` | `bool` | User-specific state. |
| `is_bookmarked` | `bool` | User-specific state. |
| `is_pinned` | `bool` | UI state. |
| `is_tag_good` | `bool` | User-specific endorsement state. |
| `t` | `int` | Internal timestamp-like token. |
| `default_anonymity` | `str` | Raw anonymity setting. |

---

## 8) Related RPCs observed in the HARs

These are not post fields, but they help explain how the data is produced and mutated.

| RPC | Observed result shape | Notes |
|---|---|---|
| `content.get` | Full post dictionary | Main post fetch endpoint. |
| `content.auto_save` | `"OK"` | Autosave / draft persistence. |
| `content.edit` | string ID | Returns a content/edit identifier. |
| `content.cancel_edit` | `"OK"` | Cancels an in-progress edit. |
| `content.bookmark` / `content.unbookmark` | `"OK"` | Bookmark/unbookmark thread. |
| `content.mark_favorite` / `content.mark_unfavorite` | `"OK"` | Favorite/unfavorite thread. |
| `content.add_feedback` / `content.remove_feedback` | `"OK"` | Add/remove feedback/endorsement-like actions. |
| `generic.sanitize_html` | `{"main": "<p>...</p>"}` | HTML sanitization result. |
| `network.get_instructor_stats` | stats dict | Includes unanswered questions, response time, and contribution counts. |
| `network.get_all_users` | `list[dict]` | Returns user records for the whole network. |
| `network.get_users` | `list[dict]` | Returns specific user records. |
| `network.get_online_users` | `{"users": int}` | Online user count. |
| `network.get_my_feed` | feed wrapper dict | Feed listing with `feed`, `more`, `sort`, `live`, and other metadata. |
| `network.filter_feed` | feed wrapper dict | Filtered feed results. |
| `network.search` | list of lightweight thread dicts | Search result rows with compressed thread fields. |

---

## 9) Lightweight search / feed shapes

The HARs also expose lighter-weight representations used by feed/search endpoints.

### Search result row

Observed `network.search` rows contain fields like:

- `folders`
- `nr`
- `main_version`
- `request_instructor`
- `log`
- `subject`
- `bucket_order`
- `no_answer_followup`
- `bucket_name`
- `num_favorites`
- `type`
- `tags`
- `tag_good_prof`
- `gd_f`
- `unique_views`
- `content_snipet` (note the misspelling)
- `view_adjust`
- `modified`
- `id`
- `gd`
- `updated`
- `status`
- `uv`
- `naf`
- `fol`
- `na`
- `pin`
- `u`
- `v`
- `va`
- `m`
- `rq`
- `highlighted_snipet`
- `version`
- `is_new`
- `book`
- `labels`
- `sort_order`

### Feed wrapper

Observed `network.filter_feed` / `network.get_my_feed` wrappers include keys such as:

- `feed`
- `t`
- `more`
- `sort`
- `live`

`network.get_my_feed` also includes additional account/feed metadata such as `drafts`, `tags`, `notifications`, `hof`, `token_data`, `has_live_posts`, and user/network counters.

---

## 10) Suggested model guidance

For a current SDK, the safest approach is:

1. Keep a **lossless raw post model** that preserves every field Piazza returns.
2. Build a **normalized domain model** on top of it for convenient use.
3. Treat unknown fields as forward-compatible rather than forbidden when parsing raw Piazza responses.

A good raw model should preserve:

- `anon_map`
- `followup_summary`
- `drafts`
- `is_pinned`
- `request_instructor`
- `request_instructor_me`
- `bookmarked`
- `num_favorites`
- `my_favorite`
- `is_bookmarked`
- `is_tag_good`
- `t`
- `default_anonymity`

and should leave room for future fields without breaking parsing.

---

## 11) network.update
This JSON-RPC method is used to configure network-level (course-level) properties such as Office Hours, General Information, and Course Description.

### Office Hours
```json
{
  "method": "network.update",
  "params": {
    "id": "network_id",
    "office_hours": {
      "staff_uid": {
        "time": "4",
        "location": "dse"
      }
    }
  }
}
```

### General Information
```json
{
  "method": "network.update",
  "params": {
    "id": "network_id",
    "general_information": [
      {
        "label": "label here",
        "text": "information goes here"
      }
    ]
  }
}
```
An empty array `[]` clears the general information.

### Course Description
```json
{
  "method": "network.update",
  "params": {
    "id": "network_id",
    "course_description": "description"
  }
}
```

### Add Students
```json
{
  "method": "network.update",
  "params": {
    "id": "network_id",
    "from": "ClassSettingsPage",
    "add_students": ["student@example.com"]
  }
}
```

### Remove Users
```json
{
  "method": "network.update",
  "params": {
    "id": "network_id",
    "remove_users": ["user_id_123"]
  }
}
```

## 12) user.status
This JSON-RPC method is used to get the global status of the authenticated user, including their enrolled classes and system-wide notifications.
Unlike most content endpoints, it resides at `/main/api`, not `/logic/api`.

```json
{
  "method": "user.status",
  "params": {}
}
```
