"""
metrics.py — KOL 訊號統計指標

提供 4 類診斷指標，回答「這個 KOL 的反指標訊號有沒有統計顯著的 edge」：
  1. hit_rate：方向勝率 + binomial test
  2. information_coefficient：訊號強度 vs 報酬的 Spearman
  3. long_short_pnl：把訊號當成日內等權多空組合
  4. compute_kol_skill_score：★ 留給使用者實作（核心 design choice）
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class HitRateResult:
    n: int
    hits: int
    rate: float
    p_value: float  # H0: rate = 0.5
    ci_low: float
    ci_high: float

    def __str__(self) -> str:
        sig = "★" if self.p_value < 0.05 else " "
        return (f"  hit_rate = {self.rate:.3f}  (n={self.n}, hits={self.hits}, "
                f"p={self.p_value:.4f} {sig}, 95% CI=[{self.ci_low:.3f}, {self.ci_high:.3f}])")


def hit_rate(direction: pd.Series, returns: pd.Series) -> HitRateResult:
    """
    direction: +1 (反指標看漲, 我們 long) / -1 (反指標看跌, 我們 short) / 0 (skip)
    returns: 對應的未來報酬
    Hit = sign(return) == direction（即反指標方向與實際方向一致）
    """
    df = pd.DataFrame({"d": direction, "r": returns}).dropna()
    df = df[df["d"] != 0]
    if len(df) == 0:
        return HitRateResult(0, 0, np.nan, np.nan, np.nan, np.nan)

    df["hit"] = (np.sign(df["r"]) == df["d"]).astype(int)
    n = len(df)
    hits = int(df["hit"].sum())
    rate = hits / n

    # 兩尾 binomial test
    res = stats.binomtest(hits, n, p=0.5, alternative="two-sided")
    ci = res.proportion_ci(confidence_level=0.95)
    return HitRateResult(n, hits, rate, res.pvalue, ci.low, ci.high)


@dataclass
class ICResult:
    n: int
    ic: float
    p_value: float

    def __str__(self) -> str:
        sig = "★" if self.p_value < 0.05 else " "
        return f"  IC (Spearman) = {self.ic:+.4f}  (n={self.n}, p={self.p_value:.4f} {sig})"


def information_coefficient(signal: pd.Series, returns: pd.Series) -> ICResult:
    """signal: 連續強度 (e.g. direction × conviction_weight). returns: 未來報酬."""
    df = pd.DataFrame({"s": signal, "r": returns}).dropna()
    if len(df) < 10:
        return ICResult(len(df), np.nan, np.nan)
    rho, p = stats.spearmanr(df["s"], df["r"])
    return ICResult(len(df), rho, p)


@dataclass
class PnLResult:
    n_days: int
    n_trades: int
    total_return: float
    daily_mean: float
    daily_std: float
    sharpe: float       # 年化（×√252）
    win_rate: float
    max_drawdown: float

    def __str__(self) -> str:
        sig = "★" if self.sharpe > 0.8 else " "
        return (f"  trades={self.n_trades}, days={self.n_days}, "
                f"total={self.total_return:+.2%}, sharpe={self.sharpe:+.2f} {sig}, "
                f"daily μ={self.daily_mean:+.4%} σ={self.daily_std:.4%}, "
                f"DD={self.max_drawdown:.2%}, win={self.win_rate:.1%}")


def long_short_pnl(
    predictions: pd.DataFrame,
    horizon_col: str = "ret_5d",
    market_relative: bool = False,
    benchmark_col: str | None = None,
) -> PnLResult:
    """
    每個 prediction 視為一筆等權交易：
      direction × ret_5d / horizon_days = 日均報酬貢獻
    將同一交易日多筆訊號等權加總，模擬日內多空組合。

    market_relative=True：扣掉同期 benchmark 報酬（去除多頭市場 drag）
    """
    df = predictions.copy()
    df = df[df["direction"] != 0].dropna(subset=[horizon_col])
    if len(df) == 0:
        return PnLResult(0, 0, 0, 0, 0, 0, 0, 0)

    horizon_days = int(horizon_col.split("_")[1].rstrip("d"))
    df["pos_ret"] = df["direction"] * df[horizon_col]
    if market_relative and benchmark_col is not None:
        df["pos_ret"] = df["direction"] * (df[horizon_col] - df[benchmark_col])
    df["daily_contrib"] = df["pos_ret"] / horizon_days  # 攤成 daily

    # 同日訊號等權加總
    daily = df.groupby("created_date")["daily_contrib"].mean()
    if len(daily) == 0:
        return PnLResult(0, 0, 0, 0, 0, 0, 0, 0)

    cum = (1 + daily).cumprod()
    dd = (cum / cum.cummax() - 1).min()
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0

    return PnLResult(
        n_days=len(daily),
        n_trades=len(df),
        total_return=cum.iloc[-1] - 1,
        daily_mean=daily.mean(),
        daily_std=daily.std(),
        sharpe=sharpe,
        win_rate=(daily > 0).mean(),
        max_drawdown=dd,
    )


def by_subgroup(
    predictions: pd.DataFrame, group_col: str, horizon_col: str = "ret_5d"
) -> pd.DataFrame:
    """每個 subgroup 跑 hit_rate，看訊號異質性。"""
    rows = []
    for g, sub in predictions.groupby(group_col):
        h = hit_rate(sub["direction"], sub[horizon_col])
        rows.append({
            "group": g, "n": h.n, "hits": h.hits,
            "hit_rate": h.rate, "p_value": h.p_value,
        })
    return pd.DataFrame(rows).sort_values("n", ascending=False)


# ============================================================================
#  ★ 你的 contribution：compute_kol_skill_score
# ============================================================================
#
#  這是整個 POC 的 epistemological core —— 「什麼叫一個 KOL 有 skill」。
#  以下三個決策是 design choice，沒有正確答案，但你要能為自己選的辯護。
#
#  決策點：
#    1. min_samples           樣本不足時的處理閾值
#    2. decay_halflife_days   時間加權衰減（近期 vs 遠期樣本權重）
#    3. metric                hit_rate / IC / sharpe — 哪個當 skill proxy
#
#  TODO:
#    a) 樣本 < min_samples → return np.nan
#    b) 對每個 prediction 算 age_days = (today - created_date)
#       權重 w = 0.5 ** (age_days / decay_halflife_days)
#    c) 根據 metric 計算對應 skill：
#       - hit_rate: 加權勝率 - 0.5（範圍化到 [-0.5, 0.5]，再 ×2 變 [-1, 1]）
#       - IC:       weighted Spearman approximation 或 simple weighted Pearson(rank, rank)
#       - sharpe:   weighted long-short pnl sharpe / 5（normalize 到接近 [-1, 1]）
#
#  提示：pandas 的 .corr() 不支援 weights，可以用：
#      np.cov(x, y, aweights=w) / (weighted_std(x) * weighted_std(y))
#
def compute_kol_skill_score(
    predictions: pd.DataFrame,
    today: pd.Timestamp,
    min_samples: int = 30,
    decay_halflife_days: int = 60,
    metric: str = "hit_rate",
    horizon_col: str = "ret_5d",
) -> float:
    """
    回傳 [-1, +1] 範圍：
      +1 = 完美正指標（KOL 看漲就漲）
      -1 = 完美反指標（KOL 看漲就跌）
       0 = 雜訊
      NaN = 樣本不足

    參數:
      predictions: 必須包含 direction, created_date, {horizon_col} 三欄
      today: 計算「現在」的時點（用於時間衰減）
      min_samples: 最少樣本數，不夠 return NaN
      decay_halflife_days: 半衰期（60 天 = 2 個月前的樣本權重 0.5）
      metric: 'hit_rate' | 'IC' | 'sharpe'

    >>> 你來實作 <<<
    """
    raise NotImplementedError(
        "請實作 compute_kol_skill_score。\n"
        "決策點 1 — min_samples：30 寬鬆 / 100 嚴格\n"
        "決策點 2 — halflife：30 天反應快 / 180 天統計穩\n"
        "決策點 3 — metric：hit_rate 直觀 / IC 用強度 / sharpe 含波動\n"
        "三個都沒有正確答案，但要能在面試辯護。"
    )
