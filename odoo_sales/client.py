from __future__ import annotations

import os
import xmlrpc.client
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable, cast

from dotenv import load_dotenv
from google.cloud import firestore

_SYNCED_DATES = "synced_dates"
_SALE_ORDERS = "sale_orders"
_SALE_ORDER_LINES = "sale_order_lines"
_BATCH_SIZE = 400  # stay under Firestore's 500-op batch limit

DEFAULT_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "date_order",
    "amount_total",
    "partner_id",
    "currency_id",
    # Channel detection fields
    "lazada_order_id",
    "woocommerce_order_id",
    "shopee_order_id",
    "origin",
)

ORDER_LINE_FIELDS: tuple[str, ...] = (
    "id",
    "order_id",
    "product_id",
    "product_uom_qty",
    "price_subtotal",
)


@dataclass(frozen=True)
class SaleOrder:
    id: int
    name: str
    date_order: datetime
    amount_total: float
    partner_name: str | None
    currency_name: str | None
    channel: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SaleOrder":
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            date_order=datetime.fromisoformat(data["date_order"]),
            amount_total=float(data["amount_total"]),
            partner_name=data.get("partner_name"),
            currency_name=data.get("currency_name"),
            channel=str(data.get("channel", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "date_order": self.date_order.isoformat(sep=" ", timespec="seconds"),
            "amount_total": self.amount_total,
            "partner_name": self.partner_name,
            "currency_name": self.currency_name,
            "channel": self.channel,
        }


@dataclass(frozen=True)
class SaleOrderLine:
    line_id: int
    order_id: int
    order_name: str
    date_order: datetime
    product_name: str
    sku: str | None
    quantity: float
    price_subtotal: float
    channel: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SaleOrderLine":
        return cls(
            line_id=int(data["line_id"]),
            order_id=int(data["order_id"]),
            order_name=str(data["order_name"]),
            date_order=datetime.fromisoformat(data["date_order"]),
            product_name=str(data["product_name"]),
            sku=data.get("sku"),
            quantity=float(data["quantity"]),
            price_subtotal=float(data["price_subtotal"]),
            channel=str(data.get("channel", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "line_id": self.line_id,
            "order_id": self.order_id,
            "order_name": self.order_name,
            "date_order": self.date_order.isoformat(sep=" ", timespec="seconds"),
            "product_name": self.product_name,
            "sku": self.sku,
            "quantity": self.quantity,
            "price_subtotal": self.price_subtotal,
            "channel": self.channel,
        }


class OdooClient:
    """Minimal XML-RPC client for Odoo sales data.

    Records are mirrored per-record in Firestore (sale_orders / sale_order_lines),
    keyed by day in synced_dates. On each request only missing days are fetched
    from Odoo; everything else is served from Firestore.
    """

    def __init__(
        self,
        url: str,
        db: str,
        username: str,
        password: str,
        firestore_project: str | None = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self._uid: int | None = None
        self._firestore_project = firestore_project
        self._fs: firestore.Client | None = None

    @classmethod
    def from_env(cls) -> "OdooClient":
        load_dotenv()
        return cls(
            url=_require_env("ODOO_URL"),
            db=_require_env("ODOO_DB"),
            username=_require_env("ODOO_USERNAME"),
            password=_require_env("ODOO_API_KEY"),
            firestore_project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        )

    def authenticate(self) -> int:
        if self._uid is not None:
            return self._uid
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        uid = common.authenticate(self.db, self.username, self.password, {})
        if not uid:
            raise RuntimeError("Authentication failed; check ODOO_DB/ODOO_USERNAME/ODOO_API_KEY")
        self._uid = cast(int, uid)
        return self._uid

    # ── Firestore helpers ──────────────────────────────────────────────────────

    def _get_firestore(self) -> firestore.Client | None:
        if self._fs is not None:
            return self._fs
        try:
            kwargs: dict[str, Any] = {}
            if self._firestore_project:
                kwargs["project"] = self._firestore_project
            self._fs = firestore.Client(**kwargs)
            return self._fs
        except Exception:
            return None

    def _get_synced_dates(self, fs: firestore.Client, date_from: date, date_to: date) -> set[date]:
        """Batch-fetch which dates in the range are already synced."""
        refs = []
        current = date_from
        while current <= date_to:
            refs.append(fs.collection(_SYNCED_DATES).document(current.isoformat()))
            current += timedelta(days=1)
        return {date.fromisoformat(doc.id) for doc in fs.get_all(refs) if doc.exists}

    def _missing_ranges(
        self, synced: set[date], date_from: date, date_to: date
    ) -> list[tuple[date, date]]:
        """Return contiguous date ranges within [date_from, date_to] not in synced."""
        ranges: list[tuple[date, date]] = []
        range_start: date | None = None
        current = date_from
        while current <= date_to:
            if current not in synced:
                if range_start is None:
                    range_start = current
            else:
                if range_start is not None:
                    ranges.append((range_start, current - timedelta(days=1)))
                    range_start = None
            current += timedelta(days=1)
        if range_start is not None:
            ranges.append((range_start, date_to))
        return ranges

    def _sync_range(self, fs: firestore.Client, date_from: date, date_to: date) -> None:
        """Fetch all orders and lines from Odoo for the date range and write to Firestore."""
        uid = self.authenticate()
        models = self._models()
        date_from_dt = datetime.combine(date_from, time.min)
        date_to_dt = datetime.combine(date_to, time.max)

        order_records = self._fetch_order_records(models, uid, date_from_dt, date_to_dt)
        orders = [_sale_order_from_record(r) for r in order_records]
        order_map = {o.id: o for o in orders}

        line_records = self._fetch_line_records(models, uid, date_from_dt, date_to_dt)
        sku_map = self._resolve_skus(models, uid, line_records)
        lines = _build_sale_order_lines(line_records, order_map, sku_map)

        self._write_to_firestore(fs, orders, lines, date_from, date_to)

    def _write_to_firestore(
        self,
        fs: firestore.Client,
        orders: list[SaleOrder],
        lines: list[SaleOrderLine],
        date_from: date,
        date_to: date,
    ) -> None:
        all_ops: list[tuple[Any, dict[str, Any]]] = []

        for order in orders:
            doc = order.to_dict()
            doc["date_order_date"] = order.date_order.date().isoformat()
            all_ops.append((fs.collection(_SALE_ORDERS).document(str(order.id)), doc))

        for line in lines:
            doc = line.to_dict()
            doc["date_order_date"] = line.date_order.date().isoformat()
            all_ops.append((fs.collection(_SALE_ORDER_LINES).document(str(line.line_id)), doc))

        current = date_from
        while current <= date_to:
            all_ops.append((
                fs.collection(_SYNCED_DATES).document(current.isoformat()),
                {"synced_at": datetime.now(timezone.utc).isoformat()},
            ))
            current += timedelta(days=1)

        for i in range(0, len(all_ops), _BATCH_SIZE):
            batch = fs.batch()
            for ref, data in all_ops[i:i + _BATCH_SIZE]:
                batch.set(ref, data)
            batch.commit()

    def _query_orders(self, fs: firestore.Client, date_from: date, date_to: date) -> list[SaleOrder]:
        docs = (
            fs.collection(_SALE_ORDERS)
            .where(filter=firestore.FieldFilter("date_order_date", ">=", date_from.isoformat()))
            .where(filter=firestore.FieldFilter("date_order_date", "<=", date_to.isoformat()))
            .stream()
        )
        return [SaleOrder.from_dict(d) for doc in docs if (d := doc.to_dict()) is not None]

    def _query_lines(self, fs: firestore.Client, date_from: date, date_to: date) -> list[SaleOrderLine]:
        docs = (
            fs.collection(_SALE_ORDER_LINES)
            .where(filter=firestore.FieldFilter("date_order_date", ">=", date_from.isoformat()))
            .where(filter=firestore.FieldFilter("date_order_date", "<=", date_to.isoformat()))
            .stream()
        )
        return [SaleOrderLine.from_dict(d) for doc in docs if (d := doc.to_dict()) is not None]

    # ── Odoo fetch helpers ─────────────────────────────────────────────────────

    def _models(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def _fetch_order_records(
        self,
        models: xmlrpc.client.ServerProxy,
        uid: int,
        date_from_dt: datetime,
        date_to_dt: datetime,
    ) -> list[dict[str, Any]]:
        domain: list[Any] = [
            ("date_order", ">=", _odoo_datetime_str(date_from_dt)),
            ("date_order", "<=", _odoo_datetime_str(date_to_dt)),
        ]
        return cast(list[dict[str, Any]], models.execute_kw(
            self.db, uid, self.password,
            "sale.order", "search_read",
            [domain],
            {"fields": list(DEFAULT_FIELDS), "order": "date_order asc"},
        ))

    def _fetch_line_records(
        self,
        models: xmlrpc.client.ServerProxy,
        uid: int,
        date_from_dt: datetime,
        date_to_dt: datetime,
    ) -> list[dict[str, Any]]:
        domain: list[Any] = [
            ("order_id.date_order", ">=", _odoo_datetime_str(date_from_dt)),
            ("order_id.date_order", "<=", _odoo_datetime_str(date_to_dt)),
        ]
        return cast(list[dict[str, Any]], models.execute_kw(
            self.db, uid, self.password,
            "sale.order.line", "search_read",
            [domain],
            {"fields": list(ORDER_LINE_FIELDS), "order": "order_id asc"},
        ))

    def _resolve_skus(
        self,
        models: xmlrpc.client.ServerProxy,
        uid: int,
        line_records: list[dict[str, Any]],
    ) -> dict[int, str | None]:
        product_ids = list({
            r["product_id"][0]
            for r in line_records
            if r.get("product_id") and r["product_id"] is not False
        })
        if not product_ids:
            return {}
        prod_records = cast(list[dict[str, Any]], models.execute_kw(
            self.db, uid, self.password,
            "product.product", "search_read",
            [[("id", "in", product_ids)]],
            {"fields": ["id", "default_code"]},
        ))
        return {int(p["id"]): p["default_code"] or None for p in prod_records}

    def _fetch_order_map(
        self,
        models: xmlrpc.client.ServerProxy,
        uid: int,
        line_records: list[dict[str, Any]],
    ) -> dict[int, SaleOrder]:
        order_ids = list({
            r["order_id"][0]
            for r in line_records
            if r.get("order_id") and r["order_id"] is not False
        })
        if not order_ids:
            return {}
        order_records = cast(list[dict[str, Any]], models.execute_kw(
            self.db, uid, self.password,
            "sale.order", "search_read",
            [[("id", "in", order_ids)]],
            {"fields": list(DEFAULT_FIELDS)},
        ))
        return {so.id: so for rec in order_records for so in [_sale_order_from_record(rec)]}

    # ── Odoo fallback (no Firestore) ───────────────────────────────────────────

    def _fetch_orders_direct(
        self,
        date_from_dt: datetime,
        date_to_dt: datetime,
        chips: list[str] | None,
        limit: int | None,
        fields: Iterable[str],
    ) -> list[SaleOrder]:
        uid = self.authenticate()
        models = self._models()
        domain: list[Any] = [
            ("date_order", ">=", _odoo_datetime_str(date_from_dt)),
            ("date_order", "<=", _odoo_datetime_str(date_to_dt)),
        ]
        if chips:
            domain = _build_product_domain(chips) + domain
        kwargs: dict[str, Any] = {"fields": list(fields), "order": "date_order asc"}
        if limit is not None:
            kwargs["limit"] = limit
        records = cast(list[dict[str, Any]], models.execute_kw(
            self.db, uid, self.password, "sale.order", "search_read", [domain], kwargs,
        ))
        return [_sale_order_from_record(r) for r in records]

    def _fetch_lines_direct(
        self,
        date_from_dt: datetime,
        date_to_dt: datetime,
        chips: list[str] | None,
        limit: int | None,
    ) -> list[SaleOrderLine]:
        uid = self.authenticate()
        models = self._models()
        domain: list[Any] = [
            ("order_id.date_order", ">=", _odoo_datetime_str(date_from_dt)),
            ("order_id.date_order", "<=", _odoo_datetime_str(date_to_dt)),
        ]
        if chips:
            domain = _build_product_domain_lines(chips) + domain
        kwargs: dict[str, Any] = {"fields": list(ORDER_LINE_FIELDS), "order": "order_id asc"}
        if limit is not None:
            kwargs["limit"] = limit
        line_records = cast(list[dict[str, Any]], models.execute_kw(
            self.db, uid, self.password, "sale.order.line", "search_read", [domain], kwargs,
        ))
        if not line_records:
            return []
        sku_map = self._resolve_skus(models, uid, line_records)
        order_map = self._fetch_order_map(models, uid, line_records)
        return _build_sale_order_lines(line_records, order_map, sku_map)

    # ── Public API ─────────────────────────────────────────────────────────────

    def get_sales_data(
        self,
        date_from: str | date | datetime,
        date_to: str | date | datetime,
        *,
        fields: Iterable[str] = DEFAULT_FIELDS,
        limit: int | None = None,
        product_filter: list[str] | str | None = None,
    ) -> list[SaleOrder]:
        date_from_dt = _coerce_to_datetime(date_from, is_start=True)
        date_to_dt = _coerce_to_datetime(date_to, is_start=False)
        chips = _normalize_chips(product_filter)

        fs = self._get_firestore()
        if fs is not None:
            synced = self._get_synced_dates(fs, date_from_dt.date(), date_to_dt.date())
            for range_start, range_end in self._missing_ranges(synced, date_from_dt.date(), date_to_dt.date()):
                self._sync_range(fs, range_start, range_end)

            orders = self._query_orders(fs, date_from_dt.date(), date_to_dt.date())
            if chips:
                lines = self._query_lines(fs, date_from_dt.date(), date_to_dt.date())
                matching_order_ids = {line.order_id for line in lines if _line_matches(line, chips)}
                orders = [o for o in orders if o.id in matching_order_ids]

            orders.sort(key=lambda o: o.date_order)
            if limit is not None:
                orders = orders[:limit]
            return orders

        return self._fetch_orders_direct(date_from_dt, date_to_dt, chips, limit, fields)

    def get_order_lines(
        self,
        date_from: str | date | datetime,
        date_to: str | date | datetime,
        *,
        product_filter: list[str] | str | None = None,
        limit: int | None = None,
    ) -> list[SaleOrderLine]:
        date_from_dt = _coerce_to_datetime(date_from, is_start=True)
        date_to_dt = _coerce_to_datetime(date_to, is_start=False)
        chips = _normalize_chips(product_filter)

        fs = self._get_firestore()
        if fs is not None:
            synced = self._get_synced_dates(fs, date_from_dt.date(), date_to_dt.date())
            for range_start, range_end in self._missing_ranges(synced, date_from_dt.date(), date_to_dt.date()):
                self._sync_range(fs, range_start, range_end)

            lines = self._query_lines(fs, date_from_dt.date(), date_to_dt.date())
            if chips:
                lines = [l for l in lines if _line_matches(l, chips)]

            lines.sort(key=lambda l: (l.date_order, l.order_id))
            if limit is not None:
                lines = lines[:limit]
            return lines

        return self._fetch_lines_direct(date_from_dt, date_to_dt, chips, limit)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _normalize_chips(product_filter: list[str] | str | None) -> list[str] | None:
    if not product_filter:
        return None
    if isinstance(product_filter, str):
        product_filter = [product_filter]
    chips = [c.strip() for c in product_filter if str(c).strip()]
    return chips or None


def _line_matches(line: SaleOrderLine, chips: list[str]) -> bool:
    name_lower = line.product_name.lower()
    sku_lower = (line.sku or "").lower()
    return any(chip.lower() in name_lower or chip.lower() in sku_lower for chip in chips)


def _build_sale_order_lines(
    line_records: list[dict[str, Any]],
    order_map: dict[int, SaleOrder],
    sku_map: dict[int, str | None],
) -> list[SaleOrderLine]:
    lines: list[SaleOrderLine] = []
    for r in line_records:
        order_rel = r.get("order_id")
        if not order_rel or order_rel is False:
            continue
        order = order_map.get(int(order_rel[0]))
        if order is None:
            continue
        product_rel = r.get("product_id")
        if product_rel and product_rel is not False:
            product_name = str(product_rel[1])
            sku = sku_map.get(int(product_rel[0]))
        else:
            product_name = "Unknown"
            sku = None
        lines.append(SaleOrderLine(
            line_id=int(r["id"]),
            order_id=order.id,
            order_name=order.name,
            date_order=order.date_order,
            product_name=product_name,
            sku=sku,
            quantity=float(r.get("product_uom_qty", 0.0)),
            price_subtotal=float(r.get("price_subtotal", 0.0)),
            channel=order.channel,
        ))
    return lines


def _require_env(key: str) -> str:
    value = os.getenv(key)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def _coerce_to_datetime(value: str | date | datetime, *, is_start: bool) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min if is_start else time.max)
    parsed = _parse_date_string(value)
    return datetime.combine(parsed, time.min if is_start else time.max)


def _parse_date_string(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Dates must be in ISO format: YYYY-MM-DD") from exc


def _odoo_datetime_str(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _sale_order_from_record(record: dict[str, Any]) -> SaleOrder:
    date_order_raw = record.get("date_order")
    if isinstance(date_order_raw, str):
        date_order = datetime.strptime(date_order_raw, "%Y-%m-%d %H:%M:%S")
    else:
        date_order = datetime.min

    partner_name = _relational_name(record.get("partner_id"))
    currency_name = _relational_name(record.get("currency_id"))
    channel = _detect_channel(record, partner_name)

    return SaleOrder(
        id=int(record["id"]),
        name=str(record["name"]),
        date_order=date_order,
        amount_total=float(record.get("amount_total", 0.0)),
        partner_name=partner_name,
        currency_name=currency_name,
        channel=channel,
    )


def _detect_channel(record: dict[str, Any], partner_name: str | None) -> str:
    if bool(record.get("lazada_order_id")):
        return "Lazada"
    woo_id = record.get("woocommerce_order_id")
    if woo_id and woo_id is not False and int(woo_id) != 0:
        return "Website"
    if bool(record.get("shopee_order_id")):
        return "Shopee"
    origin = str(record.get("origin") or "")
    if origin.lower().startswith("amazon"):
        return "Amazon"
    return partner_name or "Direct"


def _relational_name(value: Any) -> str | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return str(value[1])
    return None


def _build_product_domain(filters: list[str]) -> list[Any]:
    """OR filter on sale.order via order_line traversal (name + default_code per chip)."""
    conditions: list[Any] = []
    for chip in filters:
        conditions.append(("order_line.product_id.name", "ilike", chip))
        conditions.append(("order_line.product_id.default_code", "ilike", chip))
    if not conditions:
        return []
    return ["|"] * (len(conditions) - 1) + conditions


def _build_product_domain_lines(filters: list[str]) -> list[Any]:
    """OR filter on sale.order.line (product_id.name + product_id.default_code per chip)."""
    conditions: list[Any] = []
    for chip in filters:
        conditions.append(("product_id.name", "ilike", chip))
        conditions.append(("product_id.default_code", "ilike", chip))
    if not conditions:
        return []
    return ["|"] * (len(conditions) - 1) + conditions
