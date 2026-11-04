"""Small fixed-host Alpaca paper adapter. No redirects, retries, or live endpoint."""
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from stocks.verify_connection import NoRedirect

PAPER = "https://paper-api.alpaca.markets"
DATA = "https://data.alpaca.markets"


class ApiError(RuntimeError):
    def __init__(self, status=0):
        self.status = status
        super().__init__(f"Alpaca request failed (HTTP {status or 'unknown'}); response withheld")


class Broker:
    def __init__(self, credentials):
        c = json.loads(Path(credentials).read_text(encoding="utf-8-sig"))
        self.expected = c["expected_account_number"]
        self.headers = {"APCA-API-KEY-ID": c["key_id"],
                        "APCA-API-SECRET-KEY": c["secret_key"], "Content-Type": "application/json"}
        self.opener = urllib.request.build_opener(NoRedirect)

    def request(self, path, *, method="GET", payload=None, data=False, params=None):
        if not path.startswith("/v2/") or "?" in path or ".." in path:
            raise ValueError("Invalid API path")
        if data and method != "GET":
            raise ValueError("Market data is read-only")
        url = (DATA if data else PAPER) + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        body = None if payload is None else json.dumps(payload, allow_nan=False).encode()
        req = urllib.request.Request(url, data=body, headers=self.headers, method=method)
        try:
            with self.opener.open(req, timeout=10) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raise ApiError(exc.code) from None
        except Exception:
            raise ApiError() from None

    def account(self):
        a = self.request("/v2/account")
        if a.get("account_number") != self.expected or a.get("currency") != "USD":
            raise ValueError("Paper account identity/currency mismatch")
        if a.get("status") != "ACTIVE" or any(a.get(k) is not False for k in
                ("trading_blocked", "account_blocked", "trade_suspended_by_user")):
            raise ValueError("Account is not ready")
        return a

    def clock(self):
        return self.request("/v2/clock")

    def positions(self):
        return self.request("/v2/positions")

    def orders(self):
        rows = self.request("/v2/orders", params={"status": "open", "limit": 500})
        if len(rows) >= 500:
            raise ValueError("Open order list may be truncated")
        return rows

    def order(self, client_id):
        return self.request("/v2/orders:by_client_order_id", params={"client_order_id": client_id})

    def asset(self, symbol):
        return self.request("/v2/assets/" + symbol)

    def quote(self, symbol):
        return self.request("/v2/stocks/" + symbol + "/quotes/latest", data=True,
                            params={"feed": "iex"})["quote"]

    def bars(self, symbols, start, end):
        result = {s: [] for s in symbols}
        params = {"symbols": ",".join(symbols), "timeframe": "1Min", "start": start,
                  "end": end, "feed": "iex", "adjustment": "raw", "limit": 10000}
        for _ in range(20):
            page = self.request("/v2/stocks/bars", data=True, params=params)
            for symbol, bars in (page.get("bars") or {}).items():
                if symbol in result:
                    result[symbol].extend(bars)
            if not page.get("next_page_token"):
                return result
            params["page_token"] = page["next_page_token"]
        raise ValueError("Bars pagination limit exceeded")

    def submit(self, payload):
        return self.request("/v2/orders", method="POST", payload=payload)

    def cancel(self, order_id):
        return self.request("/v2/orders/" + order_id, method="DELETE")
