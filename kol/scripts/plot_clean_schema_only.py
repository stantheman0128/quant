"""
plot_clean_schema_only.py
-------------------------
**只**用 clean 4-field schema (timestamp, id, direction, weight) 產出視覺化。
不引用 conviction / market / symbol_type 等 rich-panel 欄位。
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean_schema.jsonl"
UNIFIED = ROOT / "data" / "unified_predictions.parquet"  # 只用來 join ret_5d
OUT_DIR = ROOT / "docs"

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def load_clean_with_returns() -> pd.DataFrame:
    """純 clean schema + 從 unified panel join ret_5d (用來算 hit rate)."""
    clean = pd.read_json(CLEAN, lines=True)
    clean["timestamp"] = pd.to_datetime(clean["timestamp"]).dt.tz_localize(None)
    clean["created_date"] = clean["timestamp"].dt.normalize()
    uni = pd.read_parquet(UNIFIED)
    uni["created_date"] = pd.to_datetime(uni["created_date"]).dt.normalize()
    uni["id_match"] = uni["symbol_code"].fillna(uni["symbol_name"]).astype(str)
    ret_lookup = uni.groupby(["id_match", "created_date"])["ret_5d"].first().reset_index()
    ret_lookup.columns = ["id", "created_date", "ret_5d"]
    df = clean.merge(ret_lookup, on=["id", "created_date"], how="left")
    return df


# ============================================================================
#  Chart 1: weight 分布 histogram
# ============================================================================
def fig_weight_distribution(df: pd.DataFrame) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    weights = df["weight"]
    ax.hist(weights, bins=50, color="#1f77b4", edgecolor="white", alpha=0.85)
    median = weights.median()
    mean = weights.mean()
    ax.axvline(median, color="red", linestyle="--", label=f"median = {median:.3f}")
    ax.axvline(mean, color="green", linestyle="--", label=f"mean = {mean:.3f}")
    ax.axvline(0.5, color="gray", linestyle=":", alpha=0.7, label="random (0.5)")
    ax.set_xlabel("weight (歷史 walk-forward hit rate)")
    ax.set_ylabel("訊號數")
    ax.set_title("Weight 分布 — 所有 1739 個 clean schema 訊號",
                 fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT_DIR / "weight_distribution.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out


# ============================================================================
#  Chart 2: direction × weight bucket 的 hit rate 矩陣
# ============================================================================
def fig_direction_weight_matrix(df: pd.DataFrame) -> Path:
    sub = df[(df["direction"] != 0) & df["ret_5d"].notna()].copy()
    sub["aligned"] = (np.sign(sub["ret_5d"]) == sub["direction"]).astype(int)
    sub["weight_bucket"] = pd.cut(
        sub["weight"], bins=[0, 0.45, 0.5, 0.55, 0.6, 1.0],
        labels=["<0.45", "0.45-0.5", "=0.5", "0.55-0.6", ">0.6"],
    )
    sub["dir_label"] = sub["direction"].map({1: "看多 (+1)", -1: "看空 (-1)"})

    pvt = sub.pivot_table(
        index="dir_label", columns="weight_bucket",
        values="aligned", aggfunc="mean", observed=True,
    )
    cnt = sub.pivot_table(
        index="dir_label", columns="weight_bucket",
        values="aligned", aggfunc="count", observed=True,
    )

    fig, ax = plt.subplots(figsize=(11, 4))
    im = ax.imshow(pvt.values, cmap="RdYlGn", vmin=0.4, vmax=0.7, aspect="auto")
    ax.set_xticks(range(len(pvt.columns)))
    ax.set_xticklabels(pvt.columns)
    ax.set_yticks(range(len(pvt.index)))
    ax.set_yticklabels(pvt.index)
    ax.set_xlabel("weight bucket")
    for i in range(len(pvt.index)):
        for j in range(len(pvt.columns)):
            v = pvt.iloc[i, j]
            n = cnt.iloc[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v*100:.1f}%\nn={int(n)}",
                        ha="center", va="center", fontsize=9, color="black")
    plt.colorbar(im, ax=ax, label="hit rate (順著做)")
    ax.set_title("Hit Rate by Direction × Weight Bucket — direction+weight 共決定品質",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    out = OUT_DIR / "direction_weight_matrix.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out


# ============================================================================
#  Chart 3: 訊號隨時間的數量與 direction 平衡
# ============================================================================
def fig_signal_timeline(df: pd.DataFrame) -> Path:
    df["month"] = df["created_date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby(["month", "direction"]).size().unstack(fill_value=0)
    # rename columns for legend
    monthly = monthly.rename(columns={1: "看多 (+1)", 0: "觀望 (0)", -1: "看空 (-1)"})
    # ensure column order
    cols = [c for c in ["看多 (+1)", "觀望 (0)", "看空 (-1)"] if c in monthly.columns]
    monthly = monthly[cols]

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    # Top: stacked bar
    monthly.plot(kind="bar", stacked=True, ax=axes[0],
                 color=["#2ca02c", "#bdbdbd", "#d62728"])
    axes[0].set_ylabel("月訊號數")
    axes[0].set_title("月度訊號量（按 direction 堆疊）", fontsize=12, fontweight="bold")
    axes[0].legend(loc="upper left")
    axes[0].set_xlabel("")

    # Bottom: bullish ratio
    total = monthly.sum(axis=1)
    bull_ratio = monthly.get("看多 (+1)", 0) / total.replace(0, np.nan)
    axes[1].plot(range(len(bull_ratio)), bull_ratio.values,
                 "o-", color="#2ca02c", linewidth=2, markersize=7)
    axes[1].axhline(0.5, color="gray", linestyle="--", alpha=0.6, label="50%")
    axes[1].set_ylabel("看多訊號比例")
    axes[1].set_title("看多比例隨時間變化", fontsize=12, fontweight="bold")
    axes[1].set_xticks(range(len(monthly)))
    axes[1].set_xticklabels([d.strftime("%Y-%m") for d in monthly.index],
                             rotation=45, ha="right")
    axes[1].set_ylim(0, 1)
    axes[1].grid(alpha=0.3)
    axes[1].legend()

    fig.tight_layout()
    out = OUT_DIR / "signal_timeline.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out


# ============================================================================
#  Chart 4: Top 20 most-mentioned IDs，色階 = 平均 weight
# ============================================================================
def fig_top_ids(df: pd.DataFrame) -> Path:
    sub = df[df["direction"] != 0].copy()
    grp = sub.groupby("id").agg(
        n=("direction", "count"),
        avg_weight=("weight", "mean"),
        bull_ratio=("direction", lambda x: (x > 0).mean()),
    ).reset_index()
    top = grp.nlargest(20, "n").iloc[::-1]  # 反向讓最大的在頂部

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = plt.cm.RdYlGn((top["avg_weight"] - 0.4) / 0.3)  # 0.4-0.7 → 0-1
    bars = ax.barh(top["id"], top["n"], color=colors, edgecolor="black", linewidth=0.5)
    for bar, w, br in zip(bars, top["avg_weight"], top["bull_ratio"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"avg_w={w:.2f}, 多={br*100:.0f}%",
                va="center", fontsize=8)
    ax.set_xlabel("訊號數")
    ax.set_title("Top 20 最常被提及的標的 — 色階 = 平均 weight",
                 fontsize=13, fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
    sm = plt.cm.ScalarMappable(cmap="RdYlGn",
                               norm=plt.Normalize(vmin=0.4, vmax=0.7))
    sm.set_array([])
    plt.colorbar(sm, ax=ax, label="平均 weight", shrink=0.7)
    fig.tight_layout()
    out = OUT_DIR / "top_ids.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    df = load_clean_with_returns()
    print(f"loaded {len(df)} rows from clean schema")
    for fn in (fig_weight_distribution, fig_direction_weight_matrix,
               fig_signal_timeline, fig_top_ids):
        p = fn(df)
        print(f"→ {p.name}")


if __name__ == "__main__":
    main()
