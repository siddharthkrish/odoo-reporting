# Secure Odoo Data Debugging

Use this workflow for read-only comparisons between Odoo and the Firestore reporting mirror.

## Guardrails

- Query aggregates first; do not print API keys, OAuth tokens, customer names, or order-level details.
- Use `search_count`, `search_read`, or `read_group`. Do not call `create`, `write`, or `unlink` while diagnosing.
- Keep temporary secrets outside the repository and remove them immediately after use.
- Never place a secret in a command argument, log, patch, or assistant response.

## 1. Try the local configuration

Use `OdooClient.from_env()` from the project environment. If authentication fails, treat `.env`'s `ODOO_API_KEY` as stale. If local Python reports a CA verification failure, use the deployed container runtime rather than disabling TLS verification.

## 2. Resolve the deployed runtime image

Inspect the existing service rather than assuming an image tag:

```bash
gcloud run services describe odoo-sales \
  --project=odoo-reporting-487904 \
  --region=asia-southeast1 \
  --format='value(spec.template.spec.containers[0].image)'
```

## 3. Retrieve the Odoo key without displaying it

Create a temporary directory with `mktemp -d`. Use the exact returned directory in later commands; do not use an unresolved variable for cleanup.

```bash
mktemp -d /private/tmp/odoo-data-check.XXXXXX
gcloud secrets versions access latest \
  --secret=odoo-api-key \
  --project=odoo-reporting-487904 \
  --out-file=/private/tmp/EXACT-DIRECTORY/odoo-api-key
```

## 4. Run a read-only query in the production image

Mount the temporary key read-only and load it inside Python. Pass ordinary configuration through `.env`, replace `IMAGE` with the value from step 2, and output only aggregate results.

```bash
docker run --rm --env-file .env \
  --volume=/private/tmp/EXACT-DIRECTORY/odoo-api-key:/run/secrets/odoo-api-key:ro \
  IMAGE \
  uv run python -c "from odoo_sales.client import OdooClient; c=OdooClient.from_env(); c.password=open('/run/secrets/odoo-api-key').read().strip(); uid=c.authenticate(); print(c._models().execute_kw(c.db,uid,c.password,'sale.order','search_count',[[('date_order','>=','YYYY-MM-DD 00:00:00'),('date_order','<=','YYYY-MM-DD 23:59:59')]]))"
```

For revenue checks, request only `amount_total`, `amount_untaxed`, `state`, `currency_id`, and the relevant date fields, then summarize in memory.

## 5. Compare Firestore safely

Use the active `gcloud` credential internally without printing its access token. Query `sale_orders` or `sale_order_lines` by `date_order_date`, and read `synced_dates/{YYYY-MM-DD}` via explicit document references. Compare row count, total, and `synced_at` timestamps.

Key collections:

- `sale_orders`: order mirror keyed by Odoo order ID
- `sale_order_lines`: line mirror keyed by Odoo line ID
- `synced_dates`: per-day sync markers
- `allowed_users`: dashboard login allowlist

## 6. Clean up

Remove the exact temporary credential file and then the empty directory:

```bash
rm -f /private/tmp/EXACT-DIRECTORY/odoo-api-key
rmdir /private/tmp/EXACT-DIRECTORY
```

Report that cleanup completed. If cleanup fails, stop and surface the remaining exact path.
