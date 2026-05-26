"""
plot_poc_results.py — POC 報告專用視覺化

產出 3 張圖：
  1. equity_curves.png — 三種訊號（Baseline / Weighted / Filtered）累積報酬比較
  2. weight_bucket.png — walk-forward weight 預測力（按 bucket 分組 hit rate）
  3. signal_summary.png — 三種訊號的 hit / Sharpe / IC summary
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean_schema.jsonl"
UNIFIED = ROOT / "data" / "unified_predictions.parquet"
OUT_DIR = ROOT / "data"

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def load_merged() -> pd.DataFrame:
    clean = pd.read_json(CLEAN, lines=True)
    clean["timestamp"] = pd.to_datetime(clean["timestamp"]).dt.tz_localize(None)
    clean["created_date"] = clean["timestamp"].dt.normalize()
    uni = pd.read_parquet(UNIFIED)
    uni["created_date"] = pd.to_datetime(uni["created_date"]).dt.normalize()
    uni["id_match"] = uni["symbol_code"].fillna(uni["symbol_name"]).astype(str)
    ret_lookup = uni.groupby(["id_match", "created_date"])["ret_5d"].first().reset_index()
    ret_lookup.columns = ["id", "created_date", "ret_5d"]
    df = clean.merge(ret_lookup, on=["id", "created_date"], how="left")
    df["signal_baseline"] = df["direction"]
    df["signal_weighted"] = df["direction"] * (2 * df["weight"] - 1)
    df["signal_filtered"] = df["direction"] * (df["weight"] > 0.55)
    return df


def fig_equity_curves(df: pd.DataFrame) -> Path:
    """三種訊號的累積報酬曲線"""
    fig, ax = plt.subplots(figsize=(11, 5))
    for col, label, color in [
        ("signal_baseline", "A. Baseline (純方向)", "#1f77b4"),
        ("signal_weighted", "B. WFE-weighted", "#ff7f0e"),
        ("signal_filtered", "C. Confidence filter (w>0.55)", "#2ca02c"),
    ]:
        sub = df[(df[col] != 0) & df["ret_5d"].notna()].copy()
        sub["pnl"] = np.sign(sub[col]) * sub["ret_5d"] / 5
        daily = sub.groupby("created_date")["pnl"].mean().sort_index()
        cum = (1 + daily).cumprod()
        ax.plot(cum.index, cum.values, label=f"{label}  (n={len(sub)})",
                color=color, linewidth=1.6)
    ax.axhline(1.0, color="gray", linestyle="--", alpha=0.5)
    ax.set_title("三種訊號的累積報酬曲線", fontsize=13, fontweight="bold")
    ax.set_ylabel("累積報酬倍數")
    ax.legend(loc="upper left")
    ax.grid(alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()
    out = OUT_DIR / "equity_curves.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_weight_bucket(df: pd.DataFrame) -> Path:
    """walk-forward weight 分位數 vs hit rate 證明預測力"""
    sub = df[(df["direction"] != 0) & df["ret_5d"].notna()].copy()
    sub["aligned"] = (np.sign(sub["ret_5d"]) == sub["direction"]).astype(int)
    sub["weight_bucket"] = pd.cut(
        sub["weight"], bins=[0, 0.45, 0.5, 0.55, 0.6, 1.0],
        labels=["<0.45\n(無 skill)", "0.45-0.5\n(弱)", "=0.5\n(預設)",
                "0.55-0.6\n(中)", ">0.6\n(強 skill)"],
    )
    stats = sub.groupby("weight_bucket", observed=True)["aligned"].agg(["count", "mean"])
    stats.columns = ["n", "hit_rate"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(range(len(stats)), stats["hit_rate"],
                  color=["#d62728", "#ff9896", "#c7c7c7", "#aec7e8", "#1f77b4"])
    ax.axhline(0.5, color="red", linestyle="--", alpha=0.6, label="隨機 (50%)")
    for i, (bucket, row) in enumerate(stats.iterrows()):
        ax.text(i, row["hit_rate"] + 0.01,
                f"{row['hit_rate']*100:.1f}%\nn={row['n']}",
                ha="center", fontsize=9)
    ax.set_xticks(range(len(stats)))
    ax.set_xticklabels(stats.index)
    ax.set_ylabel("Hit Rate (順著做)")
    ax.set_ylim(0, 0.75)
    ax.set_title("Walk-Forward Weight 預測力驗證 — 高 weight → 高 hit rate",
                 fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out = OUT_DIR / "weight_bucket.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_signal_summary() -> Path:
    """三種訊號的 hit / Sharpe / IC 三併排"""
    report = json.loads((OUT_DIR / "clean_schema_eval.json").read_text())
    evals = report["evaluations"]
    labels = ["A. Baseline", "B. WFE-weighted", "C. Filtered (w>0.55)"]
    hits = [e["hit_rate"] for e in evals]
    sharpes = [e["sharpe"] for e in evals]
    ics = [e["ic"] for e in evals]
    ns = [e["n"] for e in evals]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    # Hit rate
    ax = axes[0]
    bars = ax.bar(labels, hits, color=colors)
    ax.axhline(0.5, color="red", linestyle="--", alpha=0.6, label="隨機")
    for b, v, n in zip(bars, hits, ns):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.005,
                f"{v*100:.1f}%\nn={n}", ha="center", fontsize=9)
    ax.set_ylim(0.45, 0.62)
    ax.set_title("Hit Rate (順著做)")
    ax.legend()
    ax.tick_params(axis='x', rotation=15)

    # Sharpe
    ax = axes[1]
    bars = ax.bar(labels, sharpes, color=colors)
    for b, v in zip(bars, sharpes):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.03,
                f"{v:+.2f}", ha="center", fontsize=10)
    ax.set_title("Annualized Sharpe (越高越好)")
    ax.set_ylim(0, max(sharpes) * 1.2)
    ax.tick_params(axis='x', rotation=15)

    # IC
    ax = axes[2]
    bars = ax.bar(labels, ics, color=colors)
    for b, v in zip(bars, ics):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.003,
                f"{v:+.4f}", ha="center", fontsize=9)
    ax.set_title("Information Coefficient")
    ax.set_ylim(0, max(ics) * 1.2)
    ax.tick_params(axis='x', rotation=15)

    fig.suptitle("三種訊號評估比較 — Filter 全面勝出", fontsize=13, fontweight="bold")
    fig.tight_layout()
    out = OUT_DIR / "signal_summary.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    df = load_merged()
    print(f"loaded {len(df)} rows")
    p1 = fig_equity_curves(df); print(f"→ {p1.name}")
    p2 = fig_weight_bucket(df); print(f"→ {p2.name}")
    p3 = fig_signal_summary(); print(f"→ {p3.name}")


if __name__ == "__main__":
    main()
