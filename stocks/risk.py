"""Pure, fail-closed entry validation; inputs must come from a reconciled broker snapshot.

AI output is only a proposal. This module is not a broker adapter, loss-liquidation
worker, or guarantee of execution. Pending buy exposure must include reserved cash
and shares, even for orders whose submission result is not yet known.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Mapping

PAPER_ENDPOINT = "https://paper-api.alpaca.markets"


class Blocked(ValueError):
    """An entry cannot safely be accepted."""


def amount(value: Decimal, label: str, *, positive: bool = False) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise Blocked(f"{label}: finite Decimal required")
    if value < 0 or (positive and value == 0):
        raise Blocked(f"{label}: invalid amount")
    return value


@dataclass(frozen=True)
class Snapshot:
    endpoint: str
    account_id: str
    observed_at: datetime
    cash: Decimal
    equity: Decimal
    day_start_equity: Decimal
    peak_close_equity: Decimal
    positions: Mapping[str, Decimal]  # marked dollar exposure per instrument
    pending_buys: Mapping[str, Decimal]  # maximum cash reserved per instrument
    reconciled: bool
    market_open: bool
    account_active: bool
    trading_blocked: bool
    review_lock: bool
    daily_lock: bool


@dataclass(frozen=True)
class Buy:
    symbol: str
    quantity: Decimal
    limit_price: Decimal
    quote_at: datetime
    spread_fraction: Decimal


def fresh(timestamp: datetime, now: datetime, seconds: int) -> None:
    if timestamp.tzinfo is None or now.tzinfo is None:
        raise Blocked("timezone-aware timestamps required")
    age = now - timestamp
    if age < timedelta(0) or age > timedelta(seconds=seconds):
        raise Blocked("stale or future timestamp")


def validate_buy(proposal: Buy, state: Snapshot, *, expected_account: str,
                 allowed_symbols: frozenset[str], now: datetime) -> Decimal:
    """Return reserved order dollars, or block. Caller serializes validation+reservation.

    The external asset allowlist must exclude leveraged/inverse instruments.
    The adapter must use limit orders and include fees in reservations when applicable.
    Amounts in this function are USD. Buying power is deliberately never used.
    """
    if state.endpoint != PAPER_ENDPOINT:
        raise Blocked("paper endpoint required")
    if not expected_account or state.account_id != expected_account:
        raise Blocked("unexpected account")
    if not state.reconciled or not state.account_active or state.trading_blocked:
        raise Blocked("account not ready")
    if not state.market_open or state.review_lock or state.daily_lock:
        raise Blocked("entries locked")
    fresh(state.observed_at, now, 60)
    fresh(proposal.quote_at, now, 15)
    for label in ("cash", "equity", "day_start_equity", "peak_close_equity"):
        amount(getattr(state, label), label)
    if state.day_start_equity - state.equity >= Decimal("40"):
        raise Blocked("daily loss threshold")
    if state.peak_close_equity - state.equity >= Decimal("200"):
        raise Blocked("drawdown threshold")
    if proposal.symbol not in allowed_symbols:
        raise Blocked("instrument not allowlisted")
    quantity = amount(proposal.quantity, "quantity", positive=True)
    price = amount(proposal.limit_price, "limit price", positive=True)
    if amount(proposal.spread_fraction, "spread") > Decimal("0.005"):
        raise Blocked("spread too wide")
    for mapping in (state.positions, state.pending_buys):
        for symbol, value in mapping.items():
            amount(value, f"exposure {symbol}")
    cost = quantity * price
    reserved = sum(state.pending_buys.values(), Decimal(0))
    if cost + reserved > state.cash:
        raise Blocked("insufficient unreserved cash")
    symbol_exposure = state.positions.get(proposal.symbol, Decimal(0))
    symbol_pending = state.pending_buys.get(proposal.symbol, Decimal(0))
    if symbol_exposure + symbol_pending + cost > Decimal("400"):
        raise Blocked("position limit")
    occupied = {s for m in (state.positions, state.pending_buys) for s, v in m.items() if v > 0}
    if len(occupied | {proposal.symbol}) > 4:
        raise Blocked("position count")
    if sum(state.positions.values(), Decimal(0)) + reserved + cost > state.equity:
        raise Blocked("no borrowing")
    return cost
