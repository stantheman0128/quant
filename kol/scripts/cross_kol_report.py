"""
cross_kol_report.py — 跨 KOL skill score 報告

對每個 KOL 跑 skill score（整體 + 多種 subset）並畫成可比較的表格 / 熱力圖。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from skill_score import add_direction, compute_skill_score, kol_skill_matrix  # noqa: E402


def section(title: str) -> None:
    print(f"\n{'=' * 78}\n  {title}\n{'=' * 78}")


def fmt_row(d: dict) -> str:
    if pd.isna(d.get("hit_rate")):
        return f"  n={d['n']:>4}  (insufficient samples)"
    sig = "★★" if d["p_value"] < 0.01 else ("★" if d["p_value"] < 0.05 else "  ")
    return (f"  n={d['n']:>4}  hit={d['hit_rate']:.3f}  "
            f"skill={d['skill_score']:+.3f}  ic={d.get('ic',float('nan')):+.3f}  "
            f"meanRet={d['mean_ret']:+.4f}  p={d['p_value']:.4f} {sig}")


def main():
    df = pd.read_parquet(ROOT / "data" / "unified_predictions.parquet")
    df = add_direction(df)
    df = df[df["ret_5d"].notna() & (df["direction"] != 0)].copy()
    print(f"Loaded {len(df)} rows with valid ret_5d & direction across {df['kol'].nunique()} KOLs")

    # ----------------------------------------------------------------
    section("1. 整體 KOL 比較（順著做 skill score）")
    # ----------------------------------------------------------------
    for kol in df["kol"].unique():
        sub = df[df["kol"] == kol]
        s = compute_skill_score(sub, "ret_5d", min_samples=20)
        print(f"\n{kol:18}  {fmt_row(s)}")

    # ----------------------------------------------------------------
    section("2. 每個 KOL × market subset")
    # ----------------------------------------------------------------
    for kol in df["kol"].unique():
        sub_kol = df[df["kol"] == kol]
        print(f"\n{kol}:")
        for mkt, sub in sub_kol.groupby("market"):
            s = compute_skill_score(sub, "ret_5d", min_samples=20)
            print(f"  market={mkt:6} {fmt_row(s)}")

    # ----------------------------------------------------------------
    section("3. 每個 KOL × conviction tier")
    # ----------------------------------------------------------------
    for kol in df["kol"].unique():
        sub_kol = df[df["kol"] == kol]
        print(f"\n{kol}:")
        for c in ["high", "mid", "low"]:
            sub = sub_kol[sub_kol["conviction"] == c]
            s = compute_skill_score(sub, "ret_5d", min_samples=15)
            print(f"  conv={c:4}  {fmt_row(s)}")

    # ----------------------------------------------------------------
    section("4. 每個 KOL × view direction（看多 vs 看空）")
    # ----------------------------------------------------------------
    for kol in df["kol"].unique():
        sub_kol = df[df["kol"] == kol]
        print(f"\n{kol}:")
        for d, label in [(+1, "看多/holding"), (-1, "看空/exit")]:
            sub = sub_kol[sub_kol["direction"] == d]
            s = compute_skill_score(sub, "ret_5d", min_samples=15)
            print(f"  view={label:14} {fmt_row(s)}")

    # ----------------------------------------------------------------
    section("5. 每個 KOL × symbol_type")
    # ----------------------------------------------------------------
    for kol in df["kol"].unique():
        sub_kol = df[df["kol"] == kol]
        print(f"\n{kol}:")
        for typ in sub_kol["symbol_type"].unique():
            sub = sub_kol[sub_kol["symbol_type"] == typ]
            s = compute_skill_score(sub, "ret_5d", min_samples=10)
            print(f"  type={typ:6} {fmt_row(s)}")

    # ----------------------------------------------------------------
    section("6. Top 10 顯著 (KOL × subset) by p-value")
    # ----------------------------------------------------------------
    matrix = kol_skill_matrix(df, "ret_5d", min_samples=15)
    matrix = matrix[matrix["hit_rate"].notna()].copy()
    matrix["abs_skill"] = matrix["skill_score"].abs()
    top = matrix.nsmallest(10, "p_value")
    cols = ["kol", "subset", "n", "hit_rate", "skill_score", "ic", "p_value"]
    print(top[cols].to_string(index=False))

    out = ROOT / "data" / "skill_matrix.csv"
    matrix.to_csv(out, index=False)
    print(f"\n→ matrix saved: {out}")


if __name__ == "__main__":
    main()
