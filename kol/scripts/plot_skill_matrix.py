"""
畫 cross-KOL skill matrix heatmap + 各 KOL equity curve。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from skill_score import add_direction  # noqa: E402

plt.rcParams["font.sans-serif"] = ["Microsoft JhengHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def main():
    matrix = pd.read_csv(ROOT / "data" / "skill_matrix.csv")
    matrix = matrix[matrix["hit_rate"].notna()].copy()

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # === Panel 1: skill_score heatmap (KOL × subset) ===
    ax = axes[0, 0]
    pivot = matrix.pivot_table(
        index="kol", columns="subset", values="skill_score", aggfunc="first"
    )
    # Sort columns: all first, then by category
    col_order = ["all"] + [c for c in pivot.columns if c != "all"]
    pivot = pivot.reindex(columns=col_order)
    im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=-0.5, vmax=0.5, aspect="auto")
    ax.set_xticks(range(len(pivot.columns))); ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index))); ax.set_yticklabels(pivot.index)
    ax.set_title("Skill score heatmap (red=反指標, green=正指標)")
    # Annotate cells
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            v = pivot.iloc[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:+.2f}", ha="center", va="center",
                        fontsize=8, color="black")
    plt.colorbar(im, ax=ax, label="skill_score")

    # === Panel 2: hit_rate by KOL × market ===
    ax = axes[0, 1]
    sub = matrix[matrix["subset"].str.startswith("market=")].copy()
    sub["market"] = sub["subset"].str.replace("market=", "")
    pivot = sub.pivot_table(index="kol", columns="market", values="hit_rate", aggfunc="first")
    pivot.plot(kind="bar", ax=ax, rot=0)
    ax.axhline(0.5, color="red", linestyle="--", alpha=0.7, label="random")
    ax.set_title("Hit rate by KOL × market")
    ax.set_ylabel("hit_rate (順著做)")
    ax.legend()

    # === Panel 3: hit_rate by KOL × conviction ===
    ax = axes[1, 0]
    sub = matrix[matrix["subset"].str.startswith("conv=")].copy()
    sub["conv"] = sub["subset"].str.replace("conv=", "")
    sub["conv"] = pd.Categorical(sub["conv"], categories=["high","mid","low"], ordered=True)
    pivot = sub.pivot_table(index="kol", columns="conv", values="hit_rate", aggfunc="first", observed=True)
    pivot.plot(kind="bar", ax=ax, rot=0)
    ax.axhline(0.5, color="red", linestyle="--", alpha=0.7)
    ax.set_title("Hit rate by KOL × conviction")
    ax.set_ylabel("hit_rate (順著做)")

    # === Panel 4: equity curve (cumulative ret) per KOL ===
    df = pd.read_parquet(ROOT / "data" / "unified_predictions.parquet")
    df = add_direction(df)
    df = df[df["ret_5d"].notna() & (df["direction"] != 0)].copy()
    df["pnl"] = df["direction"] * df["ret_5d"] / 5  # daily
    ax = axes[1, 1]
    for kol in df["kol"].unique():
        sub = df[df["kol"] == kol]
        daily = sub.groupby("created_date")["pnl"].mean().sort_index()
        cum = (1 + daily).cumprod()
        ax.plot(cum.index, cum.values, label=f"{kol} (n={len(sub)})", linewidth=1.5)
    ax.axhline(1.0, color="gray", linestyle="--", alpha=0.5)
    ax.set_title("順著做 累積報酬曲線（每訊號日均化攤分）")
    ax.set_ylabel("累積")
    ax.legend()
    ax.grid(alpha=0.3)
    ax.tick_params(axis='x', rotation=45)

    fig.suptitle("Cross-KOL Skill Analysis — 8zz vs panzheng_king vs uncle_us_notes",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    out = ROOT / "data" / "cross_kol_skill.png"
    fig.savefig(out, dpi=120, bbox_inches="tight")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
