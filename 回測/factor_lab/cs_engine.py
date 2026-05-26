"""
B2 — 橫斷面因子回測引擎  Cross-Sectional Factor Backtest Engine
================================================================
吃一張因子值寬表（date x ticker），輸出這個因子的：
  - 各分位數投資組合報酬（檢查單調性）
  - 多空組合（long 最高分位 / short 最低分位）報酬與 Sharpe
  - IC（資訊係數）時間序列

防 look-ahead 的關鍵：因子在第 t 天「收盤後」算出 -> 第 t 天建倉 ->
賺到 t->t+1 的報酬。所以 factor[t] 對齊 fwd_ret[t]，
而 fwd_ret[t] = close[t+1]/close[t]-1 = prices.pct_change().shift(-1)。

獨立模組，不依賴 backtest_engine/。
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class FactorResult:
    name: str
    ls_returns: pd.Series           # 多空組合每日報酬
    quantile_returns: pd.DataFrame  # 各分位每日報酬 (date x quantile)
    ic: pd.Series                   # 每日 IC
    metrics: dict = field(default_factory=dict)

    def summary(self) -> str:
        m = self.metrics
        q_ann = self.quantile_returns.mean() * TRADING_DAYS * 100  # 年化 %
        nan = float("nan")
        return "\n".join([
            f"  因子            : {self.name}",
            f"  多空 Sharpe     : {m.get('ls_sharpe', nan):>7.2f}",
            f"  多空年化報酬    : {m.get('ls_ann_return', nan) * 100:>6.1f}%",
            f"  多空最大回撤    : {m.get('ls_max_dd', nan) * 100:>6.1f}%",
            f"  平均 IC         : {m.get('ic_mean', nan):>7.3f}",
            f"  IC IR           : {m.get('ic_ir', nan):>7.2f}",
            f"  分位年化報酬(%) : "
            + "  ".join(f"Q{i + 1}={v:+.1f}" for i, v in enumerate(q_ann)),
            f"  分位單調        : {'單調' if m.get('monotonic') else '非單調'}",
        ])


def _return_metrics(returns: pd.Series) -> dict:
    """一條報酬序列的基本指標：Sharpe / 年化報酬 / 最大回撤。"""
    r = returns.dropna()
    if len(r) < 20 or r.std() == 0:
        return {}
    cum = float((1 + r).prod())
    ann = cum ** (TRADING_DAYS / len(r)) - 1 if cum > 0 else float("nan")
    equity = (1 + r).cumprod()
    return {
        "sharpe": float(r.mean() / r.std() * np.sqrt(TRADING_DAYS)),
        "ann_return": ann,
        "max_dd": float((equity / equity.cummax() - 1).min()),
    }


def backtest_factor(name: str, factor: pd.DataFrame, prices: pd.DataFrame,
                    universe: list[str] | None = None,
                    n_quantiles: int = 5) -> FactorResult:
    """
    回測一個橫斷面因子。

    factor      : DataFrame  date x ticker，因子值（第 t 天收盤後可知）
    prices      : DataFrame  date x ticker，調整後收盤價
    universe    : 限定的 ticker 清單（None = factor 全部欄位）
    n_quantiles : 分位數（5 = 五分位）
    """
    # 1. 對齊宇宙與索引
    if universe is not None:
        cols = [c for c in universe if c in factor.columns and c in prices.columns]
    else:
        cols = list(factor.columns.intersection(prices.columns))
    factor, prices = factor[cols], prices[cols]
    idx = factor.index.intersection(prices.index)
    factor, prices = factor.loc[idx], prices.loc[idx]

    # 2. 前向報酬：fwd_ret[t] = close[t+1]/close[t]-1（防 look-ahead 的關鍵）
    fwd_ret = prices.pct_change(fill_method=None).shift(-1)

    # 3. 每天把因子值橫斷面排序成分位 bucket（0 .. n-1）
    pct = factor.rank(axis=1, pct=True)
    bucket = np.floor((pct * n_quantiles).clip(upper=n_quantiles - 1e-9))

    # 4. 每個分位每天的等權報酬
    q_df = pd.DataFrame({
        q: fwd_ret.where(bucket == q).mean(axis=1)
        for q in range(n_quantiles)
    })

    # 5. 多空組合 = 最高分位 - 最低分位
    ls = (q_df[n_quantiles - 1] - q_df[0]).dropna()

    # 6. IC = 因子與前向報酬的橫斷面 Spearman 相關（= 排名後的 Pearson）
    ic = factor.rank(axis=1).corrwith(fwd_ret.rank(axis=1), axis=1).dropna()

    # 7. 指標
    rm = _return_metrics(ls)
    q_mean = q_df.mean()
    metrics = {
        "ls_sharpe": rm.get("sharpe", float("nan")),
        "ls_ann_return": rm.get("ann_return", float("nan")),
        "ls_max_dd": rm.get("max_dd", float("nan")),
        "ic_mean": float(ic.mean()),
        "ic_ir": float(ic.mean() / ic.std()) if ic.std() else float("nan"),
        "n_days": int(len(ls)),
        "n_stocks": len(cols),
        "monotonic": bool(q_mean.is_monotonic_increasing
                          or q_mean.is_monotonic_decreasing),
    }
    return FactorResult(name=name, ls_returns=ls,
                        quantile_returns=q_df, ic=ic, metrics=metrics)


# ── B1 資料載入 helper ────────────────────────────

def load_prices(data_dir, field: str = "close") -> pd.DataFrame:
    """載入 B1 抓的價格寬表（close/open/high/low/volume）。"""
    return pd.read_parquet(Path(data_dir) / f"{field}.parquet")


def load_universe(data_dir, name: str = "sp100") -> list[str]:
    """載入 B1 存的成分股清單（sp100 / sp500）。"""
    u = json.loads((Path(data_dir) / "universes.json").read_text(encoding="utf-8"))
    return u[name]
