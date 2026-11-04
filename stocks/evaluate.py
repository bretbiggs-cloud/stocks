"""Diagnostic historical replay, deliberately conservative fills; not a performance promise.

Independent single-symbol trades, then chronological portfolio cash/slot accounting.
Signals use completed bars only; fills occur no sooner than the next minute.
IEX minute OHLC cannot reproduce quotes, latency, queue priority or actual fills.
"""
import argparse
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from stocks.broker import Broker
from stocks.engine import ET
from stocks.strategy import SYMBOLS, VERSION, signal, stamp, number


def replay(bars, opening, closing):
    completed = []
    position = None
    trades = []
    attempted = False
    for i, bar in enumerate(bars):
        now = stamp(bar["t"])
        if not opening <= now < closing:
            continue
        if position:
            entry, at = position
            reason = None
            price = None
            if number(bar["l"]) <= entry * D(".99"):
                price = min(number(bar["o"]), entry * D(".99"))
                reason = "stop"
            elif number(bar["h"]) >= entry * D("1.02"):
                price = entry * D("1.02")
                reason = "target"
            elif now >= closing - timedelta(minutes=10):
                price, reason = number(bar["o"]), "session_end"
            if price:
                trades.append({"entry_time": at.isoformat(), "exit_time": now.isoformat(),
                               "entry": str(entry), "exit": str(price), "reason": reason})
                position = None
        if not attempted and now < closing - timedelta(minutes=30) and len(completed) >= 21:
            choice = signal(completed, opening, now)
            if choice["buy"]:
                attempted = True
                limit = number(choice["close"]) * D("1.0005")
                # Conservative: require the following bar to open at/below the limit.
                if number(bar["o"]) <= limit:
                    position = (number(bar["o"]), now)
        completed.append(bar)
    if position:
        # Missing closing bars is evidence of missing data, not assumed profit.
        return trades, True
    return trades, False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    broker = Broker(args.credentials)
    clock = broker.clock()
    end = stamp(clock["timestamp"]).astimezone(ET).date()
    start = end - timedelta(days=21)
    calendar = broker.request("/v2/calendar", params={"start": start.isoformat(), "end": end.isoformat()})[-10:]
    all_trades, missing = [], []
    for day in calendar:
        opening = datetime.fromisoformat(day["date"] + "T" + day["open"]).replace(tzinfo=ET)
        closing = datetime.fromisoformat(day["date"] + "T" + day["close"]).replace(tzinfo=ET)
        if closing > stamp(clock["timestamp"]):
            continue
        data = broker.bars(SYMBOLS, opening.isoformat(), closing.isoformat())
        for symbol in SYMBOLS:
            trades, incomplete = replay(data[symbol], opening, closing)
            all_trades.extend(dict(t, symbol=symbol) for t in trades)
            if incomplete or len(data[symbol]) < 100:
                missing.append({"day": day["date"], "symbol": symbol})
    # Enforce four entries per day; this diagnostic does not optimize parameters.
    selected, days = [], defaultdict(int)
    for t in sorted(all_trades, key=lambda t: (t["entry_time"], t["symbol"])):
        day = t["entry_time"][:10]
        if days[day] >= 4:
            continue
        active = [x for x in selected if x["exit_time"] > t["entry_time"]]
        if len(active) >= 4:
            continue
        qty = D(400) / D(t["entry"])
        gross = qty * (D(t["exit"]) - D(t["entry"]))
        modeled = qty * (D(t["exit"]) + D(t["entry"])) * D(".001")
        t.update(gross_pnl=str(gross), execution_cost=str(modeled), modeled_pnl=str(gross - modeled))
        selected.append(t)
        days[day] += 1
    report = {"strategy": VERSION, "sessions": len(calendar), "trades": selected,
              "gross_pnl": str(sum((D(t["gross_pnl"]) for t in selected), D(0))),
              "modeled_pnl": str(sum((D(t["modeled_pnl"]) for t in selected), D(0))),
              "missing_data": missing,
              "limitations": "Diagnostic only; fixed current universe has selection bias. Minute IEX bars omit market-wide quotes, fills, latency and exact execution behavior. Not full engine replay; loss locks, live spread gates, canary and host deferrals are not modeled. Electricity unknown. No parameters fitted to this sample."}
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("trades", "missing_data")}, indent=2))
    print(json.dumps({"trade_count": len(selected), "missing_symbol_days": len(missing)}))


if __name__ == "__main__":
    main()
