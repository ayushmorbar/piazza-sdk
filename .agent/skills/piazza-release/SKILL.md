# Skill: piazza-release

## Purpose

Version bumps, changelog updates, and PyPI publishing for the Piazza SDK.

## When to Use

- Bumping version before a release
- Updating CHANGELOG.md
- Publishing to PyPI

## Version Management

Version lives in `src/piazza_sdk/_version.py`. Format: `YYYY.MM.DD` (CalVer).

```python
__version__ = "2026.06.22"  # ← update this
```

Also reflected in `pyproject.toml`:
```toml
version = "2026.06.22"  # ← keep in sync
```

## Release Workflow

### 1. Pre-flight checks

```bash
ruff check src/ tests/
mypy src/
pytest tests/ -v
```

All must pass.

### 2. Bump version

Update both files:
- `src/piazza_sdk/_version.py` → `__version__`
- `pyproject.toml` → `project.version`

### 3. Update CHANGELOG.md

Add entry under `[Unreleased]` → move to new version section.

### 4. Build and publish

```bash
# Clean old builds
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Upload to PyPI (requires PyPI token)
twine upload dist/*

# Or upload to test PyPI first
twine upload --repository testpypi dist/*
```

## Checklist

- [ ] All tests pass
- [ ] Version bumped in `_version.py` and `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] No uncommitted changes remain
