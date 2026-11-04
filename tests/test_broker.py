import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stocks.broker import Broker
from stocks.runtime import HostGuard, ProcessLock


class TransportTests(unittest.TestCase):
    def test_news_pagination_must_complete(self):
        b = object.__new__(Broker)
        with patch.object(b, "request", side_effect=[{"news": [{"id": 1}], "next_page_token": "next"},
                                                   {"news": [{"id": 2}]}]) as request:
            self.assertEqual(b.news(["AAPL"], "start", "end"), [{"id": 1}, {"id": 2}])
            self.assertTrue(request.call_args.kwargs["data"])
        with patch.object(b, "request", return_value={"news": [], "next_page_token": "more"}):
            with self.assertRaises(ValueError):
                b.news(["AAPL"], "start", "end")

    def test_only_fixed_paper_or_data_hosts_and_no_data_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "fake.json"
            p.write_text(json.dumps({"key_id": "test", "secret_key": "test", "expected_account_number": "paper-test"}))
            b = Broker(p)
            with self.assertRaises(ValueError):
                b.request("https://api.alpaca.markets/v2/orders")
            with self.assertRaises(ValueError):
                b.request("/v2/stocks/bars", method="POST", data=True)
            with self.assertRaises(ValueError):
                b.request("/v1beta1/news", method="POST", data=True)
            with self.assertRaises(ValueError):
                b.request("/v1beta1/news", data=False)
            with patch.object(b.opener, "open", side_effect=RuntimeError("secret must not escape")) as call:
                with self.assertRaisesRegex(RuntimeError, "response withheld"):
                    b.request("/v2/orders", method="POST", payload={"symbol": "AAPL"})
                self.assertEqual(call.call_args.args[0].full_url, "https://paper-api.alpaca.markets/v2/orders")
                self.assertEqual(call.call_count, 1)

    def test_missing_host_metrics_blocks_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            guard = HostGuard(Path(tmp))
            self.assertFalse(guard())

    def test_host_pressure_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "meminfo").write_text("MemAvailable: 1000000 kB\n")
            (root / "stat").write_text("cpu 10 0 10 100 0 0 0 0\n")
            guard = HostGuard(root)
            self.assertFalse(guard())
            (root / "stat").write_text("cpu 11 0 11 200 1 0 0 0\n")
            self.assertTrue(guard())
            (root / "stat").write_text("cpu 12 0 12 210 90 0 0 0\n")
            self.assertFalse(guard())

    def test_single_writer_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = ProcessLock(Path(tmp) / "lock")
            try:
                with self.assertRaises(OSError):
                    ProcessLock(Path(tmp) / "lock")
            finally:
                first.close()


if __name__ == "__main__":
    unittest.main()
