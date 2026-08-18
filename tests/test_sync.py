from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone
from typing import Any

from odoo_sales.client import OdooClient, SaleOrder


def order(order_id: int) -> SaleOrder:
    return SaleOrder(
        id=order_id,
        name=f"SO{order_id}",
        date_order=datetime(2026, 7, order_id),
        amount_total=float(order_id),
        partner_name=None,
        currency_name="SGD",
        channel="Direct",
    )


class SyncClient(OdooClient):
    def __init__(self, query_results: list[list[SaleOrder]], remote_count: int) -> None:
        super().__init__("https://example.com", "db", "user", "key")
        self.query_results = query_results
        self.remote_count = remote_count
        self.remote_count_calls = 0
        self.sync_calls: list[tuple[date, date, bool]] = []
        self.fake_firestore = object()

    def _get_firestore(self) -> Any:
        return self.fake_firestore

    def _get_synced_dates(self, fs: Any, date_from: date, date_to: date) -> set[date]:
        return {date_from}

    def _query_orders(self, fs: Any, date_from: date, date_to: date) -> list[SaleOrder]:
        return self.query_results.pop(0)

    def _remote_count(
        self,
        model: str,
        date_field: str,
        date_from_dt: datetime,
        date_to_dt: datetime,
    ) -> int:
        self.remote_count_calls += 1
        return self.remote_count

    def _sync_range(
        self,
        fs: Any,
        date_from: date,
        date_to: date,
        *,
        reconcile: bool = False,
    ) -> None:
        self.sync_calls.append((date_from, date_to, reconcile))


class FakeDoc:
    def __init__(self, doc_id: str) -> None:
        self.id = doc_id
        self.reference = f"ref:{doc_id}"


class FakeBatch:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.committed = False

    def delete(self, ref: str) -> None:
        self.deleted.append(ref)

    def commit(self) -> None:
        self.committed = True


class FakeFirestore:
    def __init__(self) -> None:
        self.batches: list[FakeBatch] = []

    def batch(self) -> FakeBatch:
        batch = FakeBatch()
        self.batches.append(batch)
        return batch


class SyncTests(unittest.TestCase):
    def test_count_match_reuses_cached_orders(self) -> None:
        client = SyncClient([[order(1)]], remote_count=1)

        result = client.get_sales_data("2026-07-01", "2026-07-01")

        self.assertEqual([item.id for item in result], [1])
        self.assertEqual(client.sync_calls, [])
        self.assertEqual(client.remote_count_calls, 1)

    def test_count_mismatch_reconciles_full_range(self) -> None:
        client = SyncClient([[order(1)], [order(1), order(2)]], remote_count=2)

        result = client.get_sales_data("2026-07-01", "2026-07-01")

        self.assertEqual([item.id for item in result], [1, 2])
        self.assertEqual(
            client.sync_calls,
            [(date(2026, 7, 1), date(2026, 7, 1), True)],
        )

    def test_hard_sync_reconciles_even_when_counts_match(self) -> None:
        client = SyncClient([[order(1)]], remote_count=1)

        client.get_sales_data("2026-07-01", "2026-07-01", hard_sync=True)

        self.assertEqual(
            client.sync_calls,
            [(date(2026, 7, 1), date(2026, 7, 1), True)],
        )
        self.assertEqual(client.remote_count_calls, 0)

    def test_reconciliation_deletes_documents_missing_from_odoo(self) -> None:
        client = SyncClient([], remote_count=0)
        fs = FakeFirestore()
        client._date_range_documents = lambda *args: [FakeDoc("1"), FakeDoc("2")]  # type: ignore[method-assign]

        client._delete_stale_documents(
            fs, "sale_orders", date(2026, 7, 1), date(2026, 7, 31), {"2"}
        )

        self.assertEqual(len(fs.batches), 1)
        self.assertEqual(fs.batches[0].deleted, ["ref:1"])
        self.assertTrue(fs.batches[0].committed)

    def test_future_dates_are_not_marked_synced(self) -> None:
        client = SyncClient([], remote_count=0)
        fs = FakeFirestore()
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)

        client._write_to_firestore(fs, [], [], tomorrow, tomorrow + timedelta(days=5))

        self.assertEqual(fs.batches, [])


if __name__ == "__main__":
    unittest.main()
