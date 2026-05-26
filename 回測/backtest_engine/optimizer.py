"""
策略優化器 — Grid Search + Monte Carlo Validation

1. 對所有 (標的 × 年份 × 頻率 × 策略 × 參數) 組合跑回測
2. 按 Sharpe / Sortino / 綜合分數排名
3. 對 Top N 做 Monte Carlo 驗證（shuffle returns）
"""

import itertools
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .data_loader import load_and_resample, list_available_symbols, find_data_file
from .engine import run_backtest
from .strategy import (
    Strategy,
    BuyAndHold,
    SMACrossover,
    MACDStrategy,
    BollingerBands,
)
from .metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    annualized_return,
)


# ─── Parameter Grids ──────────────────────────

def default_param_grid() -> dict[str, list[dict]]:
    """
    每個策略的預設參數搜索空間。
    回傳 {strategy_key: [param_dict, ...]}
    """
    sma_combos = [
        {'fast': f, 'slow': s}
        for f in [5, 10, 20, 30, 50]
        for s in [20, 50, 100, 150, 200]
        if f < s
    ]

    macd_combos = [
        {'fast': f, 'slow': s, 'signal_period': g}
        for f in [8, 12, 16]
        for s in [20, 26, 34]
        for g in [5, 9, 13]
        if f < s
    ]

    bb_combos = [
        {'period': p, 'num_std': std}
        for p in [10, 20, 30, 50]
        for std in [1.5, 2.0, 2.5, 3.0]
    ]

    return {
        'buyhold': [{}],
        'sma': sma_combos,
        'macd': macd_combos,
        'bollinger': bb_combos,
    }


def _make_strategy(name: str, params: dict) -> Strategy:
    """根據名稱和參數建立策略實例。"""
    factories = {
        'buyhold': lambda p: BuyAndHold(),
        'sma': lambda p: SMACrossover(**p),
        'macd': lambda p: MACDStrategy(**p),
        'bollinger': lambda p: BollingerBands(**p),
    }
    return factories[name](params)


# ─── Grid Search ──────────────────────────────

@dataclass
class SearchResult:
    symbol: str
    year: str
    freq: str
    strategy_name: str
    params: dict
    sharpe: float
    sortino: float
    annual_return: float
    max_drawdown: float
    calmar: float
    win_rate: float
    profit_factor: float
    total_trades: int
    score: float = 0.0  # 綜合分數


def run_grid_search(
    data_dir: str | Path,
    symbols: list[str] | None = None,
    years: list[str] | None = None,
    freqs: list[str] | None = None,
    strategies: list[str] | None = None,
    param_grid: dict | None = None,
    commission: float = 0.0,
    cache_dir: Path | None = None,
    progress_callback=None,
) -> list[SearchResult]:
    """
    全組合 grid search。

    Parameters
    ----------
    data_dir : 數據根目錄
    symbols  : 要測試的標的 (None = 全部)
    years    : 要測試的年份 (None = 全部)
    freqs    : 要測試的頻率 (預設 ['1h'])
    strategies : 要測試的策略 (None = 全部)
    param_grid : 參數搜索空間 (None = 用預設)
    commission : 交易成本
    cache_dir  : OHLCV 快取目錄
    progress_callback : fn(current, total, msg) 進度回呼

    Returns
    -------
    list[SearchResult] 按綜合分數排序
    """
    data_dir = Path(data_dir)
    if cache_dir is None:
        cache_dir = data_dir / '.ohlcv_cache'

    available = list_available_symbols(data_dir)

    if symbols is None:
        symbols = sorted(available.keys())
    if years is None:
        years = sorted(set(y for yrs in available.values() for y in yrs))
    if freqs is None:
        freqs = ['1h']
    if strategies is None:
        strategies = ['buyhold', 'sma', 'macd', 'bollinger']
    if param_grid is None:
        param_grid = default_param_grid()

    # 計算總任務數
    total_combos = 0
    for sym in symbols:
        sym_years = [y for y in years if y in available.get(sym, [])]
        for _ in sym_years:
            for _ in freqs:
                for strat in strategies:
                    total_combos += len(param_grid.get(strat, [{}]))

    results: list[SearchResult] = []
    done = 0
    t_start = time.perf_counter()

    # 按 (symbol, year, freq) 分組 — 每組只載入一次數據
    for sym in symbols:
        sym_years = [y for y in years if y in available.get(sym, [])]
        for yr in sym_years:
            for freq in freqs:
                # 載入數據（一次）
                try:
                    path = find_data_file(data_dir, sym, yr)
                    prices = load_and_resample(path, freq, cache_dir=cache_dir)
                except Exception:
                    # 跳過壞數據
                    for strat in strategies:
                        done += len(param_grid.get(strat, [{}]))
                    continue

                if len(prices) < 50:
                    for strat in strategies:
                        done += len(param_grid.get(strat, [{}]))
                    continue

                # 對這組數據跑所有策略組合
                for strat_name in strategies:
                    for params in param_grid.get(strat_name, [{}]):
                        done += 1
                        try:
                            strategy = _make_strategy(strat_name, params)
                            bt = run_backtest(
                                prices=prices,
                                strategy=strategy,
                                symbol=sym,
                                freq=freq,
                                commission=commission,
                            )
                            m = bt.metrics

                            results.append(SearchResult(
                                symbol=sym,
                                year=yr,
                                freq=freq,
                                strategy_name=str(strategy),
                                params=params,
                                sharpe=m['sharpe_ratio'],
                                sortino=m['sortino_ratio'],
                                annual_return=m['annualized_return'],
                                max_drawdown=m['max_drawdown'],
                                calmar=m['calmar_ratio'],
                                win_rate=m['win_rate'],
                                profit_factor=m['profit_factor'],
                                total_trades=int(m.get('total_trades', 0)),
                            ))
                        except Exception:
                            pass

                        if progress_callback and done % 50 == 0:
                            elapsed = time.perf_counter() - t_start
                            rate = done / elapsed if elapsed > 0 else 0
                            eta = (total_combos - done) / rate if rate > 0 else 0
                            progress_callback(
                                done, total_combos,
                                f"{sym} 20{yr} {freq} | {done}/{total_combos} | "
                                f"{rate:.0f}/s | ETA {eta:.0f}s"
                            )

    # 計算綜合分數
    _compute_scores(results)

    # 排序
    results.sort(key=lambda r: r.score, reverse=True)

    return results


def _compute_scores(results: list[SearchResult]) -> None:
    """
    綜合分數 = 加權 Z-score 排名

    權重: Sharpe 0.35, Sortino 0.25, Calmar 0.20, Profit Factor 0.10, Win Rate 0.10
    """
    if not results:
        return

    metrics = {
        'sharpe':        (0.35, [r.sharpe for r in results]),
        'sortino':       (0.25, [r.sortino for r in results]),
        'calmar':        (0.20, [r.calmar for r in results]),
        'profit_factor': (0.10, [r.profit_factor for r in results]),
        'win_rate':      (0.10, [r.win_rate for r in results]),
    }

    # Clip extreme values
    for key, (w, vals) in metrics.items():
        arr = np.array(vals, dtype=float)
        arr = np.clip(arr, -10, 10)
        metrics[key] = (w, arr)

    # Z-score normalize
    z_scores = {}
    for key, (w, arr) in metrics.items():
        mean = np.mean(arr)
        std = np.std(arr)
        if std > 0:
            z_scores[key] = (w, (arr - mean) / std)
        else:
            z_scores[key] = (w, np.zeros_like(arr))

    # 加權合成
    for i, r in enumerate(results):
        r.score = sum(w * z[i] for w, z in z_scores.values())


# ─── Monte Carlo Validation ──────────────────

@dataclass
class MonteCarloResult:
    original_sharpe: float
    simulated_sharpes: list[float]
    percentile: float        # 原始 Sharpe 在模擬分佈中的百分位
    p_value: float           # 統計顯著性
    is_significant: bool     # p < 0.05


def monte_carlo_validate(
    prices: pd.DataFrame,
    strategy: Strategy,
    freq: str = '1h',
    commission: float = 0.0,
    n_simulations: int = 1000,
) -> MonteCarloResult:
    """
    Monte Carlo 驗證：shuffle 報酬序列 N 次，看原始策略是否顯著優於隨機。

    方法: 保持信號不變，shuffle 價格報酬的時間順序，重新計算 Sharpe。
    如果原始 Sharpe > 95% 的 shuffled 版本，策略是統計顯著的。
    """
    from .engine import _estimate_periods_per_year

    # 原始回測
    signals = strategy.generate_signals(prices)
    price_returns = prices['close'].pct_change().fillna(0).values
    shifted_signals = signals.shift(1).fillna(0).values

    # 原始 Sharpe
    orig_strat_returns = shifted_signals * price_returns
    periods_per_year = _estimate_periods_per_year(freq)
    orig_sharpe = sharpe_ratio(orig_strat_returns, periods_per_year=periods_per_year)

    # Monte Carlo: shuffle price returns, keep signals fixed
    rng = np.random.default_rng(42)
    sim_sharpes = []

    for _ in range(n_simulations):
        shuffled_returns = rng.permutation(price_returns)
        sim_strat_returns = shifted_signals * shuffled_returns
        sim_sharpe = sharpe_ratio(sim_strat_returns, periods_per_year=periods_per_year)
        sim_sharpes.append(sim_sharpe)

    sim_sharpes_arr = np.array(sim_sharpes)
    percentile = float(np.mean(sim_sharpes_arr < orig_sharpe) * 100)
    p_value = 1.0 - percentile / 100

    return MonteCarloResult(
        original_sharpe=orig_sharpe,
        simulated_sharpes=sim_sharpes,
        percentile=percentile,
        p_value=p_value,
        is_significant=p_value < 0.05,
    )


# ─── Output Formatting ───────────────────────

def results_to_dataframe(results: list[SearchResult]) -> pd.DataFrame:
    """轉成 DataFrame 方便查看/輸出。"""
    rows = []
    for r in results:
        rows.append({
            'Rank': 0,  # 填後面
            'Symbol': r.symbol,
            'Year': f"20{r.year}",
            'Freq': r.freq,
            'Strategy': r.strategy_name,
            'Sharpe': r.sharpe,
            'Sortino': r.sortino,
            'AR': r.annual_return,
            'MDD': r.max_drawdown,
            'Calmar': r.calmar,
            'WinRate': r.win_rate,
            'PF': r.profit_factor,
            'Trades': r.total_trades,
            'Score': r.score,
        })
    df = pd.DataFrame(rows)
    if len(df) > 0:
        df['Rank'] = range(1, len(df) + 1)
    return df
