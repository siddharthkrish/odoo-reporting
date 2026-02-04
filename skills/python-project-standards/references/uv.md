# UV Packaging Reference

## Core commands

- `uv sync` — install deps from `pyproject.toml` / `uv.lock`
- `uv add <package>` — add dependency and update lock
- `uv remove <package>` — remove dependency and update lock
- `uv run <cmd>` — run command in the uv-managed environment

## Files

- `pyproject.toml` — project metadata and dependencies
- `uv.lock` — resolved dependency lockfile (commit it for reproducible installs)

## Minimal pyproject sections

```
[project]
name = "your-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "example>=1.0.0",
]

[project.scripts]
my-cli = "your_package.cli:main"
```

## Notes

- Prefer `uv sync` for setup and `uv add` for dependency changes.
- Keep dependency lists small and explicit.
