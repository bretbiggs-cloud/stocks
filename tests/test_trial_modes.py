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

    def test_news_trial_isolated_and_failure_still_allows_exit(self):
        opening = self.now - timedelta(minutes=30)
        closing = self.now + timedelta(hours=3)
        article = dict(id=7, headline="Company announcement", source="benzinga",
                       url="https://example.com/news", symbols=["AAPL"],
                       created_at=self.now.isoformat(), updated_at=self.now.isoformat())
        self.broker.news = lambda *args: [article]
        key = "shadow:news-volume-v1:" + opening.date().isoformat()
        with patch("stocks.shadow.signal", side_effect=lambda bars, *args: {"buy": bool(bars), "volume_ratio": "2"}):
            run_shadow(self.broker, self.store, self.root, self.now, opening, closing,
                       allow_entries=True, news_filter=True)
            self.assertIn("AAPL", self.store.get(key)["positions"])
            self.assertIsNone(self.store.get("shadow:" + opening.date().isoformat()))
            self.broker.news = lambda *args: (_ for _ in ()).throw(RuntimeError())
            self.broker.bid = 103
            run_shadow(self.broker, self.store, self.root, self.now + timedelta(minutes=6),
                       opening, closing, allow_entries=True, news_filter=True)
        result = self.store.get(key)
        self.assertEqual(result["positions"], {})
        self.assertEqual(len(result["trades"]), 1)
        self.assertFalse(result["news_status"]["ok"])
        self.assertEqual(result["trades"][0]["entry_evidence"]["news_ids"], [7])
        self.assertEqual(self.broker.calls, [])

    def test_news_rejects_stale_future_and_wrong_symbol(self):
        from stocks.news import eligible_articles
        row = dict(id=1, headline="News", source="benzinga", url="https://example.com",
                   symbols=["AAPL"], created_at=self.now.isoformat(),
                   updated_at=self.now.isoformat(), first_observed_at=self.now.isoformat())
        self.assertEqual(len(eligible_articles([row, row], "AAPL", self.now)), 1)
        self.assertEqual(eligible_articles([row], "MSFT", self.now), [])
        for field, value in (("created_at", self.now-timedelta(hours=3)),
                             ("updated_at", self.now+timedelta(minutes=1)),
                             ("first_observed_at", self.now+timedelta(minutes=1))):
            self.assertEqual(eligible_articles([dict(row, **{field: value.isoformat()})], "AAPL", self.now), [])

    def test_news_failure_blocks_new_mock_entries(self):
        with patch("stocks.shadow.signal", return_value={"buy": True, "volume_ratio": "2"}):
            run_shadow(self.broker, self.store, self.root, self.now,
                       self.now-timedelta(minutes=30), self.now+timedelta(hours=3),
                       allow_entries=True, news_filter=True)
        result = self.store.get("shadow:news-volume-v1:" + (self.now-timedelta(minutes=30)).date().isoformat())
        self.assertEqual(result["positions"], {})
        self.assertTrue(all(d["reason"] == "news_unavailable" for d in result["latest_decisions"]))
        self.assertEqual(self.broker.calls, [])

    def test_paper_research_requires_news_and_date_gate(self):
        from decimal import Decimal as D
        e = Engine(self.broker, self.store, self.root, enabled=True, strategy_enabled=True)
        opening = self.now - timedelta(minutes=30)
        args = (self.now, opening, {"cash": "2000"}, [], [], D(2000), D(2000))
        with patch("stocks.engine.signal", side_effect=lambda *a: {"buy": True, "volume_ratio": "2"}), patch.object(e, "buy") as buy:
            e.research(*args)
            buy.assert_not_called()
            self.broker.news = lambda *a: []
            self.store.put("news-volume-v1:news", None)
            e.research(*args)
            buy.assert_not_called()
            self.broker.news = lambda *a: [dict(id=9, headline="News", source="benzinga", url="https://example.com",
                symbols=["AAPL"], created_at=self.now.isoformat(), updated_at=self.now.isoformat())]
            self.store.put("news-volume-v1:news", None)
            e.research(*args)
            self.assertEqual(buy.call_count, 1)
            self.assertEqual(buy.call_args.args[4], "AAPL")
        p = {"symbol": "AAPL", "side": "buy", "qty": ".1", "type": "limit", "limit_price": "100"}
        with self.assertRaises(ValueError):
            e.submit(self.now, "news-volume-v1:test", p)
        e.strategy_date = self.now.astimezone(ET).date().isoformat()
        self.assertTrue(e.submit(self.now, "news-volume-v1:test", p))

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
