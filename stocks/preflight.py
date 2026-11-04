"""Read-only runtime connectivity and asset eligibility probe."""
import argparse
import json
from stocks.broker import Broker
from stocks.strategy import SYMBOLS


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--credentials", required=True)
    args = p.parse_args()
    broker = Broker(args.credentials)
    account = broker.account()
    clock = broker.clock()
    valid = []
    for symbol in SYMBOLS:
        asset = broker.asset(symbol)
        if asset.get("symbol") != symbol or asset.get("status") != "active" or \
                asset.get("class") != "us_equity" or asset.get("tradable") is not True or \
                asset.get("fractionable") is not True:
            raise ValueError("Asset eligibility failed")
        quote = broker.quote(symbol)
        if not quote.get("t"):
            raise ValueError("Market data unavailable")
        valid.append(symbol)
    print(json.dumps({"paper_account_verified": True, "cash": account["cash"],
                      "equity": account["equity"], "market_open": clock["is_open"],
                      "next_open": clock["next_open"], "eligible_symbols": valid,
                      "iex_quotes_available": True, "orders_submitted": 0}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "error_type": type(exc).__name__}))
        raise SystemExit(1)
