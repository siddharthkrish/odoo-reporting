---
name: odoo-xmlrpc-integration
description: Integrate with Odoo using the XML-RPC API, including authentication with API keys, common endpoints, model access patterns, domains, and field selection. Use for tasks that query or update Odoo data via XML-RPC.
---

# Odoo XML-RPC Integration

## Overview

Use Odoo's XML-RPC endpoints for authentication and model operations. Prefer `search_read` for simple read-only list queries.

## Workflow

1) Authenticate via `/xmlrpc/2/common` to get `uid`.
2) Use `/xmlrpc/2/object` and `execute_kw` for model calls.
3) Use `search_read` with a domain and explicit `fields` list.
4) Add `limit` and `order` for predictable results.

## Guidelines

- Use API key as the password while keeping `ODOO_USERNAME` as the login.
- Keep domains explicit; prefer ISO date strings for date filters.
- Avoid requesting all fields; fetch only what is needed.
- Normalize relational fields (`many2one`) to `(id, name)` values.

## References

- Read `references/xmlrpc.md` for endpoint patterns, examples, and common model methods.
