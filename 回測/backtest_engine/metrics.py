"""
績效指標模組 — 全部用 NumPy 向量化計算，無迴圈。

必要指標: AR, MDD, Sharpe, Sortino
延伸指標: Calmar, Win Rate, Profit Factor, 年化波動率, 最大連續虧損
"""

import numpy as np
import pandas as pd


def annualized_return(equity_curve: np.ndarray, periods_per_year: float = 252) -> float:
    """年化報酬率 (AR)"""
    total_return = equity_curve[-1] / equity_curve[0]
    n_periods = len(equity_curve) - 1
    if n_periods <= 0:
        return 0.0
    return total_return ** (periods_per_year / n_periods) - 1


def max_drawdown(equity_curve: np.ndarray) -> float:
    """最大回撤 (MDD)，回傳負數（如 -0.15 代表 15% 回撤）"""
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    return float(np.min(drawdown))


def sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252,
) -> float:
    """Sharpe Ratio = (mean excess return / std) * sqrt(年化因子)"""
    excess = returns - risk_free_rate / periods_per_year
    std = np.std(excess, ddof=1)
    if std == 0:
        return 0.0
    return float(np.mean(excess) / std * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: float = 252,
) -> float:
    """Sortino Ratio — 只用下行波動率"""
    excess = returns - risk_free_rate / periods_per_year
    downside = excess[excess < 0]
    if len(downside) == 0:
        return float('inf') if np.mean(excess) > 0 else 0.0
    downside_std = np.sqrt(np.mean(downside ** 2))  # 半標準差 (semi-deviation)
    if downside_std == 0:
        return 0.0
    return float(np.mean(excess) / downside_std * np.sqrt(periods_per_year))


def calmar_ratio(equity_curve: np.ndarray, periods_per_year: float = 252) -> float:
    """Calmar Ratio = AR / |MDD|"""
    ar = annualized_return(equity_curve, periods_per_year)
    mdd = max_drawdown(equity_curve)
    if mdd == 0:
        return float('inf') if ar > 0 else 0.0
    return ar / abs(mdd)


def win_rate(returns: np.ndarray) -> float:
    """勝率 — 正報酬的比例"""
    nonzero = returns[returns != 0]
    if len(nonzero) == 0:
        return 0.0
    return float(np.sum(nonzero > 0) / len(nonzero))


def profit_factor(returns: np.ndarray) -> float:
    """獲利因子 = 總獲利 / 總虧損"""
    gains = np.sum(returns[returns > 0])
    losses = abs(np.sum(returns[returns < 0]))
    if losses == 0:
        return float('inf') if gains > 0 else 0.0
    return float(gains / losses)


def annualized_volatility(returns: np.ndarray, periods_per_year: float = 252) -> float:
    """年化波動率"""
    return float(np.std(returns, ddof=1) * np.sqrt(periods_per_year))


def max_consecutive_losses(returns: np.ndarray) -> int:
    """最大連續虧損天數"""
    is_loss = returns < 0
    if not np.any(is_loss):
        return 0
    # 用 diff 找連續段
    changes = np.diff(is_loss.astype(int), prepend=0)
    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]
    # 如果最後一段是虧損，補上結尾
    if len(ends) < len(starts):
        ends = np.append(ends, len(is_loss))
    if len(starts) == 0:
        return 0
    return int(np.max(ends - starts))


def total_return(equity_curve: np.ndarray) -> float:
    """總報酬率"""
    return float(equity_curve[-1] / equity_curve[0] - 1)


def compute_all_metrics(
    equity_curve: np.ndarray,
    returns: np.ndarray,
    periods_per_year: float = 252,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """一次算完所有指標，回傳字典。"""
    return {
        'total_return': total_return(equity_curve),
        'annualized_return': annualized_return(equity_curve, periods_per_year),
        'max_drawdown': max_drawdown(equity_curve),
        'sharpe_ratio': sharpe_ratio(returns, risk_free_rate, periods_per_year),
        'sortino_ratio': sortino_ratio(returns, risk_free_rate, periods_per_year),
        'calmar_ratio': calmar_ratio(equity_curve, periods_per_year),
        'annualized_volatility': annualized_volatility(returns, periods_per_year),
        'win_rate': win_rate(returns),
        'profit_factor': profit_factor(returns),
        'max_consecutive_losses': max_consecutive_losses(returns),
        'total_periods': len(returns),
    }


def format_metrics(metrics: dict[str, float]) -> str:
    """格式化指標為美觀的 terminal 輸出。"""
    lines = []
    fmt = {
        'total_return':          ('Total Return',       '{:>+10.2%}'),
        'annualized_return':     ('Annual Return (AR)', '{:>+10.2%}'),
        'max_drawdown':          ('Max Drawdown (MDD)', '{:>+10.2%}'),
        'sharpe_ratio':          ('Sharpe Ratio',       '{:>10.2f}'),
        'sortino_ratio':         ('Sortino Ratio',      '{:>10.2f}'),
        'calmar_ratio':          ('Calmar Ratio',       '{:>10.2f}'),
        'annualized_volatility': ('Ann. Volatility',    '{:>10.2%}'),
        'win_rate':              ('Win Rate',            '{:>10.1%}'),
        'profit_factor':         ('Profit Factor',      '{:>10.2f}'),
        'max_consecutive_losses':('Max Consec. Losses', '{:>10.0f}'),
        'total_periods':         ('Total Periods',      '{:>10.0f}'),
    }
    for key, (label, f) in fmt.items():
        val = metrics.get(key, 0)
        lines.append(f"  {label:<22s} {f.format(val)}")
    return '\n'.join(lines)
