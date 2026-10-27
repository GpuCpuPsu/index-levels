#!/usr/bin/env python3
"""Charts for the README, drawn from results/summary.json -> docs/img/*.png."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img"

# validated reference palette (adjacent CVD dE >= 9.1); light slots carry direct labels
SURFACE, INK, INK2, MUTED, GRID, BASE = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
OUTCOMES = [("bounce", "bounce", "#2a78d6"), ("break", "break (volume + held 2 days)", "#eb6834"),
            ("failed_break", "failed break", "#1baf7a"), ("weak_break", "break on low volume", "#eda100"),
            ("unresolved", "unresolved in 5 days", "#e87ba4")]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": ["Segoe UI", "DejaVu Sans", "sans-serif"], "font.size": 10,
    "axes.edgecolor": BASE, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 9,
})


def chart_gap(s):
    names = list(s["indexes"])
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    for row, name in enumerate(names):
        g = s["indexes"][name]["low_vs_high_20d"]
        lo, hi = (v * 100 for v in g["block_bootstrap"]["block_60d"]["ci95"])
        d = g["diff_low_minus_high"] * 100
        p = g["block_bootstrap"]["block_60d"]["p_two_sided"]
        thin = g["non_overlapping"]["diff"] * 100
        ax.plot([lo, hi], [row, row], color="#2a78d6", lw=3, solid_capstyle="round", alpha=0.45)
        ax.plot([d], [row], "o", ms=9, color="#2a78d6", mec=SURFACE, mew=2, zorder=3,
                label="all touches, 95% range from block bootstrap" if row == 0 else None)
        ax.plot([thin], [row], "D", ms=6, color=SURFACE, mec=INK2, mew=1.5, zorder=3,
                label="non-overlapping touches only" if row == 0 else None)
        ax.text(hi + 0.08, row, f"{d:+.2f} pp   p = {p:.2f}", va="center", color=INK2, fontsize=9)
    ax.axvline(0, color=INK, lw=1)
    ax.set_yticks(range(len(names)), names)
    ax.invert_yaxis()
    ax.set_xlim(right=ax.get_xlim()[1] + 0.9)
    ax.set_xlabel("20-day return after 30-day-low touches minus after 30-day-high touches (pp)")
    ax.set_title("Lows beat highs on every index, but the 95% range always includes zero")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / "gap_by_index.png", dpi=150)


def chart_outcomes(s):
    names = list(s["indexes"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True)
    for ax, side, title in ((axes[0], "resistance", "At the 30-day HIGH"),
                            (axes[1], "support", "At the 30-day LOW")):
        for row, name in enumerate(names):
            rates = s["indexes"][name]["touches"][side]["outcome_rates"]
            left = 0.0
            for key, label, color in OUTCOMES:
                v = rates.get(key, 0) * 100
                ax.barh(row, v, left=left, color=color, height=0.6, edgecolor=SURFACE,
                        linewidth=2, label=label if row == 0 else None)
                if v >= 6:
                    ax.text(left + v / 2, row, f"{v:.0f}%", ha="center", va="center",
                            color=INK, fontsize=9, fontweight="bold")
                left += v
        ax.set_title(title)
        ax.set_xlim(0, 100)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(names)), names)
    axes[0].invert_yaxis()
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=5, bbox_to_anchor=(0.5, -0.01))
    fig.suptitle("What happens after an index touches its 30-day high or low (2005-2026)",
                 x=0.01, ha="left", fontweight="bold", color=INK)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(OUT / "outcomes_by_index.png", dpi=150)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = json.loads((ROOT / "results" / "summary.json").read_text())
    chart_gap(s)
    chart_outcomes(s)
    print(f"[charts] wrote {sorted(p.name for p in OUT.glob('*.png'))}")


if __name__ == "__main__":
    main()
