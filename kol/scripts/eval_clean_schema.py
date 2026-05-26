"""
eval_clean_schema.py
--------------------
用 clean 4-field schema 跑下游因子評估，比較：
  Baseline A: direction only (忽略 weight)
  Weighted B: signal = direction × (2*weight - 1) (用歷史 WFE 加權)
  Filtered C: 只交易 weight > 0.55 的高信心訊號

評估指標：hit rate / IC / 多空 PnL Sharpe / drawdown
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean_schema.jsonl"
UNIFIED = ROOT / "data" / "unified_predictions.parquet"
OUT_REPORT = ROOT / "data" / "clean_schema_eval.json"


@dataclass
class EvalResult:
    name: str
    n: int
    n_with_ret: int
    hit_rate: float
    p_hit: float
    ic: float
    p_ic: float
    sharpe: float
    total_return: float
    max_drawdown: float
    win_rate_daily: float


def evaluate(df: pd.DataFrame, signal_col: str, name: str) -> EvalResult:
    """df: must have columns [signal_col, ret_5d, created_date]
       trades only on rows where signal != 0 and ret_5d is valid"""
    sub = df[(df[signal_col] != 0) & df["ret_5d"].notna()].copy()
    n = len(sub)
    if n == 0:
        return EvalResult(name, 0, 0, np.nan, np.nan, np.nan, np.nan, np.nan, 0, 0, 0)

    # hit rate: sign(signal) == sign(ret)
    sub["hit"] = (np.sign(sub[signal_col]) == np.sign(sub["ret_5d"])).astype(int)
    hr = sub["hit"].mean()
    p_hit = stats.binomtest(int(sub["hit"].sum()), n, 0.5, "two-sided").pvalue

    # IC: spearman(signal, ret)
    if sub[signal_col].std() > 0 and sub["ret_5d"].std() > 0:
        ic, p_ic = stats.spearmanr(sub[signal_col], sub["ret_5d"])
    else:
        ic, p_ic = np.nan, np.nan

    # daily PnL: signal direction × ret / 5 (攤平日均)
    sub["pnl"] = np.sign(sub[signal_col]) * sub["ret_5d"] / 5
    daily = sub.groupby("created_date")["pnl"].mean().sort_index()
    cum = (1 + daily).cumprod()
    sharpe = (daily.mean() / daily.std() * np.sqrt(252)) if daily.std() > 0 else 0
    dd = (cum / cum.cummax() - 1).min()
    win_d = (daily > 0).mean()
    total = cum.iloc[-1] - 1 if len(cum) else 0

    return EvalResult(
        name=name, n=n, n_with_ret=n,
        hit_rate=float(hr), p_hit=float(p_hit),
        ic=float(ic) if not pd.isna(ic) else np.nan,
        p_ic=float(p_ic) if not pd.isna(p_ic) else np.nan,
        sharpe=float(sharpe), total_return=float(total),
        max_drawdown=float(dd), win_rate_daily=float(win_d),
    )


def main() -> None:
    # 載入 clean schema
    clean = pd.read_json(CLEAN, lines=True)
    clean["timestamp"] = pd.to_datetime(clean["timestamp"]).dt.tz_localize(None)
    clean["created_date"] = clean["timestamp"].dt.normalize()
    print(f"[load] {len(clean)} clean records")

    # 載入 unified panel 取 ret_5d（按 (id, date) JOIN）
    uni = pd.read_parquet(UNIFIED)
    uni["created_date"] = pd.to_datetime(uni["created_date"]).dt.normalize()
    # priority: code_hint else symbol_name
    uni["id_match"] = uni["symbol_code"].fillna(uni["symbol_name"]).astype(str)

    # 簡單 inner join：clean.id ↔ uni.id_match + same date
    # 但同一 (id, date) 在 uni 可能有多筆 (多 KOL)，take first
    ret_lookup = uni.groupby(["id_match", "created_date"])["ret_5d"].first().reset_index()
    ret_lookup.columns = ["id", "created_date", "ret_5d"]

    df = clean.merge(ret_lookup, on=["id", "created_date"], how="left")
    print(f"[merge] with ret_5d: {df['ret_5d'].notna().sum()} / {len(df)}")

    # 三種訊號
    df["signal_baseline"] = df["direction"]                          # A: 純方向
    df["signal_weighted"] = df["direction"] * (2 * df["weight"] - 1) # B: 用 WFE 加權
    df["signal_filtered"] = df["direction"] * (df["weight"] > 0.55)  # C: 只交易高信心

    print()
    print("=" * 80)
    print("  下游因子評估 — 三種訊號比較")
    print("=" * 80)

    results = []
    for col, name in [
        ("signal_baseline", "A. Baseline (純方向，忽略 weight)"),
        ("signal_weighted", "B. WFE-weighted (direction × (2w-1))"),
        ("signal_filtered", "C. High-confidence filter (只交易 weight>0.55)"),
    ]:
        r = evaluate(df, col, name)
        results.append(r)
        print(f"\n{name}")
        print(f"  trades:        n={r.n}")
        print(f"  hit_rate:      {r.hit_rate:.3f}  (p={r.p_hit:.4f})")
        print(f"  IC:            {r.ic:+.4f}  (p={r.p_ic:.4f})")
        print(f"  Sharpe:        {r.sharpe:+.2f}")
        print(f"  total return:  {r.total_return:+.2%}")
        print(f"  max DD:        {r.max_drawdown:.2%}")
        print(f"  daily win:     {r.win_rate_daily:.2%}")

    # 額外：top-K KOL 切片 ranking
    print()
    print("=" * 80)
    print("  按 weight 分位看 hit rate (證明 walk-forward weight 有預測力)")
    print("=" * 80)
    df_valid = df[(df["direction"] != 0) & df["ret_5d"].notna()].copy()
    df_valid["weight_bucket"] = pd.cut(
        df_valid["weight"],
        bins=[0, 0.45, 0.5, 0.55, 0.6, 1.0],
        labels=["<0.45", "0.45-0.5", "=0.5(default)", "0.55-0.6", ">0.6"],
    )
    df_valid["aligned"] = (np.sign(df_valid["ret_5d"]) == df_valid["direction"]).astype(int)
    bucket_stats = df_valid.groupby("weight_bucket", observed=True)["aligned"].agg(["count", "mean"])
    bucket_stats.columns = ["n", "hit_rate"]
    print(bucket_stats.to_string())

    # 存 JSON 報告
    report = {
        "evaluations": [r.__dict__ for r in results],
        "weight_bucket_hit_rates": bucket_stats.reset_index().astype({"weight_bucket": str}).to_dict("records"),
        "n_clean_records": len(clean),
        "n_with_returns": int(df["ret_5d"].notna().sum()),
    }
    OUT_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    print(f"\n[report] → {OUT_REPORT}")


if __name__ == "__main__":
    main()
