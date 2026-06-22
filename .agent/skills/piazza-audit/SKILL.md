# Skill: piazza-audit

## Purpose

Audit the Piazza SDK codebase for security, type safety, and code quality issues.

## When to Use

- Before a release
- After major refactors
- When reviewing PRs
- Periodic health checks

## Audit Checklist

### 1. Secrets and credentials

```bash
# Check for hardcoded secrets
grep -rn "password\|secret\|token\|api_key" src/ --include="*.py" | grep -v "test\|example\|mock"
```

- No hardcoded passwords, tokens, or API keys in source
- `.env` is in `.gitignore`
- `.env.example` has placeholder values only

### 2. Exception safety

```bash
# Check for bare Exception catches
grep -rn "except Exception" src/ --include="*.py"
```

- No bare `except Exception` (catch specific SDK exceptions)
- No `except:` (bare except clause)
- All exceptions inherit from `PiazzaSDKError`

### 3. Type safety

```bash
mypy src/ --strict
```

- Zero mypy errors
- No `Any` escape hatches without comment
- All public functions have type hints

### 4. Lint

```bash
ruff check src/ tests/
```

- Zero ruff errors
- No `# noqa` suppressions without justification

### 5. Dependency audit

```bash
pip-audit
```

- No known vulnerabilities in dependencies
- Dependencies pinned to minimum versions in `pyproject.toml`

### 6. Session security

- Cookie encryption uses Fernet (AES-128-CBC)
- `CookieJar.encryption_key` excluded from serialization (`exclude=True`)
- Session state transitions are validated
- CSRF token validated before use

### 7. HTTP safety

- Retry logic uses exponential backoff (tenacity)
- Rate limit errors include `retry_after_ms`
- Timeouts configured on httpx client
- No `verify=False` (SSL verification always on)

## Output Format

Report findings as:

```
[OK]   Item description
[WARN] Item description — details
[FAIL] Item description — details — fix: suggestion
```
