"""
跨標的穩健性評分 — Cross-Sectional Robustness Scorer

Score = Portfolio Sharpe（業界標準）

等權組合 63 個標的的 returns，計算組合 Sharpe。
天然包含分散化效果和跨標的一致性。

Hard constraint: pct_positive < 0.35 → penalty
Diagnostics: median_sharpe, pct_positive, worst_10pctl, sharpe_std
"""

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm


@dataclass
class RobustnessScore:
    """跨標的穩健性評估結果"""
    portfolio_sharpe: float    # 等權組合 Sharpe（= composite）
    median_sharpe: float       # 中位數 Sharpe（診斷）
    mean_sharpe: float         # 平均 Sharpe（診斷）
    pct_positive: float        # 正 Sharpe 的標的比例（診斷）
    worst_10pctl: float        # 最差 10th percentile Sharpe（診斷）
    sharpe_std: float          # Sharpe 跨標的標準差（診斷）
    median_sortino: float      # 診斷
    median_ar: float           # 中位數年化報酬（診斷）
    median_mdd: float          # 中位數最大回撤（診斷）
    n_symbols: int
    composite: float = 0.0

    def summary(self) -> str:
        lines = [
            f"  Portfolio Sharpe:  {self.portfolio_sharpe:>8.3f}  ← SCORE",
            f"  Hit Rate:         {self.pct_positive:>8.1%}",
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
    Score = Portfolio Sharpe

    Hard constraint: pct_positive < 0.35 or n < 10 → portfolio_sharpe - 10
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

    # Hard constraint: if <35% of symbols profitable, strategy doesn't generalize
    # (Removed n_symbols<10 check — that's a group-size concern, handled by DSR
    # at composite level in evaluate.py. Commod only has 5 symbols by design.)
    if pct_positive < 0.35:
        composite = portfolio_sharpe - 10
    else:
        composite = portfolio_sharpe

    return RobustnessScore(
        portfolio_sharpe=float(portfolio_sharpe),
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


def deflated_sharpe_ratio(observed_sr: float, n_trials: int, n_returns: int,
                          skew: float = 0.0, kurtosis: float = 3.0) -> float:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado).

    Returns p-value: probability that the observed Sharpe is real
    (not just the best out of n_trials random strategies).

    > 0.95: very likely real
    0.50-0.95: uncertain
    < 0.50: likely noise
    """
    if n_trials < 2 or n_returns < 10 or observed_sr <= 0:
        return 0.0

    euler_gamma = 0.5772156649
    log_n = np.log(n_trials)

    # Expected max Sharpe under null hypothesis
    sr0 = np.sqrt(2 * log_n) * (1 - euler_gamma / (2 * log_n))

    # Standard error of Sharpe estimate
    se = np.sqrt(
        (1 + 0.5 * observed_sr**2
         - skew * observed_sr
         + (kurtosis - 3) / 4 * observed_sr**2)
        / (n_returns - 1)
    )

    if se < 1e-10:
        return 0.0

    return float(norm.cdf((observed_sr - sr0) / se))


def dsr_quality_adjustment(composite: float, dsr: float) -> float:
    """
    Adjust composite score by DSR (quality multiplier).

    Only applies to POSITIVE composites — negative scores pass through
    unchanged (no "rewarding bad strategies by halving them").

    - DSR >= 0.5: no adjustment (strategy looks real)
    - 0.2 <= DSR < 0.5: composite × 0.5 (suspicious)
    - DSR < 0.2: composite × 0.2 (very likely noise)

    Rationale: DSR encodes "given multiple testing, how likely is this real?"
    Applied as gentle multiplier rather than hard cutoff to avoid Goodhart's Law
    (agent optimizing DSR itself rather than strategy quality).
    """
    if composite <= 0:
        return composite
    if dsr < 0.2:
        return composite * 0.2
    if dsr < 0.5:
        return composite * 0.5
    return composite
