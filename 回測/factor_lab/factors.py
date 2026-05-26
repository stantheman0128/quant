"""
B4 — 初始因子組（Alpha101 風格）
================================
每個因子函式吃一個 data dict（close/open/high/low/volume 寬表），
回傳一張 date x ticker 的因子值寬表。

符號約定：因子值「越大」= 預期報酬「越高」（配合引擎做多最高分位）。
若某因子 IC 為負，代表方向相反 —— 取負號即可。B4 回測會用 IC 說真相。

所有因子只用「第 t 天（含）以前」的資料 —— 無 look-ahead。
"""

import numpy as np
import pandas as pd  # noqa: F401  (因子庫慣例 import，未來擴充會用到)


def mom_12_1(d):
    """12-1 月動能：一年前到一個月前的報酬。動能延續效應。"""
    c = d["close"]
    return c.shift(21) / c.shift(252) - 1


def reversal_1m(d):
    """短期反轉：過去一個月報酬的負號。買近期輸家。"""
    c = d["close"]
    return -(c / c.shift(21) - 1)


def low_vol(d):
    """低波動異常：過去 126 日報酬波動的負號。低波動股風險調整後較佳。"""
    ret = d["close"].pct_change(fill_method=None)
    return -ret.rolling(126).std()


def high_52w(d):
    """52 週高點接近度：收盤 / 過去 252 日最高。越接近年高越強（George & Hwang）。"""
    c = d["close"]
    return c / c.rolling(252).max()


def mom_vol_adj(d):
    """風險調整動能：12-1 動能 / 波動。每單位風險的動能。"""
    c = d["close"]
    mom = c.shift(21) / c.shift(252) - 1
    vol = c.pct_change(fill_method=None).rolling(126).std()
    return mom / vol.replace(0, np.nan)


def amihud_illiq(d):
    """Amihud 非流動性：平均 |報酬| / 成交額。非流動性溢酬 —— 越不流動預期報酬越高。"""
    ret = d["close"].pct_change(fill_method=None).abs()
    dollar_vol = (d["close"] * d["volume"]).replace(0, np.nan)
    return (ret / dollar_vol).rolling(63).mean()


def alpha101_101(d):
    """Alpha#101（Kakushadze 2016）：(close-open)/(high-low)。當日多空力道。"""
    rng = (d["high"] - d["low"]).replace(0, np.nan)
    return (d["close"] - d["open"]) / rng


FACTORS = {
    "mom_12_1": mom_12_1,
    "reversal_1m": reversal_1m,
    "low_vol": low_vol,
    "high_52w": high_52w,
    "mom_vol_adj": mom_vol_adj,
    "amihud_illiq": amihud_illiq,
    "alpha101_101": alpha101_101,
}
