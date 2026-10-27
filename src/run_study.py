#!/usr/bin/env python3
"""
Run the 30-day high/low study on each index and write results/.

  python src/run_study.py [--start 2005-01-01] [--end YYYY-MM-DD] [--reps 5000]

Per index: results/<NAME>_events.csv (every touch, its outcome and forward returns),
and one combined results/summary.json with outcome rates, the effect of the 2-day hold
rule on breaks, and the low-vs-high significance test.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

import data
import levels
import significance

ROOT = Path(__file__).resolve().parent.parent
INDEXES = {"SPY": "SPY", "SPX": "^GSPC", "QQQ": "QQQ", "IWM": "IWM"}
RULES = dict(lookback=30, tol=0.005, horizon=5, vol_mult=1.5, vol_window=20, rev_pct=0.01)


def run_index(name, ticker, start, end, reps):
    df = data.load(ticker, start, end)
    ev = levels.find_events(df, hold=2, **RULES)
    ev_nohold = levels.find_events(df, hold=0, **RULES)
    ev.to_csv(ROOT / "results" / f"{name}_events.csv", index=False)

    hold_effect = {}
    for side in ("resistance", "support"):
        a, b = ev_nohold[ev_nohold.side == side], ev[ev.side == side]
        n = len(b)
        hold_effect[side] = {
            "volume_breaks": int((a.outcome == "break").sum()),
            "confirmed_by_hold": int((b.outcome == "break").sum()),
            "break_rate_no_hold": round(float((a.outcome == "break").sum() / n), 4),
            "break_rate_hold_2": round(float((b.outcome == "break").sum() / n), 4)}

    return {"ticker": ticker, "bars": len(df), "first": int(df.index[0]), "last": int(df.index[-1]),
            "touches": levels.summarise(ev), "hold_rule": hold_effect,
            "low_vs_high_20d": significance.gap_test(df["Close"], ev, reps=reps)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2005-01-01")
    ap.add_argument("--end", default=(pd.Timestamp.today() - pd.Timedelta(days=1)).strftime("%Y-%m-%d"))
    ap.add_argument("--reps", type=int, default=5000)
    a = ap.parse_args()
    (ROOT / "results").mkdir(exist_ok=True)

    out = {"rules": RULES, "hold": 2, "indexes": {}}
    for name, ticker in INDEXES.items():
        out["indexes"][name] = r = run_index(name, ticker, a.start, a.end, a.reps)
        g = r["low_vs_high_20d"]
        print(f"[{name}] {r['first']}-{r['last']}  touches high {g['n_high']} / low {g['n_low']}  "
              f"gap {g['diff_low_minus_high']:+.4f}  p(60d blocks) "
              f"{g['block_bootstrap']['block_60d']['p_two_sided']}  "
              f"non-overlapping {g['non_overlapping']['diff']:+.4f} "
              f"(p {g['non_overlapping']['p_two_sided_normal']})", flush=True)
    (ROOT / "results" / "summary.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
