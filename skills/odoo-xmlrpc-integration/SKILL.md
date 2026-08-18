---
name: odoo-xmlrpc-integration
description: Integrate with and debug this project's Odoo XML-RPC data, including authentication, read-only aggregate checks, model operations, domains, field selection, and secure access to the deployed API credential. Use for Odoo queries, reporting discrepancies, cache comparisons, or XML-RPC changes.
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
- Read `references/debug-access.md` when investigating reporting discrepancies or when local Odoo credentials fail.
