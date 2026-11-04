import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch

from stocks.broker import ApiError
from stocks.engine import Engine
from stocks.store import Store
from stocks.strategy import signal


class BrokerFake:
    expected = "test-paper"

    def __init__(self):
        self.submissions = []
        self.lookup = {}
        self.fail_submit = False
        self.cancellations = []

    def submit(self, payload):
        self.submissions.append(payload)
        if self.fail_submit:
            raise ApiError()
        row = dict(payload, id="order-1", status="new", filled_qty="0", filled_avg_price=None)
        self.lookup[payload["client_order_id"]] = row
        return row

    def order(self, client_id):
        if client_id not in self.lookup:
            raise ApiError(404)
        return self.lookup[client_id]

    def cancel(self, order_id):
        self.cancellations.append(order_id)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "ledger.sqlite")
        self.broker = BrokerFake()
        self.engine = Engine(self.broker, self.store, self.tmp.name, enabled=True)
        self.now = datetime.now(timezone.utc)
        self.payload = {"symbol": "AAPL", "side": "buy", "qty": "0.1", "type": "limit", "limit_price": "100"}

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_ambiguous_submission_blocks_replay_even_after_restart(self):
        self.broker.fail_submit = True
        with self.assertRaises(ApiError):
            self.engine.submit(self.now, "test", self.payload)
        self.store.close()
        self.store = Store(Path(self.tmp.name) / "ledger.sqlite")
        self.engine.store = self.store
        self.assertTrue(self.engine.reconcile())
        self.assertFalse(self.engine.submit(self.now, "test", self.payload))
        self.assertEqual(len(self.broker.submissions), 1)

    def test_partial_fill_retains_reservation_until_terminal(self):
        self.engine.submit(self.now, "test", self.payload)
        row = next(iter(self.broker.lookup.values()))
        row.update(status="partially_filled", filled_qty="0.03", filled_avg_price="100")
        self.engine.reconcile()
        self.assertEqual(len(self.store.unresolved()), 1)
        row.update(status="canceled")
        self.engine.reconcile()
        self.assertEqual(len(self.store.unresolved()), 0)
        self.assertEqual(self.store.order_rows()[0]["filled_qty"], "0.03")

    def test_cancel_does_not_assume_order_terminal(self):
        self.engine.submit(self.now, "test", self.payload)
        order = next(iter(self.broker.lookup.values()))
        self.engine.cancel(self.now, order)
        self.assertEqual(len(self.store.unresolved()), 1)
        self.assertEqual(self.broker.cancellations, ["order-1"])

    def test_sell_never_duplicates_or_shorts(self):
        pos = {"symbol": "AAPL", "qty": "0.03", "qty_available": "0.03"}
        self.assertTrue(self.engine.sell(self.now, pos, [], "test"))
        self.assertFalse(self.engine.sell(self.now, pos, [], "test"))
        self.assertEqual(self.broker.submissions[0]["qty"], "0.03")
        with self.assertRaises(ValueError):
            self.engine.sell(self.now, dict(pos, qty="-1"), [], "test")

    def test_foreign_orders_are_not_canceled(self):
        self.engine.cancel(self.now, {"id": "foreign", "client_order_id": "foreign"})
        self.assertEqual(self.broker.cancellations, [])

    def test_readonly_never_submits(self):
        self.engine.enabled = False
        self.assertFalse(self.engine.submit(self.now, "test", self.payload))
        self.assertEqual(self.broker.submissions, [])

    def test_durable_loss_lock_and_backup_restore(self):
        self.store.put("review_lock", True)
        self.store.checkpoint(Path(self.tmp.name) / "backups", "2026-11-03")
        restored = Store(Path(self.tmp.name) / "backups/daily-2026-11-03.sqlite")
        try:
            self.assertTrue(restored.get("review_lock"))
            self.assertEqual(restored.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        finally:
            restored.close()


class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.open = datetime(2026, 11, 3, 14, 30, tzinfo=timezone.utc)
        self.bars = [{"t": (self.open + timedelta(minutes=i)).isoformat(),
                      "o": 99, "h": 100, "l": 98, "c": 99, "v": 100, "vw": 99}
                     for i in range(21)]
        self.bars[-1].update(c=100.1, h=100.2, v=200, vw=100)
        self.now = self.open + timedelta(minutes=21, seconds=5)

    def test_signal_and_future_bar_exclusion(self):
        self.assertTrue(signal(self.bars, self.open, self.now)["buy"])
        future = dict(self.bars[-1], t=(self.now + timedelta(minutes=5)).isoformat(), c=999)
        self.assertEqual(signal(self.bars, self.open, self.now), signal(self.bars + [future], self.open, self.now))

    def test_missing_stale_and_duplicate_data(self):
        self.assertFalse(signal(self.bars[1:], self.open, self.now)["buy"])
        self.assertFalse(signal(self.bars, self.open, self.now + timedelta(minutes=5))["buy"])
        with self.assertRaises(ValueError):
            signal(self.bars + [self.bars[0]], self.open, self.now)

    def test_no_chasing_and_no_low_volume_entry(self):
        self.bars[-1]["c"] = 102
        self.assertFalse(signal(self.bars, self.open, self.now)["buy"])
        self.bars[-1].update(c=100.1, v=100)
        self.assertFalse(signal(self.bars, self.open, self.now)["buy"])


class TickBroker(BrokerFake):
    def __init__(self, now):
        super().__init__()
        self.now = now
        self.current_positions = []
        self.balance = "2000"
        self.open = True

    def account(self):
        return {"cash": self.balance, "equity": self.balance, "last_equity": "2000"}

    def clock(self):
        return {"is_open": self.open, "timestamp": self.now.isoformat(),
                "next_open": "2026-11-04T09:30:00-05:00"}

    def orders(self):
        return [r for r in self.lookup.values() if r["status"] not in ("filled", "canceled", "rejected")]

    def positions(self):
        return self.current_positions

    def request(self, path, **kwargs):
        return [{"date": "2026-11-03", "open": "09:30", "close": "13:00"}]

    def quote(self, symbol):
        raise ApiError(503)


class TickTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "ledger.sqlite")
        self.store.put("initialized", True)
        self.store.put("peak_close", "2000")
        self.store.put("canary", "passed")
        self.now = datetime(2026, 11, 3, 17, 51, tzinfo=timezone.utc)  # 12:51 ET, early close 13:00
        self.broker = TickBroker(self.now)
        self.engine = Engine(self.broker, self.store, self.tmp.name, enabled=True, host_ok=lambda: True)
        fixed = self.now

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)

        self.clock_patch = patch("stocks.engine.datetime", FixedDatetime)
        self.clock_patch.start()

    def tearDown(self):
        self.clock_patch.stop()
        self.store.close()
        self.tmp.cleanup()

    def own_position(self):
        cid = self.store.reserve("entry", {"symbol": "AAPL", "side": "buy"})
        self.store.record_order("entry", {"client_order_id": cid, "symbol": "AAPL", "side": "buy",
                                "status": "filled", "filled_qty": "1", "filled_avg_price": "100"})
        self.broker.current_positions = [{"symbol": "AAPL", "qty": "1", "qty_available": "1",
                                         "avg_entry_price": "100", "market_value": "100"}]

    def test_early_close_liquidates_before_session_end(self):
        self.own_position()
        self.engine.tick()
        self.assertEqual(len(self.broker.submissions), 1)
        self.assertEqual(self.broker.submissions[0]["side"], "sell")

    def test_closed_market_never_submits_and_flags_leftover_position(self):
        self.own_position()
        self.broker.open = False
        result = self.engine.tick()
        self.assertEqual(self.broker.submissions, [])
        self.assertIn("attention", result)
        self.assertTrue(self.store.get("review_lock"))

    def test_daily_loss_lock_persists_after_recovery(self):
        self.broker.balance = "1960"
        self.engine.tick()
        self.broker.balance = "2000"
        self.engine.tick()
        self.assertTrue(self.store.get("daily_lock"))

    def test_peak_drawdown_lock_persists(self):
        self.store.put("peak_close", "2200")
        self.engine.tick()
        self.assertTrue(self.store.get("review_lock"))

    def test_unknown_intent_blocks_entries(self):
        self.store.reserve("unknown", {"symbol": "AAPL", "side": "buy"})
        result = self.engine.tick()
        self.assertTrue(result["uncertain_order"])
        self.assertEqual(self.broker.submissions, [])

    def test_canary_passes_only_after_completed_roundtrip(self):
        self.store.put("canary", "pending")
        self.own_position()
        self.engine.tick()
        self.assertEqual(self.store.get("canary"), "pending")
        exit_order = next(iter(self.broker.lookup.values()))
        exit_order.update(status="filled", filled_qty="1", filled_avg_price="100")
        self.broker.current_positions = []
        self.engine.tick()
        self.assertEqual(self.store.get("canary"), "passed")

    def test_failed_canary_locks_entries(self):
        self.store.put("canary", "pending")
        cid = self.store.reserve("canary:buy", {"symbol": "AAPL", "side": "buy"})
        self.store.record_order("canary:buy", {"client_order_id": cid, "symbol": "AAPL", "side": "buy",
                                "status": "rejected", "filled_qty": "0", "filled_avg_price": None})
        self.engine.tick()
        self.assertEqual(self.store.get("canary"), "failed")
        self.assertTrue(self.store.get("review_lock"))

    def test_stale_position_after_filled_exit_cannot_create_short(self):
        self.own_position()
        cid = self.store.reserve("exit:AAPL:0", {"symbol": "AAPL", "side": "sell"})
        self.store.record_order("exit:AAPL:0", {"client_order_id": cid, "symbol": "AAPL", "side": "sell",
                                "status": "filled", "filled_qty": "1", "filled_avg_price": "100"})
        result = self.engine.tick()
        self.assertEqual(result["position_reconciliation_pending"], ["AAPL"])
        self.assertEqual(self.broker.submissions, [])


if __name__ == "__main__":
    unittest.main()
