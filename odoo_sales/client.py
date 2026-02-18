from __future__ import annotations

import os
import xmlrpc.client
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Iterable

from dotenv import load_dotenv


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


@dataclass(frozen=True)
class SaleOrder:
    id: int
    name: str
    date_order: datetime
    amount_total: float
    partner_name: str | None
    currency_name: str | None
    channel: str

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


class OdooClient:
    """Minimal XML-RPC client for Odoo sales data."""

    def __init__(self, url: str, db: str, username: str, password: str) -> None:
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.password = password
        self._uid: int | None = None

    @classmethod
    def from_env(cls) -> "OdooClient":
        load_dotenv()
        url = _require_env("ODOO_URL")
        db = _require_env("ODOO_DB")
        username = _require_env("ODOO_USERNAME")
        api_key = _require_env("ODOO_API_KEY")
        return cls(url=url, db=db, username=username, password=api_key)

    def authenticate(self) -> int:
        if self._uid is not None:
            return self._uid
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        uid = common.authenticate(self.db, self.username, self.password, {})
        if not uid:
            raise RuntimeError("Authentication failed; check ODOO_DB/ODOO_USERNAME/ODOO_API_KEY")
        self._uid = int(uid)
        return self._uid

    def get_sales_data(
        self,
        date_from: str | date | datetime,
        date_to: str | date | datetime,
        *,
        fields: Iterable[str] = DEFAULT_FIELDS,
        limit: int | None = None,
    ) -> list[SaleOrder]:
        uid = self.authenticate()
        date_from_dt = _coerce_to_datetime(date_from, is_start=True)
        date_to_dt = _coerce_to_datetime(date_to, is_start=False)

        domain = [
            ("date_order", ">=", _odoo_datetime_str(date_from_dt)),
            ("date_order", "<=", _odoo_datetime_str(date_to_dt)),
        ]
        kwargs: dict[str, Any] = {"fields": list(fields), "order": "date_order asc"}
        if limit is not None:
            kwargs["limit"] = limit

        models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        records = models.execute_kw(
            self.db,
            uid,
            self.password,
            "sale.order",
            "search_read",
            [domain],
            kwargs,
        )
        return [_sale_order_from_record(record) for record in records]


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
        id=int(record.get("id")),
        name=str(record.get("name")),
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
