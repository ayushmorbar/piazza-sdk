# Skill: piazza-dev

## Purpose

Develop features and fix bugs in the Piazza SDK codebase. Enforces async-first patterns, Pydantic v2 conventions, and the project's exception hierarchy.

## When to Use

- Adding new API endpoints or models
- Modifying auth flow, RPC layer, or exception handling
- Refactoring existing code
- Any task that touches `src/piazza_sdk/`

## Workflow

### 1. Read before writing

Always read the target file and its imports before editing. Understand existing patterns:

- `auth.py` — async context manager pattern, httpx client lifecycle
- `api/rpc.py` — tenacity retry decorators, HTTP error → exception mapping
- `api/piazza.py` and `api/network.py` — high-level methods using RPC
- `models/` — Pydantic v2 BaseModel with `ConfigDict(strict=True, extra="forbid")`
- `exceptions.py` — never raise bare `Exception`; use the SDK hierarchy

### 2. Coding standards

```python
# Type hints — always
async def get_user(self, user_id: str) -> User: ...

# X | None — not Optional[X]
config: str | None = None

# Pydantic v2 — ConfigDict, not model_config dict
from pydantic import BaseModel, ConfigDict, Field

class MyModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    name: str = Field(..., description="The name")

# Constants — module level, not inline
MAX_RETRIES = 3
_RETRY_WAIT_MIN = 1.0
_RETRY_WAIT_MAX = 30.0
```

### 3. Error handling

```python
from piazza_sdk.exceptions import AuthenticationError, RateLimitError

# Map HTTP status to typed exception
if response.status_code == 401:
    raise AuthenticationError(f"Login failed: {response.text}")
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", "5")) * 1000
    raise RateLimitError(retry_after_ms=retry_after)
```

### 4. Lint before finishing

```bash
ruff check src/
mypy src/
```

Fix any errors before declaring the task complete.

### 5. Checklist

- [ ] New code has full type hints
- [ ] Uses existing exception classes (no new ones unless necessary)
- [ ] Models use `ConfigDict(strict=True, extra="forbid")`
- [ ] No bare `except Exception` — catch specific SDK exceptions
- [ ] `ruff check src/` passes
- [ ] `mypy src/` passes
- [ ] If adding a model, add it to `__init__.py` `__all__`
