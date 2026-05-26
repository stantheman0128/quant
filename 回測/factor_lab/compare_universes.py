"""
B6 — S&P 100 vs S&P 500 宇宙比較
=================================
回答最初的問題：哪個成分股宇宙的因子比較有效？
把 B4 的 7 個因子分別在兩個宇宙上跑，並列 IC / IC_IR。

假設（B4 得出）：宇宙越廣、因子訊號越強 -> 預期 S&P 500 > S&P 100。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cs_engine import backtest_factor, load_prices, load_universe
from factors import FACTORS

DATA = Path(__file__).resolve().parent / "data"


def run_universe(data, universe):
    out = {}
    for name, fn in FACTORS.items():
        try:
            res = backtest_factor(name, fn(data), data["close"],
                                  universe=universe, n_quantiles=5)
            out[name] = res.metrics
        except Exception as e:
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
    return out


def main():
    fields = ["close", "open", "high", "low", "volume"]
    data = {f: load_prices(DATA, f) for f in fields}
    sp100 = load_universe(DATA, "sp100")
    sp500 = load_universe(DATA, "sp500")
    print(f"S&P 100: {len(sp100)} 檔   S&P 500: {len(sp500)} 檔\n")

    r100 = run_universe(data, sp100)
    r500 = run_universe(data, sp500)

    rows = []
    for name in FACTORS:
        a, b = r100.get(name, {}), r500.get(name, {})
        rows.append({
            "factor": name,
            "IC_sp100": a.get("ic_mean", np.nan),
            "IC_sp500": b.get("ic_mean", np.nan),
            "ICIR_sp100": a.get("ic_ir", np.nan),
            "ICIR_sp500": b.get("ic_ir", np.nan),
        })
    cmp = pd.DataFrame(rows).set_index("factor")
    cmp["dIC"] = cmp["IC_sp500"] - cmp["IC_sp100"]

    print("=" * 78)
    print("  B6 — 因子 IC：S&P 100 vs S&P 500")
    print("=" * 78)
    print(f"  {'factor':<16}{'IC@100':>10}{'IC@500':>10}"
          f"{'ICIR@100':>11}{'ICIR@500':>11}{'dIC':>10}")
    print("  " + "-" * 76)
    for name, r in cmp.iterrows():
        print(f"  {name:<16}{r['IC_sp100']:>+10.4f}{r['IC_sp500']:>+10.4f}"
              f"{r['ICIR_sp100']:>+11.3f}{r['ICIR_sp500']:>+11.3f}"
              f"{r['dIC']:>+10.4f}")
    print("  " + "-" * 76)

    m100, m500 = cmp["IC_sp100"].abs().mean(), cmp["IC_sp500"].abs().mean()
    ir100, ir500 = cmp["ICIR_sp100"].abs().mean(), cmp["ICIR_sp500"].abs().mean()
    print(f"  平均 |IC|  : S&P 100 = {m100:.4f}   S&P 500 = {m500:.4f}")
    print(f"  平均 |ICIR|: S&P 100 = {ir100:.3f}   S&P 500 = {ir500:.3f}")
    winner = "S&P 500" if m500 > m100 else "S&P 100"
    note = "廣度有幫助、與假設一致" if m500 > m100 else "廣度沒幫助、與假設相反"
    print(f"  => {winner} 因子訊號較強（{note}）")
    print("=" * 78)

    cmp.to_csv(DATA / "b6_universe_compare.csv")
    print(f"  存到 {DATA / 'b6_universe_compare.csv'}\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
