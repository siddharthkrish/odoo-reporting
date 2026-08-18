from __future__ import annotations

import unittest
from datetime import datetime

from odoo_sales.client import (
    OdooClient,
    SaleOrder,
    SaleOrderLine,
    _build_pos_order_lines,
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

    def get_order_lines(self, *args, **kwargs) -> list[SaleOrderLine]:
        return [
            SaleOrderLine(10, 1, "SO1", datetime(2025, 2, 12, 10), "Tea", "TEA", 2, 20, "Isetan"),
            SaleOrderLine(11, 3, "SO3", datetime(2025, 2, 12, 11), "Cup", "CUP", 1, 40, "Redmart"),
        ]

    def _fetch_pos_lines_direct(self, *args, **kwargs) -> list[SaleOrderLine]:
        return [
            SaleOrderLine(-12, -2, "POS1", datetime(2025, 2, 12, 9), "Bag", "BAG", 3, 30, "Glamorous Giving 2025")
        ]


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

    def test_pos_line_uses_product_sku_quantity_sales_and_pos_channel(self) -> None:
        order = SaleOrder(
            -42,
            "Order 00042",
            datetime(2025, 2, 12, 12, 30),
            125.5,
            "Individual Customer",
            "SGD",
            "Glamorous Giving 2025",
        )

        lines = _build_pos_order_lines(
            [{
                "id": 99,
                "order_id": [42, "Order 00042"],
                "product_id": [7, "Gift Bag"],
                "qty": 3,
                "price_subtotal": 75.0,
            }],
            {42: order},
            {7: "BAG-01"},
        )

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0].line_id, -99)
        self.assertEqual(lines[0].order_id, -42)
        self.assertEqual(lines[0].product_name, "Gift Bag")
        self.assertEqual(lines[0].sku, "BAG-01")
        self.assertEqual(lines[0].quantity, 3)
        self.assertEqual(lines[0].price_subtotal, 75.0)
        self.assertEqual(lines[0].channel, "Glamorous Giving 2025")

    def test_channel_data_combines_and_sorts_regular_and_pos_sales(self) -> None:
        result = ChannelClient().get_channel_sales_data("2025-02-12", "2025-02-12")

        self.assertEqual(
            [order.channel for order in result],
            ["Glamorous Giving 2025", "Amazon", "Redmart"],
        )

    def test_channel_lines_combine_regular_and_pos_products(self) -> None:
        result = ChannelClient().get_channel_order_lines("2025-02-12", "2025-02-12")

        self.assertEqual(
            [(line.product_name, line.channel) for line in result],
            [("Bag", "Glamorous Giving 2025"), ("Tea", "Amazon"), ("Cup", "Redmart")],
        )


if __name__ == "__main__":
    unittest.main()
