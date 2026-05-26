"""
visualize.py — POC 結果視覺化

產出 4 張圖：
  1. equity curve (反指標 vs 順指標)
  2. hit_rate by conviction tier
  3. hit_rate by symbol_type
  4. ret_5d distribution split by direction
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT_DIR = Path(__file__).resolve().parent / "output"
PARQUET = OUT_DIR / "banini_predictions.parquet"

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def equity_curves(df: pd.DataFrame, ax: plt.Axes) -> None:
    """反指標 (direction) vs 順指標 (-direction) 的累積報酬曲線"""
    for label, sign in [("反指標 (banini-tracker 邏輯)", +1), ("順指標 (順著她做)", -1)]:
        sub = df.copy()
        sub["pnl"] = sign * sub["direction"] * sub["ret_5d"] / 5  # 攤 daily
        daily = sub.groupby("created_date")["pnl"].mean().sort_index()
        cum = (1 + daily).cumprod()
        ax.plot(cum.index, cum.values, label=label, linewidth=1.5)
    ax.axhline(1.0, color="gray", linestyle="--", alpha=0.5)
    ax.set_title("策略累積報酬：反指標 vs 順指標")
    ax.set_ylabel("累積報酬")
    ax.legend()
    ax.grid(alpha=0.3)


def hit_rate_bars(df: pd.DataFrame, group_col: str, ax: plt.Axes, title: str) -> None:
    rows = []
    for g, sub in df.groupby(group_col):
        if len(sub) < 5:
            continue
        sub = sub[sub["direction"] != 0]
        hit = (np.sign(sub["ret_5d"]) == sub["direction"]).mean()
        rows.append({"group": str(g), "hit_rate": hit, "n": len(sub)})
    r = pd.DataFrame(rows)
    bars = ax.bar(r["group"], r["hit_rate"], color="steelblue")
    ax.axhline(0.5, color="red", linestyle="--", alpha=0.7, label="隨機 (50%)")
    for b, n in zip(bars, r["n"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.01,
                f"n={n}", ha="center", fontsize=8)
    ax.set_title(title)
    ax.set_ylabel("反指標方向 hit rate")
    ax.set_ylim(0, max(0.7, r["hit_rate"].max() * 1.2))
    ax.legend()


def return_dist(df: pd.DataFrame, ax: plt.Axes) -> None:
    """ret_5d 在 reverse_view='空' vs '多' 的分布"""
    bins = np.linspace(-0.20, 0.20, 41)
    for label, d in [("反指標看空 (n=242)", -1), ("反指標看多 (n=63)", +1)]:
        sub = df[df["direction"] == d]["ret_5d"].dropna()
        ax.hist(sub.clip(-0.20, 0.20), bins=bins, alpha=0.5, label=label, density=True)
    ax.axvline(0, color="black", linestyle="-", alpha=0.5)
    ax.set_title("5 日報酬分布：依反指標方向")
    ax.set_xlabel("ret_5d")
    ax.set_ylabel("density")
    ax.legend()


def main() -> None:
    df = pd.read_parquet(PARQUET)

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    equity_curves(df, axes[0, 0])
    hit_rate_bars(df, "conviction_tier", axes[0, 1], "Hit rate by conviction tier")
    hit_rate_bars(df, "symbol_type", axes[1, 0], "Hit rate by symbol type")
    return_dist(df, axes[1, 1])

    fig.suptitle("Banini POC — 反指標假設驗證 (n=305, 2024-04 ~ 2026-04)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    out = OUT_DIR / "poc_results.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    print(f"[viz] → {out}")


if __name__ == "__main__":
    main()
