from __future__ import annotations

import argparse

from odoo_sales.client import OdooClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Test script for fetching Odoo sales data by date range."
    )
    parser.add_argument("--from", dest="date_from", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=10, help="Limit number of records")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    client = OdooClient.from_env()
    orders = client.get_sales_data(args.date_from, args.date_to, limit=args.limit)

    print(f"Fetched {len(orders)} sale orders")
    for order in orders:
        print(f"{order.date_order} | {order.name} | {order.amount_total:.2f} | {order.partner_name}")


if __name__ == "__main__":
    main()
