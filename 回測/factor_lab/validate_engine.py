"""
B3 — 驗證橫斷面回測引擎
========================
用三個因子壓測 cs_engine，確認它「對」：

  1. 隨機因子    -> 應該 IC≈0、多空 Sharpe≈0      （不會無中生有）
  2. 動能因子    -> 12-1 月動能，看實際表現         （真實因子基準）
  3. Oracle 因子 -> 因子 = 明天的報酬本身           （正確性的關鍵測試）

Oracle 測試是重點：如果引擎的 look-ahead 對齊正確，「明天報酬」這個
因子必然 IC≈1.0、Sharpe 天文數字。如果對齊錯了，oracle 不會滿分。
隨機因子夾下界、oracle 夾上界 —— 兩者同時成立才算通過。
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cs_engine import backtest_factor, load_prices, load_universe

DATA = Path(__file__).resolve().parent / "data"


def main():
    close = load_prices(DATA, "close")
    sp100 = load_universe(DATA, "sp100")
    print(f"資料：{close.shape[0]} 天 x {close.shape[1]} 檔；"
          f"宇宙 = S&P 100（{len(sp100)} 檔）\n")

    # ── 三個測試因子 ──────────────────────────────
    np.random.seed(42)
    f_random = pd.DataFrame(np.random.randn(*close.shape),
                            index=close.index, columns=close.columns)
    f_mom = close.shift(21) / close.shift(252) - 1          # 12-1 月動能
    f_oracle = close.pct_change(fill_method=None).shift(-1)   # 明天的報酬（作弊）

    factors = {
        "隨機因子 (random)": f_random,
        "動能因子 (12-1 momentum)": f_mom,
        "Oracle 因子 (明天報酬, 作弊)": f_oracle,
    }

    results = {}
    for name, fac in factors.items():
        res = backtest_factor(name, fac, close, universe=sp100, n_quantiles=5)
        results[name] = res
        print("-" * 64)
        print(res.summary())
    print("-" * 64)

    # ── 驗證判定 ──────────────────────────────────
    rnd = results["隨機因子 (random)"].metrics
    orc = results["Oracle 因子 (明天報酬, 作弊)"].metrics

    rnd_flat = abs(rnd["ic_mean"]) < 0.03 and abs(rnd["ls_sharpe"]) < 1.0
    orc_huge = orc["ic_mean"] > 0.95 and orc["ls_sharpe"] > 10

    print(f"\n{'='*64}")
    print("  引擎驗證")
    print(f"{'='*64}")
    print(f"  下界（隨機因子應接近 0）: IC={rnd['ic_mean']:+.4f}, "
          f"Sharpe={rnd['ls_sharpe']:+.2f}  -> {'OK' if rnd_flat else '異常'}")
    print(f"  上界（Oracle 應接近滿分）: IC={orc['ic_mean']:+.4f}, "
          f"Sharpe={orc['ls_sharpe']:+.1f}  -> {'OK' if orc_huge else '異常'}")
    verdict = ("通過 — 引擎對齊正確、能正確分辨有無預測力"
               if (rnd_flat and orc_huge)
               else "未通過 — 引擎有問題，需檢查")
    print(f"\n  判定：{verdict}")
    print(f"{'='*64}\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
