import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from stocks.journal import Journal
from stocks.risk import Blocked, Buy, PAPER_ENDPOINT, Snapshot, validate_buy


class RiskTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 15, tzinfo=timezone.utc)
        self.state = Snapshot(PAPER_ENDPOINT, "paper-test", self.now, D(2000), D(2000),
                              D(2000), D(2000), {}, {}, True, True, True, False, False, False)
        self.buy = Buy("SPY", D("0.5"), D(600), self.now, D("0.001"))

    def validate(self, state=None, buy=None):
        return validate_buy(buy or self.buy, state or self.state, expected_account="paper-test",
                            allowed_symbols=frozenset({"SPY"}), now=self.now)

    def test_valid_paper_order(self):
        self.assertEqual(self.validate(), D(300))

    def test_reject_unready_or_wrong_account(self):
        cases = [dict(endpoint="https://api.alpaca.markets"), dict(account_id="other"),
                 dict(reconciled=False), dict(market_open=False), dict(account_active=False),
                 dict(trading_blocked=True), dict(review_lock=True), dict(daily_lock=True)]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(Blocked):
                self.validate(replace(self.state, **change))

    def test_pending_orders_reserve_cash_and_slots(self):
        with self.assertRaises(Blocked):
            self.validate(replace(self.state, cash=D(500), pending_buys={"AAPL": D(300)}))
        with self.assertRaises(Blocked):
            self.validate(replace(self.state, pending_buys={s: D(10) for s in "ABCD"}))

    def test_existing_and_pending_exposure_counts(self):
        with self.assertRaises(Blocked):
            self.validate(replace(self.state, positions={"SPY": D(80)}, pending_buys={"SPY": D(30)}))

    def test_loss_thresholds_and_persistent_locks(self):
        for change in (dict(equity=D(1960)), dict(peak_close_equity=D(2200)),
                       dict(review_lock=True, equity=D(2100))):
            with self.subTest(change=change), self.assertRaises(Blocked):
                self.validate(replace(self.state, **change))

    def test_no_borrowing_even_if_cash_is_inconsistent(self):
        with self.assertRaises(Blocked):
            self.validate(replace(self.state, positions={"AAPL": D(1800)}))

    def test_bad_market_data(self):
        for change in (dict(quote_at=self.now - timedelta(seconds=16)),
                       dict(quote_at=self.now + timedelta(seconds=1)),
                       dict(quote_at=self.now.replace(tzinfo=None)),
                       dict(spread_fraction=D("0.006"))):
            with self.subTest(change=change), self.assertRaises(Blocked):
                self.validate(buy=replace(self.buy, **change))
        with self.assertRaises(Blocked):
            self.validate(replace(self.state, observed_at=self.now - timedelta(seconds=61)))

    def test_malformed_and_disallowed_orders(self):
        for change in (dict(symbol="UNKNOWN"), dict(quantity=D(-1)), dict(quantity=D(0)),
                       dict(quantity=D("NaN")), dict(limit_price=D("Infinity")),
                       dict(quantity=1.0), dict(quantity=D(1))):
            with self.subTest(change=change), self.assertRaises(Blocked):
                self.validate(buy=replace(self.buy, **change))

    def test_negative_cash_or_short_position_blocks(self):
        for change in (dict(cash=D(-1)), dict(positions={"AAPL": D(-1)})):
            with self.assertRaises(Blocked):
                self.validate(replace(self.state, **change))


class JournalTests(unittest.TestCase):
    def test_unknown_order_cannot_be_retried_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            journal = Journal(path)
            client_id = journal.reserve("decision-1", {"symbol": "SPY", "dollars": "300"})
            journal.mark("decision-1", "unknown")
            journal.close()
            recovered = Journal(path)
            try:
                self.assertEqual(recovered.unresolved()[0][1], client_id)
                with self.assertRaises(sqlite3.IntegrityError):
                    recovered.reserve("decision-1", {"symbol": "SPY", "dollars": "300"})
            finally:
                recovered.close()

    def test_consistent_backup_restores_pending_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Journal(Path(directory) / "ledger.sqlite")
            journal.reserve("decision-2", {"symbol": "SPY"})
            backup = Path(directory) / "backup.sqlite"
            journal.backup(backup)
            journal.close()
            restored = Journal(backup)
            try:
                self.assertEqual(restored.unresolved()[0][0], "decision-2")
                self.assertEqual(restored.db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            finally:
                restored.close()


if __name__ == "__main__":
    unittest.main()
