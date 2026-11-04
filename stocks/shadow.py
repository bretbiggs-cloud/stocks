"""Forward mock trial using observed quotes. Has no order-submission API calls."""
import json
from datetime import timedelta, timezone, datetime
from decimal import Decimal as D, ROUND_DOWN
from pathlib import Path

from stocks.risk import fresh
from stocks.strategy import SYMBOLS, signal, stamp, number


def run_shadow(broker, store, root, now, opening, closing, *, allow_entries):
    day = opening.date().isoformat()
    key = "shadow:" + day
    state = store.get(key, {"cash": "2000", "positions": {}, "used": [], "trades": [], "locked": False})
    quotes, missing = {}, []
    # Quotes are observed now, not replayed retrospectively after seeing future prices.
    for symbol in SYMBOLS:
        try:
            q = broker.quote(symbol)
            fresh(stamp(q["t"]), datetime.now(timezone.utc), 15)
            bid, ask = number(q["bp"]), number(q["ap"])
            if ask < bid:
                raise ValueError("Crossed quote")
            quotes[symbol] = (bid, ask, stamp(q["t"]))
        except Exception:
            missing.append(symbol)
    cash = D(state["cash"])
    for symbol, p in state["positions"].items():
        if symbol in quotes:
            p["mark"] = str(quotes[symbol][0])
    equity = cash + sum((D(p["qty"]) * D(p["mark"]) for p in state["positions"].values()), D(0))
    if D(2000) - equity >= 40:
        state["locked"] = True
    for symbol, p in list(state["positions"].items()):
        if symbol not in quotes:
            continue
        bid = quotes[symbol][0]
        reason = None
        if state["locked"] or now >= closing - timedelta(minutes=10):
            reason = "session_or_loss_exit"
        elif bid <= D(p["entry"]) * D(".99"):
            reason = "stop"
        elif bid >= D(p["entry"]) * D("1.02"):
            reason = "target"
        if reason:
            qty = D(p["qty"])
            cash += qty * bid * D(".999")
            state["trades"].append({"symbol": symbol, "entry_time": p["time"], "exit_time": now.isoformat(),
                "entry": p["entry"], "exit": str(bid), "qty": p["qty"], "reason": reason,
                "modeled_pnl": str(qty * (bid * D(".999") - D(p["entry"]) * D("1.001")))})
            del state["positions"][symbol]
    if allow_entries and not state["locked"] and opening + timedelta(minutes=21) <= now < closing - timedelta(minutes=30) and len(state["used"]) < 4:
        try:
            bars = broker.bars(SYMBOLS, opening.isoformat(), (now - timedelta(seconds=1)).isoformat())
        except Exception:
            bars = {s: [] for s in SYMBOLS}
        candidates = []
        for symbol in SYMBOLS:
            result = signal(bars[symbol], opening, now)
            store.event(now, "mock_research", dict(symbol=symbol, **result))
            if result["buy"] and symbol not in state["used"] and symbol in quotes:
                candidates.append((D(result["volume_ratio"]), symbol))
        for _, symbol in sorted(candidates, reverse=True):
            if len(state["positions"]) >= 4 or len(state["used"]) >= 4:
                break
            bid, ask, quote_time = quotes[symbol]
            try:
                fresh(quote_time, datetime.now(timezone.utc), 15)
            except ValueError:
                continue
            if (ask - bid) / ask > D(".0025"):
                continue
            qty = (min(D(400), cash / D("1.001")) / ask).quantize(D(".000001"), rounding=ROUND_DOWN)
            if qty * ask < 1:
                continue
            cash -= qty * ask * D("1.001")
            state["positions"][symbol] = {"qty": str(qty), "entry": str(ask), "mark": str(bid), "time": now.isoformat()}
            state["used"].append(symbol)
    state["cash"] = str(cash)
    state["equity"] = str(cash + sum((D(p["qty"]) * D(p["mark"]) for p in state["positions"].values()), D(0)))
    state.update(time=now.isoformat(), missing_quotes=missing, broker_strategy_orders=0,
                 note="Forward mock ledger only: assumed fills at observed ask/bid plus 10bps each side. No Alpaca orders. Unqualified original strategy measured for diagnostics only.")
    store.put(key, state)
    report = Path(root) / "reports" / f"mock-{day}.json"
    temporary = report.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(report)
