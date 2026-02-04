---
name: python-project-standards
description: "Apply Python project standards for this repo, including uv packaging workflows, .env configuration with python-dotenv, and modern code conventions (types, dataclasses, CLIs). Use when shaping project structure, dependency management, or configuration patterns."
---

# Python Project Standards

## Overview

Apply modern Python conventions alongside uv-based packaging and .env configuration.

## Guidelines

- Use type hints throughout and prefer `dataclasses` for data containers.
- Keep modules small; avoid global state and side effects on import.
- Provide clear error messages for configuration and input errors.
- Prefer `argparse` for CLIs and expose a `main()` entry point.
- Use ISO date strings (`YYYY-MM-DD`) for user inputs when dates are needed.
- Keep dependencies minimal and document required env vars.
 - Prefer uv for dependency changes and lockfile updates.
 - Load `.env` early with `python-dotenv` and validate required keys.

## References

- Read `references/standards.md` for style patterns and project structure hints.
- Read `references/uv.md` for uv command patterns and `pyproject.toml` expectations.
- Read `references/dotenv.md` for python-dotenv usage and env precedence rules.
