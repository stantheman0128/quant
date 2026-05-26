"""
sources/price.py — 統一股價查詢介面 (台股 FinMind / 美股 yfinance)

對齊 banini-tracker 的 price_snapshots schema：
  prediction_id, day_number (1-5), date, open/high/low/close, change_pct_*

設計：
  - get_t5_ohlc(symbol, market, base_date) → list[dict] (5 個交易日)
  - 自動 cache 已查過的 (symbol, date) 避免重複請求
"""
from __future__ import annotations

import json
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache" / "price"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

Market = Literal["TW", "US"]


def _cache_key(symbol: str, market: Market, base_date: date) -> Path:
    return CACHE_DIR / f"{market}_{symbol}_{base_date.isoformat()}.json"


def _load_cache(symbol: str, market: Market, base_date: date) -> list[dict] | None:
    p = _cache_key(symbol, market, base_date)
    if p.exists():
        return json.loads(p.read_text())
    return None


def _save_cache(symbol: str, market: Market, base_date: date, data: list[dict]) -> None:
    _cache_key(symbol, market, base_date).write_text(json.dumps(data, default=str))


# ============================================================================
#  TW stocks via FinMind
# ============================================================================

def _fetch_tw(symbol: str, base_date: date) -> list[dict]:
    """FinMind TaiwanStockPrice: 抓 base_date 起 + 14 日（保險），取前 5 個有資料的交易日"""
    token = os.environ.get("FINMIND_TOKEN", "")
    end_date = base_date + timedelta(days=14)
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": symbol,
        "start_date": base_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    if token:
        params["token"] = token
    r = requests.get("https://api.finmindtrade.com/api/v4/data", params=params, timeout=30)
    r.raise_for_status()
    raw = r.json().get("data", [])
    # FinMind 用 'date' / 'open' / 'max' / 'min' / 'close' 欄位
    bars = []
    for b in raw:
        if b["date"] <= base_date.isoformat():
            continue
        bars.append({
            "date": b["date"],
            "open": float(b["open"]),
            "high": float(b["max"]),
            "low": float(b["min"]),
            "close": float(b["close"]),
        })
        if len(bars) >= 5:
            break
    return bars


# ============================================================================
#  US stocks via yfinance
# ============================================================================

def _fetch_us(symbol: str, base_date: date) -> list[dict]:
    import yfinance as yf
    end_date = base_date + timedelta(days=14)
    tk = yf.Ticker(symbol)
    hist = tk.history(start=base_date.isoformat(), end=end_date.isoformat(), auto_adjust=False)
    if hist.empty:
        return []
    bars = []
    for idx, row in hist.iterrows():
        d = idx.date() if hasattr(idx, "date") else idx
        if d <= base_date:
            continue
        bars.append({
            "date": d.isoformat(),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        })
        if len(bars) >= 5:
            break
    return bars


# ============================================================================
#  Public API
# ============================================================================

def get_base_price(symbol: str, market: Market, base_date: date) -> float | None:
    """取 base_date 當天（或最近一個交易日）的收盤價作為 base_price。"""
    bars = _get_with_base(symbol, market, base_date)
    return bars[0]["close"] if bars else None


def _get_with_base(symbol: str, market: Market, base_date: date) -> list[dict]:
    """取 base 那天 + T+1..5。bar[0] = base 當天, bar[1..5] = T+1..T+5。"""
    cached = _load_cache(symbol, market, base_date)
    if cached is not None:
        return cached
    fetcher = _fetch_tw if market == "TW" else _fetch_us
    # 也抓 base 當天，所以從 base_date - 5 開始（FinMind/yfinance 會自動處理）
    try:
        bars_after = fetcher(symbol, base_date)
        # 抓 base 當天
        bars_base = fetcher(symbol, base_date - timedelta(days=7))
        base_bar = next((b for b in bars_base if b["date"] <= base_date.isoformat()), None)
        # 取 base date 前最近一個交易日當作 day0
        # 簡化：直接用 base_date 前 7 天內最後一個交易日
        bars_base_sorted = sorted([b for b in bars_base if b["date"] <= base_date.isoformat()],
                                  key=lambda x: x["date"])
        if not bars_base_sorted:
            return []
        result = [bars_base_sorted[-1]] + bars_after
        time.sleep(0.5)  # rate limit
    except Exception as e:
        print(f"[price] {market}/{symbol} @ {base_date}: {e}")
        return []
    _save_cache(symbol, market, base_date, result)
    return result


def compute_returns(symbol: str, market: Market, base_date: date) -> dict | None:
    """便利函數：直接回傳 ret_1d..5d, max/min."""
    bars = _get_with_base(symbol, market, base_date)
    if len(bars) < 2:
        return None
    base = bars[0]["close"]
    out = {"base_price": base, "base_date": bars[0]["date"]}
    for i in range(1, min(6, len(bars))):
        out[f"ret_{i}d"] = bars[i]["close"] / base - 1
    high_5 = max(b["high"] for b in bars[1:6])
    low_5 = min(b["low"] for b in bars[1:6])
    out["max_ret_5d"] = high_5 / base - 1
    out["min_ret_5d"] = low_5 / base - 1
    return out
