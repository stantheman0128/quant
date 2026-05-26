"""
跨指數策略比較 — Cross-Index Strategy Comparison
================================================
回答一個問題：「換一個指數宇宙，會不會影響策略表現？」

把同一批策略跑遍 15 個指數標的（2024 全年、1h K 線），
輸出各指數 × 各策略的 Sharpe 對照表，以及「宇宙離散度」摘要。

設計：本腳本「import」backtest_engine 當函式庫使用，不修改它
（符合 STATUS.md 禁令：不可改 backtest_engine/）。

用法：
    python cross_index_compare.py
"""

import math
import sys
import statistics
from pathlib import Path

# 確保能 import 到 backtest_engine（本檔與 backtest_engine/ 同層）
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from backtest_engine.data_loader import load_and_resample, find_data_file
from backtest_engine.engine import run_backtest
from backtest_engine.strategy import (
    BuyAndHold, SMACrossover, MACDStrategy, BollingerBands,
)

# ── 設定 ──────────────────────────────────────────
HERE = Path(__file__).resolve().parent            # 回測/
CACHE = HERE / ".ohlcv_cache"
FREQ = "1h"
YEAR = "24"

# 15 個指數標的（依地區排序）
INDICES = [
    "US500", "US100", "US30",                  # 美國：S&P500 / 那斯達克100 / 道瓊
    "DE40", "FR40", "UK100", "EU50",           # 歐洲（大）
    "ES35", "CH20", "NL25",                    # 歐洲（小）
    "JP225", "HK50", "AU200", "CN50", "SG30",  # 亞太
]

# 同一批策略，跑遍每個指數
STRATEGIES = {
    "BuyHold":     BuyAndHold(),
    "SMA(20/50)":  SMACrossover(fast=20, slow=50),
    "MACD(12/26)": MACDStrategy(fast=12, slow=26, signal_period=9),
    "BB(20,2.0)":  BollingerBands(period=20, num_std=2.0),
}


def fmt(x, width=13, plus=False):
    """安全格式化：NaN / None → 「—」"""
    try:
        x = float(x)
        if not math.isfinite(x):
            return f"{'—':>{width}}"
        return f"{x:>+{width}.2f}" if plus else f"{x:>{width}.2f}"
    except (TypeError, ValueError):
        return f"{'—':>{width}}"


def main():
    print(f"\n{'='*76}")
    print(f"  跨指數策略比較  —  2024 全年, {FREQ} K 線, 未扣手續費")
    print(f"{'='*76}\n")

    # 1. 載入 15 個指數的資料
    data = {}
    for sym in INDICES:
        try:
            path = find_data_file(HERE, sym, YEAR)
            data[sym] = load_and_resample(path, FREQ, cache_dir=CACHE)
            print(f"  loaded  {sym:<7s} {len(data[sym]):>7,} bars")
        except Exception as e:
            print(f"  [SKIP]  {sym}: {type(e).__name__}: {e}")
    if not data:
        print("\n[ERROR] 沒載入到任何資料")
        return

    # 2. 回測：每個指數 × 每個策略
    results = {}   # results[sym][strat] = metrics dict (or None)
    for sym, prices in data.items():
        results[sym] = {}
        for sname, strat in STRATEGIES.items():
            try:
                r = run_backtest(prices=prices, strategy=strat,
                                 symbol=sym, freq=FREQ, commission=0.0)
                results[sym][sname] = r.metrics
            except Exception as e:
                results[sym][sname] = None
                print(f"  [FAIL]  {sym}/{sname}: {type(e).__name__}: {e}")

    snames = list(STRATEGIES.keys())

    # ── 表 1：各指數 × 各策略 Sharpe ──────────────────
    print(f"\n{'-'*76}")
    print("  表 1  SHARPE RATIO（各指數 × 各策略）")
    print(f"{'-'*76}")
    print(f"  {'Index':<8s}" + "".join(f"{sn:>13s}" for sn in snames))
    for sym in data:
        print(f"  {sym:<8s}" +
              "".join(fmt(results[sym][sn]['sharpe_ratio']
                          if results[sym].get(sn) else None)
                      for sn in snames))

    # ── 表 2：主動策略相對 B&H 的超額 Sharpe ──────────
    active = [sn for sn in snames if sn != "BuyHold"]
    print(f"\n{'-'*76}")
    print("  表 2  超額 SHARPE（主動策略 − BuyHold；正數 = 打贏買進持有）")
    print(f"{'-'*76}")
    print(f"  {'Index':<8s}" + "".join(f"{sn:>13s}" for sn in active))
    for sym in data:
        bh = results[sym].get("BuyHold")
        cells = []
        for sn in active:
            m = results[sym].get(sn)
            if m and bh:
                cells.append(fmt(m['sharpe_ratio'] - bh['sharpe_ratio'], plus=True))
            else:
                cells.append(fmt(None))
        print(f"  {sym:<8s}" + "".join(cells))

    # ── 表 3：宇宙重不重要？同一策略 Sharpe 的跨指數離散 ──
    print(f"\n{'-'*76}")
    print("  表 3  「宇宙重不重要」— 同一策略的 Sharpe 在 15 個指數間的離散")
    print(f"{'-'*76}")
    print(f"  {'Strategy':<13s}{'min':>11s}{'median':>11s}{'max':>11s}{'spread':>11s}")
    for sn in snames:
        vals = []
        for sym in data:
            m = results[sym].get(sn)
            if m is not None:
                sr = float(m['sharpe_ratio'])
                if math.isfinite(sr):
                    vals.append(sr)
        if vals:
            lo, hi = min(vals), max(vals)
            print(f"  {sn:<13s}" + fmt(lo, 11) + fmt(statistics.median(vals), 11)
                  + fmt(hi, 11) + fmt(hi - lo, 11))

    print(f"\n{'='*76}")
    print("  spread 越大 = 換指數對這個策略影響越大 = 「宇宙」越重要。")
    print("  註：2024 全年單一窗口，非 autoresearch 的 W1/W2 嚴謹分數。")
    print(f"{'='*76}\n")


if __name__ == "__main__":
    main()
