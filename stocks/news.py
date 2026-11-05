"""Deterministic news-activity filter, not sentiment or confirmed catalyst analysis."""
from datetime import timedelta
from stocks.strategy import SYMBOLS, stamp

VERSION = "news-volume-v1"


def eligible_articles(rows, symbol, now, *, hours=2):
    selected = {}
    for row in rows:
        try:
            created, updated = stamp(row["created_at"]), stamp(row["updated_at"])
            observed = stamp(row["first_observed_at"])
            if (symbol not in row["symbols"] or not row.get("source") or
                    not row.get("url", "").startswith("https://") or
                    not row.get("headline") or not isinstance(row["id"], int)):
                continue
            if now - timedelta(hours=hours) <= created <= updated <= now and created <= observed <= now:
                selected[row["id"]] = row
        except (KeyError, TypeError, ValueError):
            continue
    return list(selected.values())


def observe_news(broker, store, now, *, symbols=SYMBOLS, hours=2):
    key = VERSION + ":news" if symbols == SYMBOLS and hours == 2 else "daily-news:" + str(hours) + ":" + ",".join(symbols)
    cached = store.get(key)
    if cached and timedelta(0) <= now - stamp(cached["time"]) < timedelta(minutes=5):
        return cached
    try:
        rows = broker.news(symbols, (now - timedelta(hours=hours)).isoformat(), now.isoformat())
        clean = []
        for row in rows:
            # Preserve first observation per article revision, never backdate availability.
            revision = f"news-observed:{row['id']}:{row['updated_at']}"
            observed = store.get(revision)
            if observed is None:
                observed = now.isoformat()
                store.put(revision, observed)
            item = {k: row.get(k) for k in
                    ("id", "symbols", "source", "url", "headline", "created_at", "updated_at")}
            item["first_observed_at"] = observed
            clean.append(item)
        cached = {"time": now.isoformat(), "ok": True, "articles": clean}
    except Exception:
        cached = {"time": now.isoformat(), "ok": False, "articles": [],
                  "reason": "news_unavailable_or_incomplete"}
    store.put(key, cached)
    store.event(now, "news_observation", cached)
    return cached
