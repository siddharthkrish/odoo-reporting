from __future__ import annotations

import argparse
import json

from .client import OdooClient


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch Odoo sales data by date range.")
    parser.add_argument("--from", dest="date_from", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of records")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    client = OdooClient.from_env()
    orders = client.get_sales_data(args.date_from, args.date_to, limit=args.limit)

    payload = [order.to_dict() for order in orders]
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
