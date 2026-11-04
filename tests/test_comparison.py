from collections import deque
from datetime import datetime, timedelta
import unittest

from stocks.compare import features, entry, run, confidence
from stocks.engine import ET
from stocks.strategy import SYMBOLS, signal


class ComparisonTests(unittest.TestCase):
    def sample(self):
        opening = datetime(2026, 7, 1, 9, 30, tzinfo=ET)
        rows = [{"t": (opening + timedelta(minutes=i)).isoformat(), "o": 99.0,
                 "h": 100.0, "l": 98.0, "c": 99.0, "v": 100, "vw": 99.0} for i in range(390)]
        rows[20].update(o=99, c=100.1, h=100.2, v=200, vw=100)
        day = {"date": "2026-07-01", "open": "09:30", "close": "16:00"}
        return opening, day, rows

    def test_baseline_signal_matches_existing_rules(self):
        opening, day, rows = self.sample()
        prepared = features(day, {s: rows for s in SYMBOLS}, {s: deque(maxlen=14) for s in SYMBOLS})
        for i in range(15, 35):
            original = signal(rows[:i+1], opening, opening + timedelta(minutes=i+1))["buy"]
            self.assertEqual(entry("orb_baseline", prepared["symbols"]["AAPL"], i) is not None, original)

    def test_orders_fill_after_signal_and_stop_applies_to_entry_bar(self):
        _, day, rows = self.sample()
        rows[21].update(o=100.1, h=104, l=95, c=100)
        prepared = features(day, {s: rows for s in SYMBOLS}, {s: deque(maxlen=14) for s in SYMBOLS})
        result = run("orb_baseline", [prepared])
        self.assertEqual(result["trade_count"], 4)
        for trade in result["trades"]:
            self.assertEqual(trade["entry_minute"], 21)
            self.assertEqual(trade["exit_minute"], 21)
            self.assertEqual(trade["reason"], "stop")
            self.assertLess(trade["pnl"], 0)
        self.assertLess(run("orb_baseline", [prepared], .002)["net_modeled_pnl"], result["net_modeled_pnl"])

    def test_missing_next_bar_cannot_fill(self):
        _, day, rows = self.sample()
        rows = [r for i, r in enumerate(rows) if i != 21]
        prepared = features(day, {s: rows for s in SYMBOLS}, {s: deque(maxlen=14) for s in SYMBOLS})
        self.assertEqual(run("orb_baseline", [prepared])["trade_count"], 0)

    def test_future_bar_cannot_change_earlier_signal(self):
        _, day, rows = self.sample()
        history = lambda: {s: deque(maxlen=14) for s in SYMBOLS}
        before = features(day, {s: rows for s in SYMBOLS}, history())
        rows[100].update(c=999, h=1000, v=100000)
        after = features(day, {s: rows for s in SYMBOLS}, history())
        self.assertEqual(entry("orb_baseline", before["symbols"]["AAPL"], 20),
                         entry("orb_baseline", after["symbols"]["AAPL"], 20))

    def test_bootstrap_deterministic_and_detects_negative_sample(self):
        days = [{"pnl": -1.0}] * 50
        self.assertEqual(confidence(days), -1.0)


if __name__ == "__main__":
    unittest.main()
