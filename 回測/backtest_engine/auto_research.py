"""
Auto Research — 自動策略搜索器

在 2024 年訓練集上：
1. Grid search 所有策略 × 參數組合
2. 每組參數在全部標的上跑回測
3. 計算跨標的穩健性分數
4. 輸出 Top N 候選策略

然後可以把 Top 候選拿去 BlackBoxValidator 驗證 2025 年表現。

用法:
  cd 回測/
  python -m backtest_engine.auto_research
  python -m backtest_engine.auto_research --top 5 --validate
"""

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .data_loader import load_and_resample, list_available_symbols, find_data_file
from .engine import run_backtest
from .strategy import BuyAndHold, SMACrossover, MACDStrategy, BollingerBands, Strategy
from .scorer import RobustnessScore, compute_robustness
from .black_box import BlackBoxValidator


# ─── Parameter Space ──────────────────────────

PARAM_SPACE = {
    'buyhold': [{}],

    'sma': [
        {'fast': f, 'slow': s}
        for f in [5, 8, 10, 15, 20, 30, 50]
        for s in [20, 30, 50, 80, 100, 150, 200]
        if f < s
    ],

    'macd': [
        {'fast': f, 'slow': s, 'signal_period': g}
        for f in [6, 8, 10, 12, 16, 20]
        for s in [16, 20, 26, 30, 40]
        for g in [5, 7, 9, 12, 15]
        if f < s
    ],

    'bollinger': [
        {'period': p, 'num_std': std}
        for p in [10, 15, 20, 30, 40, 50, 80]
        for std in [1.0, 1.5, 2.0, 2.5, 3.0]
    ],
}

STRATEGY_FACTORIES = {
    'buyhold': lambda p: BuyAndHold(),
    'sma': lambda p: SMACrossover(**p),
    'macd': lambda p: MACDStrategy(**p),
    'bollinger': lambda p: BollingerBands(**p),
}

# 計算總數
TOTAL_CONFIGS = sum(len(v) for v in PARAM_SPACE.values())


@dataclass
class Candidate:
    rank: int
    strategy_name: str
    display_name: str
    params: dict
    score: RobustnessScore


def run_auto_research(
    data_dir: str | Path,
    train_year: str = '24',
    freq: str = '1h',
    commission: float = 0.0,
    top_n: int = 20,
) -> list[Candidate]:
    """
    在訓練集上搜索最穩健的策略。

    回傳 top_n 個候選策略，按 composite score 排序。
    """
    data_dir = Path(data_dir)
    cache_dir = data_dir / '.ohlcv_cache'

    available = list_available_symbols(data_dir)
    symbols = [sym for sym, years in available.items() if train_year in years]

    print(f"\n{'═'*60}")
    print(f" AUTO RESEARCH")
    print(f" Train: 20{train_year} | Freq: {freq} | Symbols: {len(symbols)}")
    print(f" Strategy configs: {TOTAL_CONFIGS}")
    print(f" Total backtests: {TOTAL_CONFIGS * len(symbols):,}")
    print(f"{'═'*60}\n")

    # 預載所有 2024 數據
    print("預載數據...")
    data_cache: dict[str, pd.DataFrame] = {}
    for i, sym in enumerate(symbols):
        try:
            path = find_data_file(data_dir, sym, train_year)
            prices = load_and_resample(path, freq, cache_dir=cache_dir)
            if len(prices) >= 50:
                data_cache[sym] = prices
        except Exception:
            pass
        if (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(symbols)}] loaded")

    active_symbols = list(data_cache.keys())
    print(f"  有效標的: {len(active_symbols)}\n")

    # Grid search
    candidates: list[Candidate] = []
    config_done = 0
    t_start = time.perf_counter()

    for strat_name, param_list in PARAM_SPACE.items():
        for params in param_list:
            config_done += 1

            try:
                strategy = STRATEGY_FACTORIES[strat_name](params)
            except Exception:
                continue

            display = str(strategy)
            sharpes, sortinos, ars, mdds = [], [], [], []

            for sym, prices in data_cache.items():
                try:
                    result = run_backtest(
                        prices=prices,
                        strategy=strategy,
                        symbol=sym,
                        freq=freq,
                        commission=commission,
                    )
                    m = result.metrics
                    sharpes.append(m['sharpe_ratio'])
                    sortinos.append(m['sortino_ratio'])
                    ars.append(m['annualized_return'])
                    mdds.append(m['max_drawdown'])
                except Exception:
                    pass

            if len(sharpes) < 10:
                continue

            score = compute_robustness(sharpes, sortinos, ars, mdds)

            candidates.append(Candidate(
                rank=0,
                strategy_name=strat_name,
                display_name=display,
                params=params,
                score=score,
            ))

            # 進度
            if config_done % 25 == 0:
                elapsed = time.perf_counter() - t_start
                rate = config_done / elapsed
                eta = (TOTAL_CONFIGS - config_done) / rate
                print(
                    f"  [{config_done:>4}/{TOTAL_CONFIGS}] "
                    f"{display:<24s} "
                    f"med_sharpe={score.median_sharpe:+.3f}  "
                    f"%pos={score.pct_positive:.0%}  "
                    f"composite={score.composite:+.3f}  "
                    f"({rate:.0f} cfg/s, ETA {eta:.0f}s)"
                )

    # 排序
    candidates.sort(key=lambda c: c.score.composite, reverse=True)
    for i, c in enumerate(candidates):
        c.rank = i + 1

    elapsed = time.perf_counter() - t_start

    # 輸出結果
    print(f"\n{'═'*80}")
    print(f" SEARCH COMPLETE — {config_done} configs × {len(active_symbols)} symbols "
          f"= {config_done * len(active_symbols):,} backtests in {elapsed:.1f}s")
    print(f"{'═'*80}\n")

    top = candidates[:top_n]
    _print_leaderboard(top)

    return top


def _print_leaderboard(candidates: list[Candidate]) -> None:
    header = (
        f" {'#':>3}  {'Strategy':<26s}  "
        f"{'MedSharpe':>9}  {'%Pos':>5}  {'W10pctl':>7}  "
        f"{'StdDev':>6}  {'MedAR':>7}  {'MedMDD':>7}  {'Score':>7}"
    )
    sep = '─' * len(header)
    print(f" TOP {len(candidates)} STRATEGIES (by Composite Score)")
    print(sep)
    print(header)
    print(sep)

    for c in candidates:
        s = c.score
        print(
            f" {c.rank:>3}  {c.display_name:<26s}  "
            f"{s.median_sharpe:>+9.3f}  {s.pct_positive:>5.0%}  {s.worst_10pctl:>+7.3f}  "
            f"{s.sharpe_std:>6.2f}  {s.median_ar:>+7.2%}  {s.median_mdd:>+7.2%}  "
            f"{s.composite:>+7.3f}"
        )

    print(sep)
    print()


def validate_top_candidates(
    candidates: list[Candidate],
    data_dir: str | Path,
    n: int = 5,
    freq: str = '1h',
    commission: float = 0.0,
) -> None:
    """把 Top N 候選自動提交到 Black Box Validator。"""
    data_dir = Path(data_dir)
    validator = BlackBoxValidator(
        data_dir=data_dir,
        test_year='25',
        freq=freq,
        commission=commission,
    )

    print(f"\n{'═'*60}")
    print(f" VALIDATING TOP {n} ON 2025 (BLACK BOX)")
    print(f"{'═'*60}\n")

    results = []
    for c in candidates[:n]:
        print(f"── #{c.rank} {c.display_name} ──")
        score = validator.submit(c.strategy_name, c.params)
        if score:
            results.append((c, score))

    # 比較表
    if results:
        print(f"\n{'═'*80}")
        print(f" TRAIN (2024) vs TEST (2025) COMPARISON")
        print(f"{'═'*80}")
        print(f" {'Strategy':<26s}  {'2024 Sharpe':>11}  {'2025 Sharpe':>11}  "
              f"{'2024 Score':>10}  {'2025 Score':>10}  {'Δ':>6}")
        print(f" {'─'*26}  {'─'*11}  {'─'*11}  {'─'*10}  {'─'*10}  {'─'*6}")

        for c, oos_score in results:
            delta = oos_score.composite - c.score.composite
            print(
                f" {c.display_name:<26s}  "
                f"{c.score.median_sharpe:>+11.3f}  "
                f"{oos_score.median_sharpe:>+11.3f}  "
                f"{c.score.composite:>+10.3f}  "
                f"{oos_score.composite:>+10.3f}  "
                f"{delta:>+6.3f}"
            )

        print(f"{'═'*80}")
        print()
        print("  D < 0: 2025 worse than 2024 (normal decay)")
        print("  D ~ 0: robust, cross-year consistent")
        print("  D > 0: 2025 better (rare but possible)")
        print()

    # 輸出 leaderboard
    print(validator.leaderboard())


# ─── CLI ──────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Auto Research — 自動策略搜索")
    parser.add_argument('--freq', '-f', default='1h', help='K 線頻率 (預設 1h)')
    parser.add_argument('--commission', '-c', type=float, default=0.0, help='交易成本 (bp)')
    parser.add_argument('--top', '-n', type=int, default=20, help='顯示 Top N (預設 20)')
    parser.add_argument('--validate', '-v', action='store_true', help='自動驗證 Top 5 到 2025')
    args = parser.parse_args()

    data_dir = Path(__file__).parent.parent

    candidates = run_auto_research(
        data_dir=data_dir,
        train_year='24',
        freq=args.freq,
        commission=args.commission / 10000 if args.commission > 0.01 else args.commission,
        top_n=args.top,
    )

    if args.validate and candidates:
        validate_top_candidates(
            candidates,
            data_dir=data_dir,
            n=5,
            freq=args.freq,
        )

    # 儲存結果
    output = data_dir / 'research_results.txt'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(f"Auto Research Results\n")
        f.write(f"Train: 2024 | Freq: {args.freq}\n\n")
        for c in candidates[:args.top]:
            s = c.score
            f.write(
                f"#{c.rank} {c.display_name}\n"
                f"  Params: {c.params}\n"
                f"  Median Sharpe: {s.median_sharpe:+.3f} | "
                f"%Pos: {s.pct_positive:.0%} | "
                f"Composite: {s.composite:+.3f}\n\n"
            )
    print(f"結果已存到: {output}")


if __name__ == '__main__':
    main()
