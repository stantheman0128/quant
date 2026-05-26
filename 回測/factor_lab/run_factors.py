"""
B4 runner — 把初始因子組全部跑過引擎，輸出 IC 排行榜
=====================================================
依 |IC| 排序（IC 為主、Sharpe 為輔 —— 見 B3 的教訓：單一 Sharpe 太吵）。
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cs_engine import backtest_factor, load_prices, load_universe
from factors import FACTORS

DATA = Path(__file__).resolve().parent / "data"


def main():
    fields = ["close", "open", "high", "low", "volume"]
    data = {f: load_prices(DATA, f) for f in fields}
    sp100 = load_universe(DATA, "sp100")
    print(f"資料：{data['close'].shape[0]} 天；宇宙 = S&P 100（{len(sp100)} 檔）")
    print(f"因子數：{len(FACTORS)}\n")

    rows = []
    for name, fn in FACTORS.items():
        try:
            factor = fn(data)
            res = backtest_factor(name, factor, data["close"],
                                  universe=sp100, n_quantiles=5)
            m = res.metrics
            rows.append({
                "factor": name, "IC": m["ic_mean"], "IC_IR": m["ic_ir"],
                "LS_Sharpe": m["ls_sharpe"], "LS_AnnRet": m["ls_ann_return"],
                "monotonic": m["monotonic"],
            })
        except Exception as e:
            print(f"  [FAIL] {name}: {type(e).__name__}: {e}")

    if not rows:
        print("[ERROR] 沒有因子成功跑完")
        return

    lb = pd.DataFrame(rows).set_index("factor")
    lb = lb.assign(absIC=lb["IC"].abs()).sort_values("absIC", ascending=False)

    print("=" * 74)
    print("  B4 因子排行榜（依 |IC| 排序）")
    print("=" * 74)
    print(f"  {'factor':<16}{'IC':>9}{'IC_IR':>9}{'LS_Sharpe':>11}"
          f"{'LS_AnnRet':>12}{'mono':>7}")
    print("  " + "-" * 72)
    for name, r in lb.iterrows():
        print(f"  {name:<16}{r['IC']:>+9.4f}{r['IC_IR']:>+9.3f}"
              f"{r['LS_Sharpe']:>+11.2f}{r['LS_AnnRet'] * 100:>+11.1f}%"
              f"{('Y' if r['monotonic'] else '-'):>7}")
    print("=" * 74)

    out = DATA / "b4_factor_leaderboard.csv"
    lb.drop(columns="absIC").to_csv(out)
    print(f"  排行榜存到 {out}\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
