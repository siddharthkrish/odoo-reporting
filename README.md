# odoo-sales

Fetch sales data from an Odoo instance for a given date range.

## Setup

1) Create a `.env` file in the project root:

```
ODOO_URL=https://your-odoo.example.com
ODOO_DB=your_database
ODOO_USERNAME=you@example.com
ODOO_API_KEY=your_api_key
```

2) Install dependencies with `uv`:

```
uv sync
```

## Usage

By default, fetched sales results are stored in a local SQLite cache (`.odoo_sales_cache.sqlite`) so repeated queries for the same date range and filters do not make additional Odoo API calls.

You can override the cache path or disable caching using environment variables:

- `ODOO_CACHE_DB` - path to the sqlite cache file (default: `.odoo_sales_cache.sqlite`)
- `ODOO_CACHE_ENABLED=false` - disable caching entirely

Library:

```
from odoo_sales.client import OdooClient

client = OdooClient.from_env()
orders = client.get_sales_data("2026-01-01", "2026-01-31")
```

CLI:

```
odoo-sales --from 2026-01-01 --to 2026-01-31
```

Test script:

```
python tests/test_sales_cli.py --from 2026-01-01 --to 2026-01-31
```
