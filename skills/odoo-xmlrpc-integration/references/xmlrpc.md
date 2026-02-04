# Odoo XML-RPC Reference

## Endpoints

- Common: `{url}/xmlrpc/2/common`
- Object: `{url}/xmlrpc/2/object`

## Authenticate

```
import xmlrpc.client

common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, api_key, {})
```

## Basic model call

```
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
records = models.execute_kw(
    db, uid, api_key,
    "sale.order", "search_read",
    [[("date_order", ">=", "2026-01-01 00:00:00")]],
    {"fields": ["id", "name", "date_order"], "limit": 10},
)
```

## Common methods

- `search` — return record IDs
- `read` — read fields for record IDs
- `search_read` — search + read in one call
- `create` — create a record
- `write` — update records
- `unlink` — delete records
