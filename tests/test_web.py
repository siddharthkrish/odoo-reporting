from __future__ import annotations

import unittest
from unittest.mock import patch

from odoo_sales import web


class Serializable:
    def to_dict(self) -> dict[str, bool]:
        return {"ok": True}


class FakeClient:
    def __init__(self) -> None:
        self.sales_hard_sync: bool | None = None
        self.lines_hard_sync: bool | None = None

    def get_sales_data(self, *args, hard_sync: bool = False, **kwargs):
        self.sales_hard_sync = hard_sync
        return [Serializable()]

    def get_order_lines(self, *args, hard_sync: bool = False, **kwargs):
        self.lines_hard_sync = hard_sync
        return [Serializable()]


class WebSyncTests(unittest.TestCase):
    def test_sales_route_forwards_hard_sync(self) -> None:
        client = FakeClient()
        with (
            patch.object(web, "_require_auth"),
            patch.object(web.OdooClient, "from_env", return_value=client),
        ):
            result = web.sales(
                object(),
                date_from="2026-07-01",
                date_to="2026-07-31",
                product=None,
                hard_sync=True,
            )

        self.assertEqual(result, [{"ok": True}])
        self.assertTrue(client.sales_hard_sync)

    def test_lines_route_forwards_hard_sync(self) -> None:
        client = FakeClient()
        with (
            patch.object(web, "_require_auth"),
            patch.object(web.OdooClient, "from_env", return_value=client),
        ):
            result = web.lines(
                object(),
                date_from="2026-07-01",
                date_to="2026-07-31",
                product=None,
                hard_sync=True,
            )

        self.assertEqual(result, [{"ok": True}])
        self.assertTrue(client.lines_hard_sync)


if __name__ == "__main__":
    unittest.main()
