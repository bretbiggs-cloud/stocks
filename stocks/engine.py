"""Paper-only single-writer execution state machine. Exits precede research."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, ROUND_DOWN, ROUND_UP
from pathlib import Path
from zoneinfo import ZoneInfo
import json

from stocks.broker import ApiError, PAPER
from stocks.risk import Buy, Snapshot, validate_buy, fresh
from stocks.strategy import SYMBOLS, VERSION, number, signal, stamp

ET = ZoneInfo("America/New_York")


def dec(value):
    result = D(str(value))
    if not result.is_finite():
        raise ValueError("Non-finite balance")
    return result


class Engine:
    def __init__(self, broker, store, root, *, enabled=False, host_ok=lambda: True,
                 strategy_enabled=False, canary_date=None, shadow_date=None):
        self.broker, self.store, self.root = broker, store, Path(root)
        self.enabled, self.host_ok = enabled, host_ok
        self.strategy_enabled = strategy_enabled
        self.canary_date, self.shadow_date = canary_date, shadow_date

    def emit(self, now, kind, **body):
        self.store.event(now, kind, body)

    def reconcile(self):
        uncertain = False
        for key, client_id, payload, status in self.store.unresolved():
            try:
                order = self.broker.order(client_id)
                proposed = json.loads(payload)
                if order.get("client_order_id") != client_id or any(
                        order.get(k) != proposed.get(k) for k in ("symbol", "side")):
                    raise ValueError("Order identity mismatch")
                self.store.record_order(key, order)
            except ApiError as exc:
                if exc.status != 404:
                    raise
                # A missing response/order is never permission to resubmit.
                self.store.mark(key, "unknown")
                uncertain = True
        return uncertain

    def submit(self, now, key, payload):
        if not self.enabled or self.store.exists(key):
            return False
        if payload["side"] == "buy":
            if key == "canary:buy":
                if self.canary_date != now.astimezone(ET).date().isoformat() or payload["symbol"] != "AAPL" or \
                        payload.get("type") != "limit" or dec(payload["qty"]) * dec(payload["limit_price"]) > 10:
                    raise ValueError("Canary not authorized for this date/instrument/amount")
            elif not self.strategy_enabled:
                raise ValueError("Strategy purchases are disabled")
        client_id = self.store.reserve(key, payload)
        try:
            order = self.broker.submit(dict(payload, client_order_id=client_id))
            if order.get("client_order_id") != client_id:
                raise ValueError("Submission identity mismatch")
            self.store.record_order(key, order)
            self.emit(now, "submitted", key=key, side=payload["side"], symbol=payload["symbol"])
        except Exception:
            self.store.mark(key, "unknown")
            self.emit(now, "submission_uncertain", key=key)
            raise
        return True

    def cancel(self, now, order):
        if self.enabled and self.store.known(order["client_order_id"]):
            key = "cancel_attempts:" + order["client_order_id"]
            attempts = self.store.get(key, 0)
            if attempts >= 3:
                self.store.put("review_lock", True)
                self.store.put("attention", "Cancellation unconfirmed after three attempts; inspect broker orders")
                return
            self.store.put(key, attempts + 1)
            try:
                self.broker.cancel(order["id"])
                self.emit(now, "cancel_requested", client_id=order["client_order_id"])
            except ApiError as exc:
                if exc.status not in (404, 422):
                    raise
            # Always await broker reconciliation; do not assume cancellation succeeded.

    def sell(self, now, position, orders, reason):
        symbol = position["symbol"]
        pending = [o for o in orders if o["symbol"] == symbol]
        if pending:
            for order in pending:
                if order["side"] == "buy":
                    self.cancel(now, order)
            return False
        qty = dec(position["qty"])
        available = dec(position.get("qty_available", position["qty"]))
        if qty <= 0 or available < qty:
            raise ValueError("Long position unavailable for exit")
        # A new exit ID is allowed only after all earlier exits are terminal/reconciled.
        if any(json.loads(row[2])["symbol"] == symbol for row in self.store.unresolved()):
            return False
        n = self.store.db.execute("SELECT count(*) FROM intents WHERE intent_key LIKE ?",
                                  (f"exit:{symbol}:%",)).fetchone()[0]
        failed = sum(1 for o in self.store.order_rows() if o["symbol"] == symbol and
                     o["side"] == "sell" and o["status"] == "rejected")
        if failed >= 3:
            self.store.put("review_lock", True)
            self.store.put("attention", "Three exit rejections; manual paper position review required")
            return False
        return self.submit(now, f"exit:{symbol}:{n}", {"symbol": symbol, "qty": str(qty),
                           "side": "sell", "type": "market", "time_in_force": "day",
                           "extended_hours": False})

    def buy(self, now, account, positions, orders, symbol, dollars, key, day_start, peak):
        asset = self.broker.asset(symbol)
        if asset.get("symbol") != symbol or asset.get("class") != "us_equity" or \
                asset.get("status") != "active" or asset.get("tradable") is not True or \
                asset.get("fractionable") is not True:
            raise ValueError("Instrument unavailable")
        quote = self.broker.quote(symbol)
        ask, bid = number(quote["ap"]), number(quote["bp"])
        if ask < bid or (ask - bid) / ask > D("0.0025"):
            raise ValueError("Invalid/wide quote")
        limit = (ask * D("1.0005")).quantize(D("0.01"), rounding=ROUND_UP)
        qty = (dollars / limit).quantize(D("0.000001"), rounding=ROUND_DOWN)
        pending = {}
        for o in orders:
            if o["side"] == "buy":
                if o.get("type") != "limit" or not o.get("qty") or not o.get("limit_price"):
                    raise ValueError("Unbounded pending buy")
                reserve = (dec(o["qty"]) - dec(o["filled_qty"])) * dec(o["limit_price"])
                pending[o["symbol"]] = pending.get(o["symbol"], D(0)) + reserve
        check_time = datetime.now(timezone.utc)
        # Recheck market immediately before placing an entry.
        clock = self.broker.clock()
        fresh(stamp(clock["timestamp"]), check_time + timedelta(seconds=2), 10)
        state = Snapshot(PAPER, self.broker.expected, now, dec(account["cash"]),
                         dec(account["equity"]), day_start, peak,
                         {p["symbol"]: abs(dec(p["market_value"])) for p in positions}, pending,
                         True, clock["is_open"] is True, True, False,
                         self.store.get("review_lock", False), self.store.get("daily_lock", False))
        validate_buy(Buy(symbol, qty, limit, stamp(quote["t"]), (ask - bid) / ask), state,
                     expected_account=self.broker.expected, allowed_symbols=frozenset(SYMBOLS), now=check_time)
        return self.submit(now, key, {"symbol": symbol, "qty": str(qty), "side": "buy",
                           "type": "limit", "limit_price": str(limit), "time_in_force": "day",
                           "extended_hours": False})

    def tick(self):
        now = datetime.now(timezone.utc)
        account = self.broker.account()
        clock = self.broker.clock()
        fresh(stamp(clock["timestamp"]), datetime.now(timezone.utc) + timedelta(seconds=2), 15)
        uncertain = self.reconcile()
        orders, positions = self.broker.orders(), self.broker.positions()
        # Detect an account changing while its separate endpoints are reconciled.
        second = self.broker.account()
        stable_cash = account["cash"] == second["cash"]
        account = second
        cash, equity = dec(account["cash"]), dec(account["equity"])
        day = now.astimezone(ET).date().isoformat()
        if not self.store.get("initialized"):
            if positions or orders or cash != 2000 or equity != 2000:
                raise ValueError("First start requires empty 2000 USD paper account")
            self.store.put("initialized", True)
            self.store.put("peak_close", "2000")
            self.store.put("canary", "pending")
        if self.store.get("day") != day:
            self.store.put("day", day)
            self.store.put("day_start", str(dec(account["last_equity"])))
            self.store.put("daily_lock", False)
        day_start, peak = dec(self.store.get("day_start")), dec(self.store.get("peak_close"))
        if day_start - equity >= 40:
            self.store.put("daily_lock", True)
        if peak - equity >= 200 or cash < 0 or any(dec(p["qty"]) <= 0 for p in positions):
            self.store.put("review_lock", True)
        foreign = any(not self.store.known(o["client_order_id"]) for o in orders)
        owned = {o["symbol"] for o in self.store.order_rows() if o["side"] == "buy" and dec(o["filled_qty"]) > 0}
        expected_qty = {}
        for order in self.store.order_rows():
            qty = dec(order["filled_qty"]) * (1 if order["side"] == "buy" else -1)
            expected_qty[order["symbol"]] = expected_qty.get(order["symbol"], D(0)) + qty
        actual_qty = {p["symbol"]: dec(p["qty"]) for p in positions}
        mismatched = {s for s in set(expected_qty) | set(actual_qty)
                      if expected_qty.get(s, D(0)) != actual_qty.get(s, D(0))}
        # Broker endpoints are not an atomic snapshot. In particular, a filled exit
        # may appear before the position endpoint updates. Never sell that stale
        # position again: that could accidentally open a short.
        mismatch_ticks = self.store.get("mismatch_ticks", 0) + 1 if mismatched else 0
        self.store.put("mismatch_ticks", mismatch_ticks)
        if mismatch_ticks >= 3:
            self.store.put("review_lock", True)
            self.store.put("attention", "Broker positions and recorded fills disagree; reconcile before trading")
        if foreign or any(p["symbol"] not in owned for p in positions):
            self.store.put("review_lock", True)
        with self.store.db:
            self.store.db.execute("INSERT OR REPLACE INTO balances VALUES (?,?,?)",
                                  (now.isoformat(), str(equity), str(cash)))
        status = {"time": now.isoformat(), "strategy": VERSION, "enabled": self.enabled,
                  "strategy_purchases_enabled": self.strategy_enabled,
                  "canary_date": self.canary_date, "shadow_date": self.shadow_date,
                  "market_open": clock["is_open"], "next_open": clock["next_open"],
                  "cash": str(cash), "equity": str(equity), "positions": len(positions),
                  "open_orders": len(orders), "canary": self.store.get("canary"),
                  "review_lock": self.store.get("review_lock", False),
                  "daily_lock": self.store.get("daily_lock", False), "uncertain_order": uncertain,
                  "attention": self.store.get("attention"),
                  "position_reconciliation_pending": sorted(mismatched),
                  "mode": "monitoring", "ai_cost_usd": "0"}
        self.report(now, status)
        if not clock["is_open"]:
            status["mode"] = "market_closed"
            if positions or orders:
                status["attention"] = "Exposure/orders remain outside regular hours; exits resume next open"
                self.store.put("review_lock", True)
            else:
                self.store.put("peak_close", str(max(peak, equity)))
            self.report(now, status)
            if self.store.get("backup_day") != day:
                self.store.checkpoint(self.root / "backups", day)
                self.store.put("backup_day", day)
            return status
        calendar = self.broker.request("/v2/calendar", params={"start": day, "end": day})
        if len(calendar) != 1:
            raise ValueError("Trading calendar unavailable")
        row = calendar[0]
        opening = datetime.fromisoformat(day + "T" + row["open"]).replace(tzinfo=ET)
        closing = datetime.fromisoformat(day + "T" + row["close"]).replace(tzinfo=ET)
        forced = now >= closing - timedelta(minutes=10) or self.store.get("daily_lock") or self.store.get("review_lock")
        if self.store.get("canary") == "pending":
            owned_orders = self.store.order_rows()
            buys = [o for o in owned_orders if o["side"] == "buy"]
            sells = [o for o in owned_orders if o["side"] == "sell"]
            filled_buy = sum((dec(o["filled_qty"]) for o in buys), D(0))
            filled_sell = sum((dec(o["filled_qty"]) for o in sells), D(0))
            if filled_buy > 0 and filled_sell >= filled_buy and not positions and not orders and not uncertain:
                self.store.put("canary", "passed")
                self.emit(now, "canary_passed", filled_quantity=str(filled_buy))
            elif self.store.exists("canary:buy") and not self.store.unresolved() and not positions and filled_buy == 0:
                self.store.put("canary", "failed")
                self.store.put("review_lock", True)
        # Cancel entries that are stale, partially filled, or no longer safe to leave pending.
        canceled = False
        for o in orders:
            if o["side"] == "buy" and self.store.known(o["client_order_id"]):
                if forced or dec(o["filled_qty"]) > 0 or now - stamp(o["created_at"]) > timedelta(seconds=120):
                    self.cancel(now, o)
                    canceled = True
        exiting = False
        for p in positions:
            if p["symbol"] not in owned or p["symbol"] in mismatched or dec(p["qty"]) <= 0:
                continue
            reason = "session_or_loss_exit" if forced else None
            if self.store.get("canary") == "pending":
                reason = "canary_roundtrip"
            if not reason:
                try:
                    q = self.broker.quote(p["symbol"])
                    fresh(stamp(q["t"]), datetime.now(timezone.utc), 15)
                    bid = number(q["bp"])
                    entry = number(p["avg_entry_price"])
                    if bid <= entry * D("0.99"):
                        reason = "one_percent_stop"
                    elif bid >= entry * D("1.02"):
                        reason = "two_percent_target"
                except (ApiError, ValueError):
                    # Cannot monitor exposure reliably: close it, and pause further entries today.
                    self.store.put("daily_lock", True)
                    reason = "quote_unavailable"
            if reason:
                self.sell(now, p, orders, reason)
                self.emit(now, "exit_required", symbol=p["symbol"], reason=reason)
                exiting = True
        blocked = forced or exiting or canceled or uncertain or foreign or bool(mismatched) or not stable_cash or \
                  self.store.get("daily_lock") or self.store.get("review_lock") or \
                  now < opening + timedelta(minutes=5) or now >= closing - timedelta(minutes=30)
        host_ready = self.host_ok() if not blocked and self.enabled else False
        if blocked or not self.enabled:
            status["mode"] = "entries_blocked" if blocked else "read_only"
        elif not host_ready:
            status["mode"] = "host_busy_entries_deferred"
        elif self.store.get("canary") == "pending":
            if day != self.canary_date:
                status["mode"] = "waiting_for_authorized_canary_date"
            elif not positions and not orders and not self.store.exists("canary:buy"):
                self.buy(now, account, positions, orders, "AAPL", D(10), "canary:buy", day_start, peak)
                status["mode"] = "canary_test"
        elif self.store.get("canary") == "passed" and not orders:
            if not self.strategy_enabled:
                status["mode"] = "strategy_purchases_disabled"
            elif now < opening + timedelta(minutes=21):
                status["mode"] = "waiting_for_opening_range"
            else:
                self.research(now, opening, account, positions, orders, day_start, peak)
                status["mode"] = "strategy_evaluated"
        if self.store.get("canary") == "passed" and day == self.shadow_date:
            from stocks.shadow import run_shadow
            run_shadow(self.broker, self.store, self.root, now, opening, closing,
                       allow_entries=not blocked and host_ready)
            run_shadow(self.broker, self.store, self.root, now, opening, closing,
                       allow_entries=not blocked and host_ready, news_filter=True)
            status["mode"] = "mock_trial_no_strategy_orders"
        status.update(canary=self.store.get("canary"), review_lock=self.store.get("review_lock", False),
                      daily_lock=self.store.get("daily_lock", False), attention=self.store.get("attention"))
        self.report(now, status)
        return status

    def research(self, now, opening, account, positions, orders, day_start, peak):
        day = opening.date().isoformat()
        prefix = f"{VERSION}:{day}:"
        count = self.store.db.execute("SELECT count(*) FROM intents WHERE intent_key LIKE ?", (prefix + "%",)).fetchone()[0]
        if count >= 4:
            return
        bars = self.broker.bars(SYMBOLS, opening.isoformat(), (now - timedelta(seconds=1)).isoformat())
        held = {p["symbol"] for p in positions}
        candidates = []
        for symbol in SYMBOLS:
            decision = signal(bars[symbol], opening, now)
            self.emit(now, "research", symbol=symbol, **decision)
            if decision["buy"] and symbol not in held and not self.store.exists(prefix + symbol):
                candidates.append((dec(decision["volume_ratio"]), symbol))
        for _, symbol in sorted(candidates, reverse=True):
            dollars = min(D(400), dec(account["cash"]) - D(1))
            if dollars < 1:
                return
            # One new entry per tick, then reconcile before considering another.
            self.buy(now, account, positions, orders, symbol, dollars, prefix + symbol, day_start, peak)
            return

    def report(self, now, status):
        reports = self.root / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        filled = sum((dec(o.get("filled_qty", 0)) * dec(o.get("filled_avg_price") or 0)
                      for o in self.store.order_rows()), D(0))
        cost = filled * D("0.001")
        status = dict(status, gross_pnl=str(dec(status["equity"]) - D(2000)),
                      modeled_execution_cost=str(cost.quantize(D("0.0001"))),
                      pnl_after_modeled_execution=str((dec(status["equity"]) - D(2000) - cost).quantize(D("0.0001"))),
                      electricity_cost="unknown", net_profit_verified=False,
                      cost_note="10 basis points per filled side modeled; actual AI/data subscription cost $0. Electricity and other actual fees not reconciled.",
                      warning="Experimental IEX-only paper strategy. Local exits are not broker-held stops; outages can prevent timely exits.")
        day = now.astimezone(ET).date().isoformat()
        encoded = json.dumps(status, indent=2)
        for filename in ("status.json", f"daily-{day}.json"):
            temporary = reports / (filename + ".tmp")
            temporary.write_text(encoded, encoding="utf-8")
            temporary.replace(reports / filename)
        month = day[:7]
        first = self.store.db.execute("SELECT equity FROM balances WHERE time LIKE ? ORDER BY time LIMIT 1",
                                     (month + "%",)).fetchone()
        month_orders = [o for o in self.store.order_rows()
                        if (o.get("filled_at") or o.get("created_at") or "").startswith(month)]
        month_cost = sum((dec(o.get("filled_qty", 0)) * dec(o.get("filled_avg_price") or 0)
                          for o in month_orders), D(0)) * D(".001")
        monthly = {"month": month, "updated": now.isoformat(),
                   "starting_equity": first[0] if first else status["equity"],
                   "equity": status["equity"], "modeled_execution_cost": str(month_cost),
                   "gross_pnl": str(dec(status["equity"]) - dec(first[0] if first else status["equity"])),
                   "ai_data_subscription_cost": "0", "electricity_cost": "unknown",
                   "net_profit_verified": False, "cash_benchmark_pnl": "0",
                   "spy_benchmark": self.store.get("spy_benchmark", "not yet observed"),
                   "strategy": VERSION}
        temporary = reports / (f"monthly-{month}.json.tmp")
        temporary.write_text(json.dumps(monthly, indent=2), encoding="utf-8")
        temporary.replace(reports / f"monthly-{month}.json")
        self.store.put("last_status", status)

    def benchmark(self):
        """Optional comparison data; never a prerequisite for protective exits."""
        try:
            q = self.broker.quote("SPY")
            now = datetime.now(timezone.utc)
            fresh(stamp(q["t"]), now, 15)
            mid = (number(q["ap"]) + number(q["bp"])) / 2
            initial = self.store.get("spy_initial")
            if not initial:
                initial = {"price": str(mid), "time": q["t"]}
                self.store.put("spy_initial", initial)
            self.store.put("spy_benchmark", {"start": initial, "last_price": str(mid), "time": q["t"],
                           "hypothetical_2000_pnl": str(D(2000) * (mid / D(initial["price"]) - 1)),
                           "method": "IEX quote midpoint, price return only; excludes dividends and costs"})
        except (ApiError, ValueError, KeyError):
            pass
