"""
跨標的穩健性評分 — Cross-Sectional Robustness Scorer

方案 B：Portfolio Sharpe × Hit Rate（WorldQuant Fitness 變體）

Score = portfolio_sharpe × breadth_multiplier
  - breadth_multiplier = pct_positive × 2
  - hit rate 50% → ×1.0（基準）
  - hit rate 75% → ×1.5
  - hit rate 100% → ×2.0

Hard gate：pct_positive < 0.35 或 n_symbols < 10 → penalty mode
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class RobustnessScore:
    """跨標的穩健性評估結果"""
    portfolio_sharpe: float    # 等權組合 Sharpe（核心指標）
    median_sharpe: float       # 中位數 Sharpe（參考）
    mean_sharpe: float         # 平均 Sharpe（參考）
    pct_positive: float        # 正 Sharpe 的標的比例 (0~1)
    worst_10pctl: float        # 最��� 10th percentile Sharpe
    sharpe_std: float          # Sharpe 跨標的標準差（參考）
    median_sortino: float      # 參考
    median_ar: float           # 中位數年化報酬
    median_mdd: float          # 中位數最大回撤
    n_symbols: int             # 測試了幾個標的
    composite: float = 0.0     # 綜合分數

    def summary(self) -> str:
        lines = [
            f"  Portfolio Sharpe:  {self.portfolio_sharpe:>8.3f}  ← 核心",
            f"  Breadth (hit%):   {self.pct_positive:>8.1%}",
            f"  Median Sharpe:    {self.median_sharpe:>8.3f}",
            f"  Worst 10th pctl:  {self.worst_10pctl:>8.3f}",
            f"  Sharpe Std Dev:   {self.sharpe_std:>8.3f}",
            f"  Median Sortino:   {self.median_sortino:>8.3f}",
            f"  Median AR:        {self.median_ar:>8.2%}",
            f"  Median MDD:       {self.median_mdd:>8.2%}",
            f"  Symbols tested:   {self.n_symbols:>8d}",
            f"  ─────────────────────────────",
            f"  COMPOSITE SCORE:  {self.composite:>8.3f}",
        ]
        return '\n'.join(lines)


def compute_robustness(
    portfolio_sharpe: float,
    sharpes: list[float],
    sortinos: list[float],
    ars: list[float],
    mdds: list[float],
) -> RobustnessScore:
    """
    方案 B：Portfolio Sharpe × Breadth Multiplier

    Score = portfolio_sharpe × (pct_positive × 2)

    Hard gate: pct_positive < 0.35 or n < 10 → portfolio_sharpe - 10
    """
    s = np.array(sharpes, dtype=float)
    s = np.clip(s, -5, 5)

    median_sharpe = float(np.median(s))
    mean_sharpe = float(np.mean(s))
    pct_positive = float(np.mean(s > 0))
    worst_10pctl = float(np.percentile(s, 10))
    sharpe_std = float(np.std(s))

    so = np.clip(np.array(sortinos, dtype=float), -5, 5)
    median_sortino = float(np.median(so))

    median_ar = float(np.median(ars))
    median_mdd = float(np.median(mdds))

    # Hard gate
    if len(sharpes) < 10 or pct_positive < 0.35:
        composite = portfolio_sharpe - 10
    else:
        breadth_multiplier = pct_positive * 2
        composite = portfolio_sharpe * breadth_multiplier

    return RobustnessScore(
        portfolio_sharpe=portfolio_sharpe,
        median_sharpe=median_sharpe,
        mean_sharpe=mean_sharpe,
        pct_positive=pct_positive,
        worst_10pctl=worst_10pctl,
        sharpe_std=sharpe_std,
        median_sortino=median_sortino,
        median_ar=median_ar,
        median_mdd=median_mdd,
        n_symbols=len(sharpes),
        composite=composite,
    )
