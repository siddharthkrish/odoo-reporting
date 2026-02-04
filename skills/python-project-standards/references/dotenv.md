# python-dotenv Reference

## Basic usage

```
from dotenv import load_dotenv

load_dotenv()  # loads .env from current or parent directories
```

## Precedence

- By default, `load_dotenv()` does not override existing environment variables.
- Use `load_dotenv(override=True)` only when explicitly needed.

## Required key validation

```
import os

value = os.getenv("MY_KEY")
if not value:
    raise RuntimeError("Missing required environment variable: MY_KEY")
```

## Recommended files

- `.env` for local secrets (never commit)
- `.env.sample` for a public template
