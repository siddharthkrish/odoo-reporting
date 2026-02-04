# Python Standards Reference

## Structure

- `package/__init__.py` should define `__all__` for public exports.
- Keep CLI in `package/cli.py` with a `main()` function.

## Errors

- Raise `ValueError` for invalid user input.
- Raise `RuntimeError` for missing configuration or failed external calls.

## Dates

- Accept `YYYY-MM-DD` input and convert to `datetime` with explicit timezone or time bounds as needed.

## Output

- For data output, return plain dicts or typed dataclasses; serialize at the edges (CLI).
