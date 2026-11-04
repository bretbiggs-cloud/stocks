"""Durable order-intent deduplication. Never turns unknown submission into retry.

A single executor owns the ledger. Intent keys represent persistent strategy
decisions, not newly generated values for every retry. Recovery must reconcile
client_order_id against broker history before any subsequent submission.
"""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path


class Journal:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("CREATE TABLE IF NOT EXISTS intents (intent_key TEXT PRIMARY KEY, "
                        "client_id TEXT UNIQUE NOT NULL, payload TEXT NOT NULL, "
                        "status TEXT NOT NULL)")
        self.db.commit()

    def close(self):
        self.db.close()

    def reserve(self, key: str, payload: dict) -> str:
        """Durably reserve one intent before network I/O; duplicate attempts fail."""
        if not key.strip():
            raise ValueError("intent key required")
        client_id = "stocks-" + hashlib.sha256(key.encode()).hexdigest()[:32]
        encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
        with self.db:
            self.db.execute("INSERT INTO intents VALUES (?, ?, ?, 'reserved')",
                            (key, client_id, encoded))
        return client_id

    def mark(self, key: str, status: str):
        if status not in {"unknown", "acknowledged", "filled", "cancelled", "rejected"}:
            raise ValueError("invalid status")
        with self.db:
            cursor = self.db.execute("UPDATE intents SET status=? WHERE intent_key=?", (status, key))
            if cursor.rowcount != 1:
                raise KeyError(key)

    def unresolved(self):
        return self.db.execute("SELECT intent_key, client_id, payload, status FROM intents "
                               "WHERE status IN ('reserved','unknown','acknowledged')").fetchall()

    def backup(self, destination: Path):
        """SQLite's online backup captures committed state, including WAL contents."""
        with closing(sqlite3.connect(destination)) as target:
            self.db.backup(target)
