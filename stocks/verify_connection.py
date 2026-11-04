"""Read-only paper account verification. Never prints credentials or raw API errors.

Usage: python -m stocks.verify_connection PRIVATE_JSON_PATH
Credentials JSON: key_id, secret_key, expected_account_number.
This program has no order submission or live endpoint support.
"""
import json
import sys
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect rejected")


def verify(path):
    credentials = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    for field in ("key_id", "secret_key", "expected_account_number"):
        if not isinstance(credentials.get(field), str) or not credentials[field].strip():
            raise ValueError("Missing credential configuration")
    request = urllib.request.Request(
        "https://paper-api.alpaca.markets/v2/account",
        headers={"APCA-API-KEY-ID": credentials["key_id"],
                 "APCA-API-SECRET-KEY": credentials["secret_key"]}, method="GET")
    with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
        account = json.load(response)
    if account.get("account_number") != credentials["expected_account_number"]:
        raise ValueError("Account identity mismatch")
    if account.get("status") != "ACTIVE":
        raise ValueError("Account is not active")
    if account.get("currency") != "USD":
        raise ValueError("USD account required")
    for flag in ("trading_blocked", "account_blocked", "trade_suspended_by_user"):
        if account.get(flag) is not False:
            raise ValueError("Account has unknown or blocked trading status")
    cash, equity = Decimal(account["cash"]), Decimal(account["equity"])
    if not cash.is_finite() or not equity.is_finite() or cash != 2000 or equity != 2000:
        raise ValueError("Initial balance differs from approved 2000 USD; review required")
    return {"paper_api_verified": True, "expected_account_matched": True,
            "cash": str(cash), "equity": str(equity), "orders_submitted": 0}


def main():
    try:
        if len(sys.argv) != 2:
            raise ValueError("Provide private credentials JSON path")
        print(json.dumps(verify(sys.argv[1])))
    except urllib.error.HTTPError as error:
        print(json.dumps({"verified": False, "http_status": error.code}))
        return 1
    except Exception:
        print(json.dumps({"verified": False, "reason": "Configuration, network, or account checks failed; no orders submitted"}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
