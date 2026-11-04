"""Single-writer durable runtime state, reconciliation records, and consistent backups."""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from stocks.journal import Journal

TERMINAL = {"filled", "canceled", "expired", "rejected", "replaced"}


class Store(Journal):
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        super().__init__(Path(path))
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, time TEXT, kind TEXT, body TEXT);
        CREATE TABLE IF NOT EXISTS orders (client_id TEXT PRIMARY KEY, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS balances (time TEXT PRIMARY KEY, equity TEXT, cash TEXT);
        """)
        self.db.commit()

    def get(self, key, default=None):
        row = self.db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (key, json.dumps(value)))

    def event(self, now, kind, body):
        with self.db:
            self.db.execute("INSERT INTO events(time,kind,body) VALUES (?,?,?)",
                            (now.isoformat(), kind, json.dumps(body, allow_nan=False)))

    def known(self, client_id):
        return bool(self.db.execute("SELECT 1 FROM intents WHERE client_id=?", (client_id,)).fetchone())

    def exists(self, key):
        return bool(self.db.execute("SELECT 1 FROM intents WHERE intent_key=?", (key,)).fetchone())

    def record_order(self, key, order):
        if order["status"] == "filled":
            status = "filled"
        elif order["status"] in TERMINAL:
            status = "rejected" if order["status"] == "rejected" else "cancelled"
        else:
            status = "acknowledged"
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO orders VALUES (?,?)",
                            (order["client_order_id"], json.dumps(order)))
            self.db.execute("UPDATE intents SET status=? WHERE intent_key=?", (status, key))

    def order_rows(self):
        return [json.loads(r[0]) for r in self.db.execute("SELECT body FROM orders")]

    def checkpoint(self, root, day):
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        target = root / f"daily-{day}.sqlite"
        self.backup(target)
        with closing(sqlite3.connect(target)) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup verification failed")
        monthly = root / f"monthly-{day[:7]}.sqlite"
        self.backup(monthly)
        # Only our specifically named snapshots, never recursive deletion.
        for pattern, keep in (("daily-????-??-??.sqlite", 14), ("monthly-????-??.sqlite", 3)):
            for old in sorted(root.glob(pattern), reverse=True)[keep:]:
                old.unlink()
