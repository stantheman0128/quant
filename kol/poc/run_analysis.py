"""
run_analysis.py — POC 主分析腳本

跑全套統計 + 印 go/no-go 決策表。不依賴 compute_kol_skill_score。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import metrics

OUT_DIR = Path(__file__).resolve().parent / "output"
PARQUET = OUT_DIR / "banini_predictions.parquet"

CONVICTION_WEIGHT = {"high": 1.5, "mid": 1.0, "low": 0.5}


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n  {title}\n{'=' * 72}")


def main() -> None:
    if not PARQUET.exists():
        sys.exit(f"先跑 ingest.py 產生 {PARQUET}")

    df = pd.read_parquet(PARQUET)
    df["signal"] = df["direction"] * df["conviction_tier"].map(CONVICTION_WEIGHT)
    print(f"\n[loaded] {len(df)} predictions, "
          f"{df['created_date'].min().date()} ~ {df['created_date'].max().date()}")

    # ------------------------------------------------------------------
    section("1. 整體 hit_rate（巴逆逆作為反指標的方向勝率）")
    # ------------------------------------------------------------------
    for h in ["ret_1d", "ret_2d", "ret_3d", "ret_5d"]:
        r = metrics.hit_rate(df["direction"], df[h])
        print(f"{h:8} {r}")

    # path-dependent: 5 日內任一刻反指標方向實現過？
    print("\n[path-dependent on 5d window]")
    df["realized"] = np.where(
        df["direction"] == 1,
        df["max_ret_5d"] >= 0.01,   # 反指標看漲 → 5 日內漲過 1%
        df["min_ret_5d"] <= -0.01,  # 反指標看跌 → 5 日內跌過 1%
    )
    n = len(df)
    n_realized = int(df["realized"].sum())
    print(f"  '反指標方向 5 日內達 ±1%' 比例: {n_realized}/{n} = {n_realized/n:.3f}")

    # ------------------------------------------------------------------
    section("2. Information Coefficient（conviction-weighted signal）")
    # ------------------------------------------------------------------
    for h in ["ret_1d", "ret_2d", "ret_3d", "ret_5d"]:
        ic = metrics.information_coefficient(df["signal"], df[h])
        print(f"{h:8} {ic}")

    # ------------------------------------------------------------------
    section("3. Long-Short PnL（每筆訊號等權，攤成日均）")
    # ------------------------------------------------------------------
    for h in ["ret_1d", "ret_3d", "ret_5d"]:
        p = metrics.long_short_pnl(df, horizon_col=h)
        print(f"{h:8} {p}")

    # ------------------------------------------------------------------
    section("4. Conviction monotonicity（高 conviction 應比低 conviction 更準）")
    # ------------------------------------------------------------------
    g = metrics.by_subgroup(df, "conviction_tier", "ret_5d")
    print(g.to_string(index=False))

    # ------------------------------------------------------------------
    section("5. 標的類型異質性")
    # ------------------------------------------------------------------
    g = metrics.by_subgroup(df, "symbol_type", "ret_5d")
    print(g.to_string(index=False))

    # ------------------------------------------------------------------
    section("6. Direction 異質性（看漲 vs 看跌訊號）")
    # ------------------------------------------------------------------
    g = metrics.by_subgroup(df, "direction", "ret_5d")
    print(g.to_string(index=False))

    # ------------------------------------------------------------------
    section("7. Regime check：分上下半段時間")
    # ------------------------------------------------------------------
    median_date = df["created_date"].median()
    df["regime"] = np.where(df["created_date"] < median_date, "early", "late")
    g = metrics.by_subgroup(df, "regime", "ret_5d")
    print(f"  split @ {median_date.date()}")
    print(g.to_string(index=False))

    # ------------------------------------------------------------------
    section("Go / No-Go 決策表")
    # ------------------------------------------------------------------
    overall = metrics.hit_rate(df["direction"], df["ret_5d"])
    ic5 = metrics.information_coefficient(df["signal"], df["ret_5d"])
    pnl5 = metrics.long_short_pnl(df, "ret_5d")

    rows = [
        ("Hit rate (5d)", f"{overall.rate:.3f}", "> 0.55 (p<0.05)",
         overall.rate > 0.55 and overall.p_value < 0.05),
        ("|IC| (5d, conv-weighted)", f"{abs(ic5.ic):.4f}", "> 0.05",
         abs(ic5.ic) > 0.05),
        ("Long-Short Sharpe (5d)", f"{pnl5.sharpe:+.2f}", "> 0.8",
         pnl5.sharpe > 0.8),
        ("Conviction monotonicity", "見上方", "high > mid > low", None),
    ]
    print(f"\n  {'指標':30} {'實際':>10}  {'門檻':<20}  通過")
    print("  " + "-" * 72)
    n_pass = 0
    for name, actual, threshold, passed in rows:
        mark = "—" if passed is None else ("✓" if passed else "✗")
        if passed:
            n_pass += 1
        print(f"  {name:30} {actual:>10}  {threshold:<20}  {mark}")

    print(f"\n  通過項目: {n_pass} / 3 (monotonicity 需肉眼判斷)")
    if n_pass >= 2:
        print("  → GO：信號有 edge，建議擴展到多 KOL")
    elif n_pass == 1:
        print("  → CONDITIONAL：限縮 scope 後再做")
    else:
        print("  → NO-GO：考慮 pivot")


if __name__ == "__main__":
    main()
