"""
向量化回測引擎核心

核心邏輯：
  strategy_return[t] = signal[t-1] * price_return[t]
  signal shift(1) 防止 lookahead bias — 用「昨天的信號」乘「今天的報酬」
"""

import numpy as np
import pandas as pd

from .strategy import Strategy
from .metrics import compute_all_metrics


class BacktestResult:
    """封裝回測結果"""

    def __init__(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        signals: pd.Series,
        prices: pd.DataFrame,
        trades: pd.DataFrame,
        metrics: dict[str, float],
        strategy_name: str,
        symbol: str,
        freq: str,
    ):
        self.equity_curve = equity_curve
        self.returns = returns
        self.signals = signals
        self.prices = prices
        self.trades = trades
        self.metrics = metrics
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.freq = freq


def _detect_trades(signals: pd.Series) -> pd.DataFrame:
    """
    從信號序列中偵測交易（進出場點位）。

    回傳 DataFrame:
      entry_time, exit_time, direction (1/-1), duration (bars)
    """
    sig = signals.values
    idx = signals.index

    trades = []
    position = 0
    entry_idx = 0

    for i in range(len(sig)):
        if sig[i] != position:
            # 如果有持倉，記錄出場
            if position != 0:
                trades.append({
                    'entry_time': idx[entry_idx],
                    'exit_time': idx[i],
                    'direction': position,
                    'duration': i - entry_idx,
                })
            # 如果有新信號，記錄進場
            if sig[i] != 0:
                entry_idx = i
            position = sig[i]

    # 如果最後還有持倉，記錄未平倉
    if position != 0:
        trades.append({
            'entry_time': idx[entry_idx],
            'exit_time': idx[-1],
            'direction': position,
            'duration': len(sig) - 1 - entry_idx,
        })

    if not trades:
        return pd.DataFrame(columns=['entry_time', 'exit_time', 'direction', 'duration'])

    return pd.DataFrame(trades)


def _estimate_periods_per_year(freq: str) -> float:
    """根據 resample 頻率估算年化因子。"""
    freq_lower = freq.lower()
    mapping = {
        '1min': 252 * 24 * 60,   # 假設 24h 市場 (forex)
        '5min': 252 * 24 * 12,
        '15min': 252 * 24 * 4,
        '1h': 252 * 24,
        '4h': 252 * 6,
        '1d': 252,
    }
    return mapping.get(freq_lower, 252)


def run_backtest(
    prices: pd.DataFrame,
    strategy: Strategy,
    symbol: str = "",
    freq: str = "1H",
    commission: float = 0.0,
    initial_capital: float = 10000.0,
) -> BacktestResult:
    """
    執行向量化回測。

    Parameters
    ----------
    prices    : OHLCV DataFrame (from data_loader)
    strategy  : Strategy 實例
    symbol    : 標的名稱 (顯示用)
    freq      : 數據頻率 (用於年化計算)
    commission: 每次交易的成本 (佔交易金額比例，如 0.0001 = 1 pip)
    initial_capital : 初始資金

    Returns
    -------
    BacktestResult
    """
    # 1. 產生信號
    signals = strategy.generate_signals(prices)

    # 2. 計算價格報酬率
    price_returns = prices['close'].pct_change().fillna(0)

    # 3. 策略報酬 = 前一期信號 × 當期報酬（防止 lookahead bias）
    shifted_signals = signals.shift(1).fillna(0)
    strategy_returns = shifted_signals * price_returns

    # 4. 扣除交易成本（信號改變時）
    signal_changes = shifted_signals.diff().fillna(0).abs()
    # Commission + 真實 spread 成本
    # spread 是絕對值，除以 close 轉成報酬率，除以 2 因為 mid→bid/ask 各半
    spread_cost = signal_changes * (prices['spread'] / prices['close'] / 2).fillna(0)
    cost = signal_changes * commission + spread_cost
    strategy_returns = strategy_returns - cost

    # 5. 計算 equity curve
    equity_curve = initial_capital * (1 + strategy_returns).cumprod()

    # 6. 偵測交易
    trades = _detect_trades(signals)

    # 7. 計算績效指標
    periods_per_year = _estimate_periods_per_year(freq)
    # 過濾掉零報酬（非交易期間），用於更精確的指標計算
    active_returns = strategy_returns[shifted_signals != 0]

    metrics = compute_all_metrics(
        equity_curve=equity_curve.values,
        returns=strategy_returns.values,
        periods_per_year=periods_per_year,
    )
    metrics['total_trades'] = len(trades)

    return BacktestResult(
        equity_curve=equity_curve,
        returns=strategy_returns,
        signals=signals,
        prices=prices,
        trades=trades,
        metrics=metrics,
        strategy_name=str(strategy),
        symbol=symbol,
        freq=freq,
    )
