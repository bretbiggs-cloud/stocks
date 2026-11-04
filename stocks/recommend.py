"""Compare three historically evaluated research candidates; never trades."""
import argparse
import hashlib
import json
import math
from pathlib import Path

NAMES = {"orb_baseline": "Opening-range breakout", "relative_volume_orb": "Relative-volume opening-range breakout", "noise_momentum": "Intraday noise-band momentum"}
DESCRIPTIONS = {
    "orb_baseline": "A price breakout with VWAP and recent-volume confirmation.",
    "relative_volume_orb": "An opening breakout focused on unusually active stocks relative to prior sessions.",
    "noise_momentum": "A breakout beyond a band derived from prior intraday price moves."}


def finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Evidence requires finite numeric metrics")
    return value


def recommend(report):
    if not isinstance(report.get("phases"), dict) or not report.get("limitations"):
        raise ValueError("Missing evaluation periods or limitations")
    for phase in ("validation", "holdout"):
        period = report["phases"][phase]
        if not period.get("start") or not period.get("end") or finite(period["sessions"]) <= 0:
            raise ValueError("Incomplete evaluation period")
    cards=[]
    for key,name in NAMES.items():
        source=report.get("candidates", {}).get(key)
        card={"id":key,"name":name,"description":DESCRIPTIONS[key],"status":"missing_evidence", "eligible_for_further_review":False}
        if source is not None:
            outcomes={}
            passes=True
            for cost in ("base", "stress"):
                outcomes[cost]={}
                for phase in ("validation", "holdout"):
                    r=source[cost][phase]
                    metrics={k:finite(r[k]) for k in ("net_modeled_pnl","trade_count","win_rate","max_drawdown")}
                    if metrics["trade_count"]<0 or metrics["max_drawdown"]<0 or not 0<=metrics["win_rate"]<=1:
                        raise ValueError("Invalid outcome metrics")
                    if not isinstance(r["review_locked"],bool) or not isinstance(r["incomplete_exit_days"],list):
                        raise ValueError("Missing risk/data quality evidence")
                    metrics.update(review_locked=r["review_locked"],incomplete_exit_days=r["incomplete_exit_days"])
                    outcomes[cost][phase]=metrics
                    passes &= metrics["net_modeled_pnl"]>0 and not r["review_locked"] and not r["incomplete_exit_days"]
            trades=sum(outcomes["base"][p]["trade_count"] for p in ("validation","holdout"))
            lower=finite(source["lower_mean_daily_pnl"])
            passes=bool(passes and trades>=20 and lower>0)
            card.update(status="passes_reported_screen" if passes else "failed_screen",eligible_for_further_review=passes,
                        outcomes=outcomes,lower_mean_daily_pnl=lower,
                        combined_base_pnl=sum(outcomes["base"][p]["net_modeled_pnl"] for p in ("validation","holdout")))
        cards.append(card)
    cards.sort(key=lambda c:(c["eligible_for_further_review"],c.get("combined_base_pnl",float("-inf"))),reverse=True)
    eligible=[c["id"] for c in cards if c["eligible_for_further_review"]]
    return {"options":cards,"suggested_for_further_review":eligible[0] if eligible else None,
            "decision":"review_candidate" if eligible else "none_qualified",
            "periods":report["phases"],"limitations":report["limitations"],
            "benchmark":report.get("spy_buy_hold_modeled_pnl"),"cash_benchmark_pnl":report.get("cash_benchmark_pnl"),
            "notice":"Research comparison only, not a buy recommendation or deployment approval. Sorting by these inspected outcomes cannot establish fresh out-of-sample performance. Periods shown are the actual evidence; no five-year claim is implied."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",required=True,help="Private comparison.json produced by stocks.compare")
    p.add_argument("--output",required=True,help="Private JSON report destination")
    a=p.parse_args();raw=Path(a.evidence).read_bytes()
    result=recommend(json.loads(raw));result["evidence_sha256"]=hashlib.sha256(raw).hexdigest()
    target=Path(a.output)
    if target.resolve()==Path(a.evidence).resolve():p.error("Output must not overwrite evidence")
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps({"decision":result["decision"],"options":[{"name":c["name"],"status":c["status"]} for c in result["options"]]}))

if __name__=="__main__":main()
