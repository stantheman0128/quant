"""
策略模組 — 基底類 + 內建策略

所有策略都繼承 Strategy，實作 generate_signals()。
信號約定: 1=做多, -1=做空, 0=空倉
"""

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class Strategy(ABC):
    """策略基底類"""

    name: str = "BaseStrategy"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        根據 OHLCV DataFrame 產生交易信號。

        Parameters
        ----------
        df : DataFrame with columns: open, high, low, close

        Returns
        -------
        Series of signals: 1 (long), -1 (short), 0 (flat)
        同 index 同長度
        """
        pass

    def __repr__(self) -> str:
        return f"{self.name}"


# ─── 內建策略 ─────────────────────────────────────


class BuyAndHold(Strategy):
    """買入持有 — 最簡單的基準策略"""

    name = "BuyAndHold"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(1, index=df.index)


class SMACrossover(Strategy):
    """
    雙均線交叉策略

    快線上穿慢線 → 做多
    快線下穿慢線 → 做空
    """

    def __init__(self, fast: int = 20, slow: int = 50):
        self.fast = fast
        self.slow = slow
        self.name = f"SMA({fast}/{slow})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        sma_fast = df['close'].rolling(self.fast).mean()
        sma_slow = df['close'].rolling(self.slow).mean()

        signal = pd.Series(0, index=df.index)
        signal[sma_fast > sma_slow] = 1
        signal[sma_fast < sma_slow] = -1

        return signal


class MACDStrategy(Strategy):
    """
    MACD 交叉策略

    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal_period)

    MACD > Signal → 做多
    MACD < Signal → 做空
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal_period: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period
        self.name = f"MACD({fast}/{slow}/{signal_period})"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df['close']
        ema_fast = close.ewm(span=self.fast, adjust=False).mean()
        ema_slow = close.ewm(span=self.slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()

        signal = pd.Series(0, index=df.index)
        signal[macd_line > signal_line] = 1
        signal[macd_line < signal_line] = -1

        return signal


class BollingerBands(Strategy):
    """
    布林通道策略

    價格觸及下軌 → 做多（均值回歸）
    價格觸及上軌 → 做空
    回到中軌 → 平倉
    """

    def __init__(self, period: int = 20, num_std: float = 2.0):
        self.period = period
        self.num_std = num_std
        self.name = f"BB({period}, {num_std}σ)"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = df['close']
        sma = close.rolling(self.period).mean()
        std = close.rolling(self.period).std()
        upper = sma + self.num_std * std
        lower = sma - self.num_std * std

        signal = pd.Series(0, index=df.index, dtype=int)

        # 向量化：用 numpy where 嵌套
        signal = pd.Series(
            np.where(
                close < lower, 1,           # 觸及下軌 → 做多
                np.where(close > upper, -1,  # 觸及上軌 → 做空
                         0)                  # 在通道內 → 空倉
            ),
            index=df.index,
        )

        # 持倉延續：空倉時維持上一個信號（直到反向觸發）
        signal = signal.replace(0, np.nan).ffill().fillna(0).astype(int)

        return signal


# ─── 策略註冊表 ─────────────────────────────────


STRATEGIES: dict[str, type[Strategy]] = {
    'buyhold': BuyAndHold,
    'sma': SMACrossover,
    'macd': MACDStrategy,
    'bollinger': BollingerBands,
}


def get_strategy(name: str, **kwargs) -> Strategy:
    """根據名稱取得策略實例。"""
    name = name.lower()
    if name not in STRATEGIES:
        available = ', '.join(STRATEGIES.keys())
        raise ValueError(f"未知策略 '{name}'。可用策略: {available}")
    return STRATEGIES[name](**kwargs)
