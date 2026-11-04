"""Frozen, offline-only candidate comparison. Never submits an order.

See .docs/strategy-comparison-protocol.md. Uses float arithmetic for research,
not the Decimal execution validator. All fills occur after signal formation.
"""
import argparse
from collections import deque
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import random
import statistics

from stocks.broker import Broker
from stocks.engine import ET
from stocks.strategy import SYMBOLS, stamp

CANDIDATES = ("orb_baseline", "relative_volume_orb", "noise_momentum")


def load_data(broker, root):
    root.mkdir(parents=True, exist_ok=True)
    clock = broker.clock()
    today = stamp(clock["timestamp"]).astimezone(ET).date()
    calendar = broker.request("/v2/calendar", params={"start": (today - timedelta(days=240)).isoformat(),
                                                     "end": today.isoformat()})
    calendar = [d for d in calendar if datetime.fromisoformat(d["date"] + "T" + d["close"]).replace(tzinfo=ET) < stamp(clock["timestamp"])]
    excluded = calendar[-10:]
    calendar = calendar[:-10][-104:]
    if len(calendar) != 104:
        raise ValueError("Need exactly 104 sessions")
    manifest = {"calendar": calendar, "excluded_previously_seen": [d["date"] for d in excluded], "sha256": {}}
    data = []
    for index, day in enumerate(calendar):
        p = root / (day["date"] + ".json")
        if not p.exists():
            opening = datetime.fromisoformat(day["date"] + "T" + day["open"]).replace(tzinfo=ET)
            closing = datetime.fromisoformat(day["date"] + "T" + day["close"]).replace(tzinfo=ET)
            bars = broker.bars(SYMBOLS, opening.isoformat(), closing.isoformat())
            temp = p.with_suffix(".tmp")
            temp.write_text(json.dumps(bars, separators=(",", ":")), encoding="utf-8")
            temp.replace(p)
        raw = p.read_bytes()
        manifest["sha256"][p.name] = hashlib.sha256(raw).hexdigest()
        data.append((day, json.loads(raw)))
        if (index + 1) % 10 == 0 or index == 103:
            print(json.dumps({"cached_sessions": index + 1, "total": 104}), flush=True)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return data


def features(day, raw, history):
    opening = datetime.fromisoformat(day["date"] + "T" + day["open"]).replace(tzinfo=ET)
    closing = datetime.fromisoformat(day["date"] + "T" + day["close"]).replace(tzinfo=ET)
    length = int((closing - opening).total_seconds() / 60)
    result, summaries = {}, {}
    for symbol in SYMBOLS:
        bars = {}
        for row in raw[symbol]:
            minute = int((stamp(row["t"]) - opening).total_seconds() / 60)
            if not 0 <= minute < length:
                continue
            values = {k: float(row[k]) for k in ("o", "h", "l", "c", "v")}
            values["vw"] = float(row.get("vw", row["c"]))
            if minute in bars or any(not math.isfinite(v) for v in values.values()) or \
                    min(values[k] for k in ("o", "h", "l", "c", "vw")) <= 0 or values["v"] <= 0 or \
                    values["h"] < max(values["o"], values["c"], values["l"]) or \
                    values["l"] > min(values["o"], values["c"]):
                raise ValueError("Invalid or duplicate bars")
            bars[minute] = values
        prior = list(history[symbol])
        opening_price = bars.get(0, {}).get("o")
        first5 = all(i in bars for i in range(5))
        first15 = all(i in bars for i in range(15))
        vol5 = sum(bars[i]["v"] for i in range(5)) if first5 else None
        baseline_volume = [d["vol5"] for d in prior if d["vol5"] is not None]
        relative = vol5 / statistics.mean(baseline_volume) if vol5 and len(baseline_volume) == 14 else None
        atr = statistics.mean(d["tr"] for d in prior) if len(prior) == 14 and all(d["tr"] is not None for d in prior) else None
        high15 = max(bars[i]["h"] for i in range(15)) if first15 else None
        high5 = max(bars[i]["h"] for i in range(5)) if first5 else None
        vwap_sum, volume_sum = 0.0, 0.0
        recent = deque(maxlen=20)
        rows = {}
        for i, bar in sorted(bars.items()):
            vwap_sum += bar["vw"] * bar["v"]
            volume_sum += bar["v"]
            r = dict(bar, vwap=vwap_sum / volume_sum, ratio=bar["v"] / statistics.mean(recent) if len(recent) == 20 else None)
            prior_moves = [d["moves"].get(i) for d in prior]
            if opening_price and len(prior) == 14 and all(v is not None for v in prior_moves) and prior[-1]["close"]:
                r["upper"] = max(opening_price, prior[-1]["close"]) * (1 + statistics.mean(prior_moves))
            else:
                r["upper"] = None
            recent.append(bar["v"])
            rows[i] = r
        previous_close = prior[-1]["close"] if prior else None
        high = max((b["h"] for b in bars.values()), default=None)
        low = min((b["l"] for b in bars.values()), default=None)
        tr = max(high - low, abs(high - previous_close), abs(low - previous_close)) if high and previous_close else None
        summaries[symbol] = {"vol5": vol5, "tr": tr, "close": bars.get(length - 1, {}).get("c"),
                             "moves": {i: abs(b["c"] / opening_price - 1) for i, b in bars.items()} if opening_price else {}}
        result[symbol] = {"rows": rows, "high15": high15, "high5": high5, "relative": relative,
                          "atr": atr, "bullish5": first5 and bars[4]["c"] > bars[0]["o"], "coverage": len(bars) / length}
    eligible = sorted((s for s in SYMBOLS if result[s]["relative"] is not None and result[s]["relative"] > 1 and
                       result[s]["atr"] is not None and result[s]["atr"] > .5 and result[s]["bullish5"]),
                      key=lambda s: (-result[s]["relative"], s))[:4]
    for s in SYMBOLS:
        result[s]["in_play"] = s in eligible
        history[s].append(summaries[s])
    return {"date": day["date"], "length": length, "symbols": result}


def entry(strategy, f, minute):
    rows = f["rows"]
    r, prev = rows.get(minute), rows.get(minute - 1)
    if not r or not prev:
        return None
    if strategy == "orb_baseline":
        high = f["high15"]
        if minute < 20 or high is None or r["ratio"] is None or not all(i in rows for i in range(minute - 5, minute + 1)):
            return None
        if prev["c"] <= high < r["c"] <= high * 1.005 and r["c"] > r["vwap"] and r["ratio"] >= 1.5:
            return r["ratio"]
    elif strategy == "relative_volume_orb":
        if minute >= 5 and f["in_play"] and prev["c"] <= f["high5"] < r["c"]:
            return f["relative"]
    elif strategy == "noise_momentum":
        if (minute + 1) % 30 == 0 and r["upper"] and r["c"] > max(r["upper"], r["vwap"]):
            return r["c"] / r["upper"]
    return None


def run(strategy, days, cost=.001):
    cash, peak = 2000.0, 2000.0
    locked = False
    trades, daily, incomplete = [], [], []
    max_drawdown, highest = 0.0, 2000.0
    for day in days:
        start = cash
        positions, pending, used = {}, {}, set()
        attempts, daily_locked = 0, False
        for minute in range(day["length"]):
            def close(symbol, price, reason):
                nonlocal cash
                pos = positions.pop(symbol)
                cash += pos["qty"] * price * (1 - cost)
                trades.append({"day": day["date"], "symbol": symbol, "entry_minute": pos["minute"],
                               "exit_minute": minute, "entry": pos["entry"], "exit": price,
                               "reason": reason, "pnl": pos["qty"] * (price - pos["entry"]) - pos["qty"] * (price + pos["entry"]) * cost})

            # Existing exits execute at the following bar's open, never the signal close.
            for symbol, pos in list(positions.items()):
                bar = day["symbols"][symbol]["rows"].get(minute)
                if not bar:
                    continue
                if pos.get("exit_next") or daily_locked or minute >= day["length"] - 10:
                    close(symbol, bar["o"], pos.get("exit_next") or "session_or_loss_exit")
            for symbol, order in list(pending.items()):
                bar = day["symbols"][symbol]["rows"].get(minute)
                if not daily_locked and not locked and bar and bar["o"] <= order["limit"] and len(positions) < 4:
                    qty = order["qty"]
                    principal = qty * bar["o"]
                    if principal * (1 + cost) <= cash + 1e-8:
                        cash -= principal * (1 + cost)
                        atr = day["symbols"][symbol]["atr"]
                        positions[symbol] = {"qty": qty, "entry": bar["o"], "minute": minute,
                                             "stop": bar["o"] - .1 * atr if strategy == "relative_volume_orb" else bar["o"] * .99,
                                             "target": bar["o"] * 1.02 if strategy == "orb_baseline" else None,
                                             "last": bar["o"]}
                del pending[symbol]
            # Stops apply on the entry bar too. If stop and target overlap, stop wins.
            for symbol, pos in list(positions.items()):
                bar = day["symbols"][symbol]["rows"].get(minute)
                if not bar:
                    continue
                pos["last"] = bar["c"]
                if bar["l"] <= pos["stop"]:
                    close(symbol, min(bar["o"], pos["stop"]), "stop")
                elif pos["target"] and bar["h"] >= pos["target"]:
                    close(symbol, pos["target"], "target")
                elif strategy == "noise_momentum" and bar["upper"] and bar["c"] < max(bar["upper"], bar["vwap"]):
                    pos["exit_next"] = "trailing_exit"
            equity = cash + sum(p["qty"] * p["last"] for p in positions.values())
            highest = max(highest, equity)
            max_drawdown = max(max_drawdown, highest - equity)
            if start - equity >= 40:
                daily_locked = True
                pending.clear()
            if locked or daily_locked or attempts >= 4 or minute + 1 >= day["length"] - 30:
                continue
            candidates = []
            universe = ("SPY", "QQQ") if strategy == "noise_momentum" else SYMBOLS
            for symbol in universe:
                if symbol in used or symbol in positions:
                    continue
                rank = entry(strategy, day["symbols"][symbol], minute)
                if rank is not None:
                    candidates.append((-rank, symbol))
            for _, symbol in sorted(candidates):
                if attempts >= 4 or len(positions) + len(pending) >= 4:
                    break
                reserved = sum(o["qty"] * o["limit"] * (1 + cost) for o in pending.values())
                limit = math.ceil(day["symbols"][symbol]["rows"][minute]["c"] * 1.0005 * 100) / 100
                dollars = min(400.0, max(0.0, (cash - reserved) / (1 + cost)))
                qty = math.floor(dollars / limit * 1e6) / 1e6
                if qty * limit < 1:
                    continue
                pending[symbol] = {"qty": qty, "limit": limit}
                used.add(symbol)
                attempts += 1
        if positions:
            incomplete.append(day["date"])
            # Mark missing exits for accounting only. Never count these as successful fills.
            for symbol, pos in list(positions.items()):
                close(symbol, pos["last"], "unexecutable_missing_close")
        peak = max(peak, cash)
        if peak - cash >= 200:
            locked = True
        daily.append({"date": day["date"], "pnl": cash - start, "equity": cash, "locked": locked})
    profits = [t["pnl"] for t in trades]
    gains = sum(p for p in profits if p > 0)
    losses = -sum(p for p in profits if p < 0)
    return {"net_modeled_pnl": cash - 2000, "trade_count": len(trades),
            "win_rate": sum(p > 0 for p in profits) / len(profits) if profits else 0,
            "profit_factor": gains / losses if losses else None, "max_drawdown": max_drawdown,
            "review_locked": locked, "incomplete_exit_days": incomplete, "daily": daily, "trades": trades}


def confidence(daily):
    values = [r["pnl"] for r in daily]
    rng = random.Random(20261103)
    means = []
    for _ in range(5000):
        sample = []
        while len(sample) < len(values):
            start = rng.randrange(len(values))
            sample.extend(values[(start + i) % len(values)] for i in range(5))
        means.append(statistics.mean(sample[:len(values)]))
    return sorted(means)[int(.0167 * len(means))]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--credentials", required=True)
    parser.add_argument("--root", required=True)
    args = parser.parse_args()
    root = Path(args.root)
    data = load_data(Broker(args.credentials), root / "data")
    history = {s: deque(maxlen=14) for s in SYMBOLS}
    prepared = [features(day, bars, history) for day, bars in data][14:]
    phases = {"development": prepared[:40], "validation": prepared[40:70], "holdout": prepared[70:]}
    benchmarks = {}
    for name, days in phases.items():
        first = days[0]["symbols"]["SPY"]["rows"].get(0)
        last = days[-1]["symbols"]["SPY"]["rows"].get(days[-1]["length"] - 1)
        benchmarks[name] = 2000 / (1.001 * first["o"]) * last["c"] * .999 - 2000 if first and last else None
    report = {"protocol_commit": "df17a0c", "phases": {k: {"start": v[0]["date"], "end": v[-1]["date"], "sessions": len(v)} for k, v in phases.items()},
              "spy_buy_hold_modeled_pnl": benchmarks,
              "benchmark_note": "Entire $2000 in SPY at first open through last close, 10bps each side, price return only/no dividends. Different exposure and overnight risk from intraday candidates.",
              "cash_benchmark_pnl": 0, "candidates": {},
              "limitations": "IEX-only minute OHLC; current fixed universe; adapted research rules; not a production-engine or quote/fill replay. Simplified intrabar stops may execute sooner than the real minute-polling exits. Fees/slippage modeled; electricity unknown. No guarantee of future profit."}
    for strategy in CANDIDATES:
        result = {}
        for cost, label in ((.001, "base"), (.002, "stress")):
            result[label] = {name: run(strategy, days, cost) for name, days in phases.items()}
        v, h = result["base"]["validation"], result["base"]["holdout"]
        lower = confidence(v["daily"] + h["daily"])
        result["lower_mean_daily_pnl"] = lower
        result["qualified"] = all(result[c][p]["net_modeled_pnl"] > 0 and not result[c][p]["review_locked"]
                                  and not result[c][p]["incomplete_exit_days"] for c in ("base", "stress") for p in ("validation", "holdout")) \
                                  and v["trade_count"] + h["trade_count"] >= 20 and lower > 0
        report["candidates"][strategy] = result
        print(json.dumps({"candidate": strategy, "base": {p: {k: val[k] for k in ("net_modeled_pnl", "trade_count", "max_drawdown")} for p, val in result["base"].items()},
                          "stress": {p: val["net_modeled_pnl"] for p, val in result["stress"].items()}, "qualified": result["qualified"], "lower_mean_daily_pnl": lower}), flush=True)
    (root / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
