# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

Create a `.env` file in the project root with:

```
ODOO_URL=https://your-odoo.example.com
ODOO_DB=your_database
ODOO_USERNAME=you@example.com
ODOO_API_KEY=your_api_key
```

Install dependencies:

```
uv sync
```

## Commands

```bash
# Run CLI (outputs JSON to stdout)
uv run odoo-sales --from 2026-01-01 --to 2026-01-31

# Run web dashboard (FastAPI at http://127.0.0.1:8000)
uv run odoo-sales-web

# Run integration test script
uv run python tests/test_sales_cli.py --from 2026-01-01 --to 2026-01-31

# Add/remove dependencies
uv add <package>
uv remove <package>
```

## Architecture

The package is `odoo_sales/` with three modules:

- **`client.py`** — Core library. `OdooClient` authenticates via Odoo's XML-RPC API (`/xmlrpc/2/common` + `/xmlrpc/2/object`) and fetches `sale.order` records. `SaleOrder` is a frozen dataclass. Channel detection (`_detect_channel`) maps Odoo order fields to sales channels (Lazada, Website/WooCommerce, Shopee, Amazon, or Direct/partner name).
- **`cli.py`** — Thin wrapper around `OdooClient`; prints JSON to stdout. Entry point: `odoo-sales`.
- **`web.py`** — FastAPI app serving a static dashboard (`static/index.html`) and a `/api/sales?from=&to=` endpoint. Entry point: `odoo-sales-web`.

`OdooClient.from_env()` loads credentials from `.env` via `python-dotenv`. Authentication is lazy (cached in `_uid` after first call).

## Skills

The `skills/` directory contains Claude Code skill definitions:

- **`odoo-xmlrpc-integration`** — Guidelines for Odoo XML-RPC patterns (authentication, `search_read`, domains, relational fields).
- **`python-project-standards`** — Project conventions: type hints, dataclasses, `argparse` CLIs, `uv` workflows, `.env` configuration.

## Conventions

- Raise `ValueError` for invalid user input, `RuntimeError` for missing config or failed external calls.
- Accept dates as `YYYY-MM-DD` strings; convert to `datetime` with explicit time bounds (`time.min`/`time.max`) when building Odoo domain filters.
- Only fetch needed fields from Odoo — extend `DEFAULT_FIELDS` in `client.py` when new fields are required.
- Serialize to dicts only at the edges (CLI/API layer), not inside the core library.
- Use `uv add` (not pip) to add dependencies; commit `uv.lock`.
