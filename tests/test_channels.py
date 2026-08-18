from __future__ import annotations

import unittest
from datetime import datetime

from odoo_sales.client import (
    OdooClient,
    SaleOrder,
    _detect_channel,
    _pos_order_from_record,
)


class ChannelClient(OdooClient):
    def __init__(self) -> None:
        super().__init__("https://example.com", "db", "user", "key")

    def get_sales_data(self, *args, **kwargs) -> list[SaleOrder]:
        return [
            SaleOrder(1, "SO1", datetime(2025, 2, 12, 10), 20, "Isetan", "SGD", "Isetan"),
            SaleOrder(3, "SO3", datetime(2025, 2, 12, 11), 40, "Redmart", "SGD", "Redmart"),
        ]

    def _fetch_pos_orders_direct(self, *args, **kwargs) -> list[SaleOrder]:
        return [SaleOrder(-2, "POS1", datetime(2025, 2, 12, 9), 30, "Person", "SGD", "Glamorous Giving 2025")]

    def _fetch_amazon_fee_order_ids(self, *args, **kwargs) -> set[int]:
        return {1}


class ChannelTests(unittest.TestCase):
    def test_invoice_partner_is_used_as_channel(self) -> None:
        self.assertEqual(_detect_channel({}, "Redmart"), "Redmart")
        self.assertEqual(_detect_channel({}, "The Green Collective"), "The Green Collective")
        self.assertEqual(_detect_channel({}, "Isetan"), "Isetan")

    def test_pos_order_uses_point_of_sale_name_as_channel(self) -> None:
        order = _pos_order_from_record({
            "id": 42,
            "name": "Order 00042",
            "date_order": "2025-02-12 12:30:00",
            "amount_total": 125.5,
            "partner_id": [7, "Individual Customer"],
            "currency_id": [1, "SGD"],
            "config_id": [9, "Glamorous Giving 2025"],
        })

        self.assertEqual(order.channel, "Glamorous Giving 2025")
        self.assertEqual(order.id, -42)

    def test_channel_data_combines_and_sorts_regular_and_pos_sales(self) -> None:
        result = ChannelClient().get_channel_sales_data("2025-02-12", "2025-02-12")

        self.assertEqual(
            [order.channel for order in result],
            ["Glamorous Giving 2025", "Amazon", "Redmart"],
        )


if __name__ == "__main__":
    unittest.main()
