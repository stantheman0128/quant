"""
CLI 入口 — python -m backtest_engine.cli

用法:
  python -m backtest_engine.cli --symbol XAUUSD --year 24 --freq 1H --strategy macd
  python -m backtest_engine.cli --symbol XAUUSD --year 24 --freq 1H --strategy macd --visual
  python -m backtest_engine.cli --list              # 列出所有可用標的
"""

import argparse
import sys
import time
from pathlib import Path

from .data_loader import load_and_resample, list_available_symbols, find_data_file
from .engine import run_backtest
from .metrics import format_metrics
from .strategy import get_strategy, STRATEGIES


def _resolve_data_dir() -> Path:
    """找到數據目錄（回測/ 的上一層或本層）"""
    # CLI 可能從不同位置執行，嘗試幾個可能的路徑
    candidates = [
        Path(__file__).parent.parent,           # backtest_engine 的上一層 = 回測/
        Path.cwd(),
        Path.cwd() / '回測',
    ]
    for d in candidates:
        if (d / '1y_24').exists() or (d / '1y_25').exists():
            return d
    raise FileNotFoundError("找不到數據目錄（1y_24 / 1y_25）。請從回測/目錄執行。")


def cmd_list(data_dir: Path) -> None:
    """列出所有可用標的"""
    symbols = list_available_symbols(data_dir)
    if not symbols:
        print("找不到任何數據檔案。")
        return

    print(f"\n可用標的 ({len(symbols)} 個):")
    print("─" * 40)

    # 分類顯示
    categories = {
        'FX Major': ['EURUSD', 'USDJPY', 'GBPUSD', 'AUDUSD', 'USDCHF', 'USDCAD', 'NZDUSD'],
        'Commodities': ['XAUUSD', 'XAGUSD', 'USOIL', 'UKOIL', 'NATGAS'],
        'Indices': ['US500', 'US100', 'US30', 'DE40', 'JP225', 'HK50', 'CN50', 'UK100',
                    'AU200', 'FR40', 'EU50', 'ES35', 'NL25', 'CH20', 'SG30'],
    }

    categorized = set()
    for cat, syms in categories.items():
        found = [s for s in syms if s in symbols]
        if found:
            print(f"\n  {cat}:")
            for s in found:
                years = ', '.join(f"20{y}" for y in symbols[s])
                print(f"    {s:<12s} [{years}]")
                categorized.add(s)

    # 剩餘未分類的
    others = [s for s in sorted(symbols) if s not in categorized]
    if others:
        print(f"\n  FX Cross / Other:")
        for s in others:
            years = ', '.join(f"20{y}" for y in symbols[s])
            print(f"    {s:<12s} [{years}]")

    print()


def cmd_run(args: argparse.Namespace, data_dir: Path) -> None:
    """執行回測"""
    # 載入數據
    t0 = time.perf_counter()
    print(f"\n載入 {args.symbol} 20{args.year} tick 數據...")
    csv_path = find_data_file(data_dir, args.symbol, args.year)
    prices = load_and_resample(csv_path, freq=args.freq)
    t_load = time.perf_counter() - t0
    print(f"  → {len(prices)} bars ({args.freq})，載入耗時 {t_load:.1f}s")

    # 建立策略
    strategy = get_strategy(args.strategy)
    print(f"策略: {strategy}")

    # 執行回測
    t1 = time.perf_counter()
    result = run_backtest(
        prices=prices,
        strategy=strategy,
        symbol=args.symbol,
        freq=args.freq,
        commission=args.commission,
    )
    t_bt = time.perf_counter() - t1

    # 輸出結果
    header = f" {args.symbol} | {strategy} | {args.freq} | 20{args.year} "
    border = "═" * max(len(header) + 2, 38)
    print(f"\n{border}")
    print(f" {header}")
    print(f"{border}")
    print(format_metrics(result.metrics))
    print(f"  {'Total Trades':<22s} {result.metrics.get('total_trades', 0):>10.0f}")
    print(f"{border}")
    print(f"  回測耗時: {t_bt*1000:.0f}ms | 總耗時: {(t_load + t_bt):.1f}s")
    print()

    # 視覺化
    if args.visual:
        from .visualizer import generate_report
        output_path = data_dir / f"report_{args.symbol}_{args.year}_{args.strategy}.html"
        generate_report(result, output_path)
        print(f"圖表已輸出: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="向量化回測引擎",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--list', action='store_true', help='列出所有可用標的')
    parser.add_argument('--symbol', '-s', type=str, help='標的代碼 (如 XAUUSD)')
    parser.add_argument('--year', '-y', type=str, help='年份 (24 或 25)')
    parser.add_argument('--freq', '-f', type=str, default='1h',
                        help='K 線頻率 (1min/5min/15min/1h/4h/1D，預設 1h)')
    parser.add_argument('--strategy', '-t', type=str, default='buyhold',
                        help=f"策略名稱 ({', '.join(STRATEGIES.keys())}，預設 buyhold)")
    parser.add_argument('--commission', '-c', type=float, default=0.0,
                        help='交易成本比例 (預設 0，如 0.0001 = 1bp)')
    parser.add_argument('--visual', '-v', action='store_true', help='輸出互動式圖表')

    args = parser.parse_args()

    data_dir = _resolve_data_dir()

    if args.list:
        cmd_list(data_dir)
        return

    if not args.symbol or not args.year:
        parser.print_help()
        print("\n錯誤: 請指定 --symbol 和 --year（或用 --list 查看可用標的）")
        sys.exit(1)

    args.symbol = args.symbol.upper()

    cmd_run(args, data_dir)


if __name__ == '__main__':
    main()
