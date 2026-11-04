"""Experimental ORB-v1: fixed rules, no claim of a profitable edge."""
from datetime import datetime, timedelta
from decimal import Decimal as D

VERSION = "orb-v1"
SYMBOLS = ("AAPL", "MSFT", "AMZN", "NVDA", "GOOGL", "META", "SPY", "QQQ")


def stamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timezone missing")
    return parsed


def number(value):
    v = D(str(value))
    if not v.is_finite() or v <= 0:
        raise ValueError("Positive finite market value required")
    return v


def signal(bars, session_open, now):
    """Only completed same-session bars. Returns diagnostics, including no-trade reasons."""
    rows = sorted((b for b in bars if session_open <= stamp(b["t"])
                   and stamp(b["t"]) + timedelta(minutes=1) <= now), key=lambda b: b["t"])
    if len(rows) < 21:
        return {"buy": False, "reason": "insufficient_completed_bars"}
    times = [stamp(b["t"]) for b in rows]
    if len(set(times)) != len(times):
        raise ValueError("Duplicate market bars")
    if now - times[-1] > timedelta(minutes=3):
        return {"buy": False, "reason": "stale_bars"}
    opening = [b for b in rows if stamp(b["t"]) < session_open + timedelta(minutes=15)]
    if len(opening) != 15 or any(times[-i] - times[-i-1] != timedelta(minutes=1)
                                  for i in range(1, 6)):
        return {"buy": False, "reason": "missing_bars"}
    high = max(number(b["h"]) for b in opening)
    volume = sum(number(b["v"]) for b in rows)
    vwap = sum(number(b.get("vw", b["c"])) * number(b["v"]) for b in rows) / volume
    last, previous = rows[-1], rows[-2]
    close = number(last["c"])
    recent_volume = sum(number(b["v"]) for b in rows[-21:-1]) / 20
    ratio = number(last["v"]) / recent_volume
    # Require a fresh crossing, not a late chase of an already extended breakout.
    buy = number(previous["c"]) <= high < close <= high * D("1.005") and close > vwap and ratio >= D("1.5")
    return {"buy": buy, "reason": "opening_range_breakout" if buy else "no_setup",
            "bar_time": last["t"], "close": str(close), "opening_high": str(high),
            "vwap": str(vwap), "volume_ratio": str(ratio)}
