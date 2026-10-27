"""
Is the low-vs-high forward-return gap real?

Touches overlap heavily: a 20-day forward window after one touch shares most of its days
with the next touch's window, and touches cluster in the same few selloffs/rallies. So
the touches are NOT independent samples. Two tests that respect that:

1. Circular block bootstrap on CALENDAR TIME. The whole daily timeline (every day's
   forward return plus its touch flags) is resampled in contiguous blocks of b trading
   days, so overlap and clustering inside a block are preserved. Repeated for several b;
   if the answer depends on b, that's itself informative. p-values are two-sided from
   the centred bootstrap distribution.
2. Non-overlapping thinning: keep a touch only if it's >= horizon trading days after the
   previously kept touch ON THE SAME SIDE, so no two kept windows share a day. Welch t
   (normal approximation) on what's left.
Plus stability: the same difference by era and with the 2008-09 / 2020 crashes removed.
"""
import math

import numpy as np


def block_bootstrap(fwd, lo, hi, block, reps, rng, chunk=500):
    """Circular block bootstrap of (mean fwd | low touch) - (mean fwd | high touch)."""
    n = len(fwd)
    nblocks = -(-n // block)
    out = []
    for c0 in range(0, reps, chunk):
        r = min(chunk, reps - c0)
        starts = rng.integers(0, n, size=(r, nblocks))
        idx = ((starts[:, :, None] + np.arange(block)[None, None, :]) % n).reshape(r, -1)[:, :n]
        f, l, h = fwd[idx], lo[idx], hi[idx]
        with np.errstate(invalid="ignore", divide="ignore"):
            out.append((f * l).sum(1) / l.sum(1) - (f * h).sum(1) / h.sum(1))
    d = np.concatenate(out)
    return d[np.isfinite(d)]


def thin(dates_idx, gap):
    kept, last = [], -10 ** 9
    for i in sorted(dates_idx):
        if i - last >= gap:
            kept.append(i)
            last = i
    return kept


def welch(a, b):
    a, b = np.asarray(a), np.asarray(b)
    if len(a) < 2 or len(b) < 2:                    # variance undefined: report, don't guess
        return float(a.mean() - b.mean()), float("nan"), float("nan")
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    z = (a.mean() - b.mean()) / se
    p = math.erfc(abs(z) / math.sqrt(2))          # two-sided, normal approximation
    return float(a.mean() - b.mean()), float(z), p


def gap_test(close, events, horizon=20, blocks=(20, 60, 120, 250), reps=5000, seed=7):
    """Mean `horizon`-day return after 30-day-low touches minus after 30-day-high touches,
    with block-bootstrap CIs / p-values and a non-overlapping (thinned) Welch test."""
    fwd_s = (close.shift(-horizon) / close - 1)
    fwd_s = fwd_s[fwd_s.index >= events["date"].min()].dropna()
    pos = {d: i for i, d in enumerate(fwd_s.index)}
    fwd = fwd_s.to_numpy()
    lo, hi = np.zeros(len(fwd)), np.zeros(len(fwd))
    for d, side in zip(events["date"], events["side"]):
        if d in pos:
            (lo if side == "support" else hi)[pos[d]] = 1
    obs = fwd[lo == 1].mean() - fwd[hi == 1].mean()
    rng = np.random.default_rng(seed)
    boot = {}
    for b in blocks:
        d = block_bootstrap(fwd, lo, hi, b, reps, rng)
        boot[f"block_{b}d"] = {"ci95": [round(float(np.percentile(d, 2.5)), 5),
                                        round(float(np.percentile(d, 97.5)), 5)],
                               "p_two_sided": round(float((np.abs(d - obs) >= abs(obs)).mean()), 4)}
    tl, th = thin(np.flatnonzero(lo), horizon), thin(np.flatnonzero(hi), horizon)
    diff, z, p = welch(fwd[tl], fwd[th])
    return {"horizon": horizon, "n_low": int(lo.sum()), "n_high": int(hi.sum()),
            "mean_fwd_low": round(float(fwd[lo == 1].mean()), 5),
            "mean_fwd_high": round(float(fwd[hi == 1].mean()), 5),
            "mean_fwd_all_days": round(float(fwd.mean()), 5),
            "diff_low_minus_high": round(float(obs), 5), "block_bootstrap": boot,
            "non_overlapping": {"n_low": len(tl), "n_high": len(th), "diff": round(diff, 5),
                                "z": round(z, 3), "p_two_sided_normal": round(p, 4)}}
