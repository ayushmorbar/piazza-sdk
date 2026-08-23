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
