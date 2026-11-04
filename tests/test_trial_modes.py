from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stocks.engine import Engine, ET
from stocks.shadow import run_shadow
from stocks.store import Store
from stocks.strategy import SYMBOLS


class Fake:
    def __init__(self):
        self.calls = []
        self.bid = 99.99

    def submit(self, payload):
        self.calls.append(payload)
        return dict(payload, status="new", filled_qty="0")

    def quote(self, symbol):
        return {"bp": self.bid, "ap": self.bid + .01, "t": datetime.now(timezone.utc).isoformat()}

    def bars(self, *args):
        return {s: [1] if s == "AAPL" else [] for s in SYMBOLS}


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "reports").mkdir()
        self.store = Store(self.root / "ledger.sqlite")
        self.broker = Fake()
        self.now = datetime.now(timezone.utc)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_canary_authorization_does_not_enable_strategy_orders(self):
        e = Engine(self.broker, self.store, self.root, enabled=True,
                   canary_date=self.now.astimezone(ET).date().isoformat())
        p = {"side": "buy", "symbol": "AAPL", "type": "limit", "qty": ".1", "limit_price": "100"}
        self.assertTrue(e.submit(self.now, "canary:buy", p))
        with self.assertRaises(ValueError):
            e.submit(self.now, "orb-v1:attempt", p)
        self.assertEqual(len(self.broker.calls), 1)

    def test_canary_date_and_amount_limits(self):
        e = Engine(self.broker, self.store, self.root, enabled=True, canary_date="2000-01-01")
        p = {"side": "buy", "symbol": "AAPL", "type": "limit", "qty": ".1", "limit_price": "100"}
        with self.assertRaises(ValueError):
            e.submit(self.now, "canary:buy", p)
        e.canary_date = self.now.astimezone(ET).date().isoformat()
        with self.assertRaises(ValueError):
            e.submit(self.now, "canary:buy", dict(p, qty="1"))
        self.assertEqual(self.broker.calls, [])

    def test_mock_trade_and_exit_never_reach_broker_submit(self):
        opening = self.now - timedelta(minutes=30)
        closing = self.now + timedelta(hours=3)
        with patch("stocks.shadow.signal", side_effect=lambda bars, *args: {"buy": bool(bars), "volume_ratio": "2"}):
            run_shadow(self.broker, self.store, self.root, self.now, opening, closing, allow_entries=True)
            state = self.store.get("shadow:" + opening.date().isoformat())
            self.assertIn("AAPL", state["positions"])
            self.broker.bid = 103
            run_shadow(self.broker, self.store, self.root, self.now, opening, closing, allow_entries=False)
        state = self.store.get("shadow:" + opening.date().isoformat())
        self.assertEqual(state["positions"], {})
        self.assertEqual(len(state["trades"]), 1)
        self.assertEqual(self.broker.calls, [])
        self.assertEqual(state["completed_trades"], 1)
        self.assertEqual(state["wins"], 1)
        self.assertEqual(state["win_rate"], "1")
        from decimal import Decimal as D
        self.assertEqual(D(state["unrealized_modeled_pnl"]), 0)
        self.assertEqual(D(state["total_modeled_pnl"]), D(state["equity"]) - 2000)
        self.assertGreater(D(state["modeled_execution_cost"]), 0)
        self.assertFalse(state["net_profit_verified"])
