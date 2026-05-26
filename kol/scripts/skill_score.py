"""
skill_score.py — KOL 多向度 skill 評分 (cross-sectional ranking)

對每個 (KOL × subset) 算一個 skill_score ∈ [-1, +1]：
  +1 = 完美正指標 (KOL 看漲就漲)
  -1 = 完美反指標 (KOL 看漲就跌)
   0 = 雜訊
  NaN = 樣本不足

支援多種 subset breakdown：
  - 整體 (all)
  - 按 market (TW vs US)
  - 按 conviction tier (high/mid/low)
  - 按 view direction (bullish vs bearish)
  - 按 symbol_type (個股 vs ETF vs 指數)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


VIEW_TO_DIRECTION = {
    "bullish": +1,
    "bearish": -1,
    "holding_long": +1,   # 持有 = 隱含看漲（不認賠）
    "exit": -1,           # 停損 = 認跌
    "neutral": 0,
}


def add_direction(df: pd.DataFrame) -> pd.DataFrame:
    """把 view 欄位轉成 +1 / -1 / 0 (KOL 的方向觀點)."""
    df = df.copy()
    df["direction"] = df["view"].map(VIEW_TO_DIRECTION).fillna(0).astype(int)
    return df


def compute_skill_score(
    df: pd.DataFrame,
    horizon_col: str = "ret_5d",
    min_samples: int = 30,
    metric: str = "hit_rate",
) -> dict:
    """
    對 df (預設整個 subset) 算 skill_score + 統計顯著性。

    回傳 dict:
      n: 有效樣本數
      hit_rate: 順著做 hit rate (sign(view)==sign(ret))
      skill_score: 2 * (hit_rate - 0.5)，範圍 [-1, +1]
      p_value: binomial test p
      ic: information coefficient (spearman of view*conviction vs ret)
      mean_ret: KOL 方向 × 報酬的平均（含 direction sign）
    """
    sub = df[(df["direction"] != 0) & df[horizon_col].notna()].copy()
    n = len(sub)

    if n < min_samples:
        return {"n": n, "hit_rate": np.nan, "skill_score": np.nan,
                "p_value": np.nan, "ic": np.nan, "mean_ret": np.nan,
                "note": f"samples<{min_samples}"}

    # hit rate (順著 KOL 方向)
    sub["aligned"] = (np.sign(sub[horizon_col]) == sub["direction"]).astype(int)
    hits = int(sub["aligned"].sum())
    hr = hits / n
    skill = 2 * (hr - 0.5)
    p = stats.binomtest(hits, n, 0.5, "two-sided").pvalue

    # IC (conviction-weighted)
    conv_w = sub["conviction"].map({"high": 1.5, "mid": 1.0, "low": 0.5}).fillna(1.0)
    signal = sub["direction"] * conv_w
    if signal.std() > 0 and sub[horizon_col].std() > 0:
        ic, _ = stats.spearmanr(signal, sub[horizon_col])
    else:
        ic = np.nan

    # 順著做的 mean ret
    mean_ret = (sub["direction"] * sub[horizon_col]).mean()

    return {"n": n, "hit_rate": hr, "skill_score": skill,
            "p_value": p, "ic": ic, "mean_ret": mean_ret}


def by_subset(
    df: pd.DataFrame,
    group_col: str,
    horizon_col: str = "ret_5d",
    min_samples: int = 20,
) -> pd.DataFrame:
    """對每個 group 跑 skill score."""
    rows = []
    for g, sub in df.groupby(group_col):
        s = compute_skill_score(sub, horizon_col, min_samples)
        rows.append({group_col: g, **s})
    return pd.DataFrame(rows).sort_values("n", ascending=False)


def kol_skill_matrix(
    df: pd.DataFrame,
    horizon_col: str = "ret_5d",
    min_samples: int = 20,
) -> pd.DataFrame:
    """每 (KOL × subset_key) 的 skill score 矩陣，方便 heatmap."""
    rows = []
    for kol, sub_kol in df.groupby("kol"):
        # 整體
        s = compute_skill_score(sub_kol, horizon_col, min_samples=min_samples)
        rows.append({"kol": kol, "subset": "all", **s})
        # by market
        for mkt, sub in sub_kol.groupby("market"):
            s = compute_skill_score(sub, horizon_col, min_samples)
            rows.append({"kol": kol, "subset": f"market={mkt}", **s})
        # by conviction
        for c, sub in sub_kol.groupby("conviction"):
            s = compute_skill_score(sub, horizon_col, min_samples)
            rows.append({"kol": kol, "subset": f"conv={c}", **s})
        # by direction
        for d, sub in sub_kol.groupby("direction"):
            if d == 0:
                continue
            s = compute_skill_score(sub, horizon_col, min_samples)
            rows.append({"kol": kol, "subset": f"view={'多' if d>0 else '空'}", **s})
    return pd.DataFrame(rows)
