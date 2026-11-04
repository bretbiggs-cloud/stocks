"""Forward mock trial using observed quotes. Has no order-submission API calls."""
import json
from datetime import timedelta, timezone, datetime
from decimal import Decimal as D, ROUND_DOWN
from pathlib import Path

from stocks.risk import fresh
from stocks.strategy import SYMBOLS, signal, stamp, number


def run_shadow(broker, store, root, now, opening, closing, *, allow_entries, news_filter=False):
    day = opening.date().isoformat()
    version = "news-volume-v1" if news_filter else "orb-v1"
    key = ("shadow:news-volume-v1:" if news_filter else "shadow:") + day
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
                "entry_evidence": p.get("entry_evidence"), "entry": p["entry"], "exit": str(bid), "qty": p["qty"], "reason": reason,
                "modeled_pnl": str(qty * (bid * D(".999") - D(p["entry"]) * D("1.001")))})
            del state["positions"][symbol]
    news = None
    if news_filter and allow_entries:
        from stocks.news import observe_news
        news = observe_news(broker, store, now)
        state["news_status"] = {k: v for k, v in news.items() if k != "articles"}
        state["news_article_count"] = len(news["articles"])
    decisions = []
    if allow_entries and not state["locked"] and opening + timedelta(minutes=21) <= now < closing - timedelta(minutes=30) and len(state["used"]) < 4:
        try:
            bars = broker.bars(SYMBOLS, opening.isoformat(), (now - timedelta(seconds=1)).isoformat())
        except Exception:
            bars = {s: [] for s in SYMBOLS}
        candidates = []
        for symbol in SYMBOLS:
            try:
                result = signal(bars[symbol], opening, now)
            except (KeyError, TypeError, ValueError):
                result = {"buy": False, "reason": "invalid_bars"}
            if news_filter:
                from stocks.news import eligible_articles
                articles = eligible_articles(news["articles"], symbol, now) if news and news["ok"] else []
                result["news_ids"] = [a["id"] for a in articles]
                result["news_evidence"] = articles
                if not articles:
                    result.update(buy=False, reason="no_recent_news" if news and news["ok"] else "news_unavailable")
            if result["buy"] and symbol in state["used"]:
                result.update(buy=False, reason="already_used_today")
            if result["buy"] and symbol not in quotes:
                result.update(buy=False, reason="missing_fresh_quote")
            decisions.append(dict(symbol=symbol, **result))
            store.event(now, "mock_research", dict(version=version, symbol=symbol, **result))
            if result["buy"] and symbol not in state["used"] and symbol in quotes:
                candidates.append((D(result["volume_ratio"]), symbol))
        for _, symbol in sorted(candidates, reverse=True):
            if len(state["positions"]) >= 4 or len(state["used"]) >= 4:
                break
            decision = next(d for d in decisions if d["symbol"] == symbol)
            bid, ask, quote_time = quotes[symbol]
            try:
                fresh(quote_time, datetime.now(timezone.utc), 15)
            except ValueError:
                decision.update(buy=False, reason="quote_expired_before_entry")
                continue
            if (ask - bid) / ask > D(".0025"):
                decision.update(buy=False, reason="spread_too_wide")
                continue
            qty = (min(D(400), cash / D("1.001")) / ask).quantize(D(".000001"), rounding=ROUND_DOWN)
            if qty * ask < 1:
                decision.update(buy=False, reason="insufficient_cash")
                continue
            cash -= qty * ask * D("1.001")
            state["positions"][symbol] = {"qty": str(qty), "entry": str(ask), "mark": str(bid), "time": now.isoformat()}
            state["used"].append(symbol)
            state["positions"][symbol]["entry_evidence"] = next(d for d in decisions if d["symbol"] == symbol)
    if decisions:
        store.event(now, "mock_decisions", {"version": version, "decisions": decisions})
    state["cash"] = str(cash)
    state["equity"] = str(cash + sum((D(p["qty"]) * D(p["mark"]) for p in state["positions"].values()), D(0)))
    net = D(state["equity"]) - D(2000)
    closed = [D(t["modeled_pnl"]) for t in state["trades"]]
    realized = sum(closed, D(0))
    fees = sum((D(t["qty"]) * (D(t["entry"]) + D(t["exit"])) * D(".001") for t in state["trades"]), D(0))
    fees += sum((D(p["qty"]) * D(p["entry"]) * D(".001") for p in state["positions"].values()), D(0))
    peak = max(D(state.get("peak_equity", "2000")), equity, D(state["equity"]))
    drawdown = max(D(state.get("max_observed_drawdown", "0")), peak - min(equity, D(state["equity"])))
    state.update(peak_equity=str(peak), max_observed_drawdown=str(drawdown),
                 completed_trades=len(closed), wins=sum(p > 0 for p in closed), losses=sum(p < 0 for p in closed),
                 win_rate=str(D(sum(p > 0 for p in closed)) / len(closed)) if closed else None,
                 realized_modeled_pnl=str(realized), unrealized_modeled_pnl=str(net - realized),
                 total_modeled_pnl=str(net), modeled_execution_cost=str(fees),
                 gross_pnl_before_modeled_cost=str(net + fees), electricity_cost="unknown",
                 net_profit_verified=False, cash_benchmark_pnl="0")
    state.update(version=version, latest_decisions=decisions, time=now.isoformat(), missing_quotes=missing, broker_strategy_orders=0,
                 note="Forward mock ledger only: assumed fills at observed ask/bid plus 10bps each side. No Alpaca orders. Unqualified experimental strategy; news presence is not positive sentiment or a confirmed catalyst.")
    store.put(key, state)
    report = Path(root) / "reports" / (f"mock-news-volume-v1-{day}.json" if news_filter else f"mock-{day}.json")
    temporary = report.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(report)
