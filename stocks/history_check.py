"""Resumable historical research only. No order submission or deployment."""
import argparse
from collections import deque
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
from stocks.broker import Broker
from stocks.compare import CANDIDATES, features, run
from stocks.engine import ET
from stocks.strategy import SYMBOLS


def plan(start, end, calendar):
    days = [d for d in calendar if start <= d["date"] <= end]
    if len(days) < 100:
        raise ValueError("At least 100 sessions required")
    usable = days[14:]
    a, b = int(len(usable)*.6), int(len(usable)*.8)
    return {"calendar": days, "phases": {"development": [d["date"] for d in usable[:a]],
            "validation": [d["date"] for d in usable[a:b]],
            "holdout": [d["date"] for d in usable[b:]]}}


def prepared(manifest, root, dates):
    history = {s: deque(maxlen=14) for s in SYMBOLS}
    wanted = set(dates)
    for day in manifest["calendar"]:
        p = root / (day["date"]+".json")
        raw = p.read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest["sha256"][p.name]:
            raise ValueError("Cached data hash mismatch")
        result = features(day, json.loads(raw), history)
        if day["date"] in wanted:
            yield result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--credentials")
    p.add_argument("--years", type=int, choices=(1,5), default=5)
    p.add_argument("--end", default=(date.today()-timedelta(days=1)).isoformat())
    p.add_argument("--max-download-sessions", type=int, default=25)
    p.add_argument("--evaluate", choices=CANDIDATES)
    p.add_argument("--include-holdout", action="store_true")
    args=p.parse_args();root=Path(args.root);root.mkdir(parents=True,exist_ok=True)
    mp=root/"manifest.json"
    if mp.exists():
        manifest=json.loads(mp.read_text())
    else:
        if not args.credentials: p.error("Credentials needed to initialize/download")
        end=date.fromisoformat(args.end)
        if end>=date.today(): p.error("Use completed dates only")
        start=end-timedelta(days=365*args.years)
        broker=Broker(args.credentials)
        calendar=broker.request("/v2/calendar",params={"start":start.isoformat(),"end":end.isoformat()})
        manifest=plan(start.isoformat(),end.isoformat(),calendar)
        manifest.update(years=args.years,end=args.end,sha256={},symbols=list(SYMBOLS),feed="iex",adjustment="raw",
                        rules_sha256=hashlib.sha256(Path(__file__).with_name("compare.py").read_bytes()).hexdigest(),
                        limitation="Fixed current universe; IEX-only OHLC, not production quote/fill replay. News strategy unsupported without point-in-time news. Previously inspected dates are not unseen.")
        mp.write_text(json.dumps(manifest,indent=2))
    if args.evaluate:
        if len(manifest["sha256"])!=len(manifest["calendar"]): p.error("Incomplete cache; evaluation refused")
        if hashlib.sha256(Path(__file__).with_name("compare.py").read_bytes()).hexdigest()!=manifest["rules_sha256"]:
            p.error("Rules changed: create a new versioned experiment")
        phases={k:v for k,v in manifest["phases"].items() if k!="holdout" or args.include_holdout}
        report={"strategy":args.evaluate,"manifest_sha256":hashlib.sha256(mp.read_bytes()).hexdigest(),
                "limitations":manifest["limitation"],"cash_benchmark_pnl":0,"qualified":False,"results":{}}
        for phase,dates in phases.items():
            report["results"][phase]={}
            for label,cost in (("base_10bps",.001),("stress_20bps",.002)):
                report["results"][phase][label]=run(args.evaluate,prepared(manifest,root,dates),cost)
        # Reading the holdout is permanently logged; never market it as unseen again.
        if args.include_holdout:
            with (root/"holdout-access.jsonl").open("a") as f:
                f.write(json.dumps({"time":datetime.now(ET).isoformat(),"strategy":args.evaluate})+"\n")
        out=root/(args.evaluate+"-"+datetime.now(ET).strftime("%Y%m%dT%H%M%S")+".json")
        out.write_text(json.dumps(report,indent=2));print(str(out));return
    if not args.credentials: p.error("Credentials needed for downloading")
    broker=Broker(args.credentials);downloaded=0
    for day in manifest["calendar"]:
        name=day["date"]+".json";file=root/name
        if name in manifest["sha256"]:
            if hashlib.sha256(file.read_bytes()).hexdigest()!=manifest["sha256"][name]:
                raise ValueError("Cached data hash mismatch")
            continue
        if downloaded>=args.max_download_sessions: break
        opening=datetime.fromisoformat(day["date"]+"T"+day["open"]).replace(tzinfo=ET)
        closing=datetime.fromisoformat(day["date"]+"T"+day["close"]).replace(tzinfo=ET)
        bars=broker.bars(SYMBOLS,opening.isoformat(),closing.isoformat())
        raw=json.dumps(bars,separators=(",", ":")).encode();tmp=file.with_suffix(".tmp");tmp.write_bytes(raw);tmp.replace(file)
        manifest["sha256"][name]=hashlib.sha256(raw).hexdigest()
        tmp=mp.with_suffix(".tmp");tmp.write_text(json.dumps(manifest,indent=2));tmp.replace(mp)
        downloaded+=1
    print(json.dumps({"cached":len(manifest["sha256"]),"required":len(manifest["calendar"]),"complete":len(manifest["sha256"])==len(manifest["calendar"])}))

if __name__=="__main__": main()
