"""One scheduler; no inbound ports, no LLM, no paid subscriptions."""
import argparse
import json
import os
from pathlib import Path
import signal
import time
from datetime import datetime, timezone

from stocks.broker import Broker
from stocks.engine import Engine
from stocks.store import Store


class HostGuard:
    def __init__(self, proc=Path("/host/proc")):
        self.proc = proc
        self.previous = None

    def __call__(self):
        # Production must have host metrics. Missing input blocks entries.
        try:
            mem = dict((line.split(":")[0], int(line.split()[1]))
                       for line in (self.proc / "meminfo").read_text().splitlines() if ":" in line)
            ticks = [int(v) for v in (self.proc / "stat").read_text().splitlines()[0].split()[1:9]]
            current = (sum(ticks), ticks[4])
            old, self.previous = self.previous, current
            if old is None or current[0] <= old[0]:
                return False
            return mem["MemAvailable"] >= 768 * 1024 and (current[1] - old[1]) / (current[0] - old[0]) <= .25
        except (OSError, ValueError, KeyError, IndexError):
            return False


class ProcessLock:
    def __init__(self, path):
        self.file = open(path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self.file.seek(0)
                if not self.file.read(1):
                    self.file.write(b"0")
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.file.close()
            raise

    def close(self):
        self.file.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--credentials", required=True)
    p.add_argument("--root", required=True)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    lock = ProcessLock(root / "executor.lock")
    store = Store(root / "ledger.sqlite")
    broker = Broker(args.credentials)
    engine = Engine(broker, store, root, host_ok=HostGuard())
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while not stopping:
            started = time.monotonic()
            try:
                # File is re-read every cycle. Removing it stops new submissions including exits.
                settings = json.loads((root / "settings.json").read_text())
                engine.enabled = settings.get("paper_enabled") is True
                if settings.get("pause_entries") is True:
                    store.put("review_lock", True)
                status = engine.tick()
                if status["market_open"]:
                    engine.benchmark()
                heartbeat = {"time": datetime.now(timezone.utc).isoformat(), "ok": True,
                             "mode": status["mode"], "canary": store.get("canary")}
            except Exception as exc:
                # Never emit exception bodies, HTTP requests, credentials, or raw responses.
                now = datetime.now(timezone.utc)
                heartbeat = {"time": now.isoformat(), "ok": False, "error_type": type(exc).__name__,
                             "attention": "Cycle failed; no additional entries this cycle. Inspect private ledger."}
                store.event(now, "cycle_failed", heartbeat)
            (root / "heartbeat.json.tmp").write_text(json.dumps(heartbeat), encoding="utf-8")
            (root / "heartbeat.json.tmp").replace(root / "heartbeat.json")
            print(json.dumps(heartbeat), flush=True)
            if args.once:
                return 0 if heartbeat["ok"] else 1
            for _ in range(max(1, int(60 - (time.monotonic() - started)))):
                if stopping:
                    break
                time.sleep(1)
    finally:
        store.close()
        lock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
