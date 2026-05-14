# CI/CD Workflows

## CI — Pull Request Checks

Trigger: `pull_request`

Runs on every PR against `main`:
- **Matrix**: Python 3.10, 3.11, 3.12, 3.13 × Ubuntu, macOS, Windows
- **Steps**: ruff linter, ruff format check, mypy type check, pytest

All steps must pass before merging.

## CD — Release Publishing

Trigger: `v*.*.*` tags (e.g., `v0.2.0`)

Builds and publishes the package to PyPI.

## Creating a Release

```bash
# 1. Ensure main is up to date
git checkout main
git pull origin main

# 2. Choose version based on changes:
#    v0.3.0 — new features or breaking changes (middle number)
#    v0.2.1 — bug fixes, minor improvements (last number)
#    v1.0.0 — major release (first number)

# 3. Set version and tag
uv version 0.2.1
git add pyproject.toml uv.lock
git commit -m "Bump version to 0.2.1"
git tag v0.2.1

# 4. Push
git push origin main --tags

# 5. (Optional) Create release notes
gh release create v0.2.1 --title "v0.2.1" --notes "Bug fixes"
```

The CD workflow will automatically build and publish to PyPI when the tag is pushed.
