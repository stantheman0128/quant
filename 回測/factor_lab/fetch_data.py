"""
B1 — 抓取 S&P 100 / S&P 500 成分股日線資料
==========================================
從 Wikipedia 取得成分股清單、從 Yahoo Finance 抓日線 OHLCV，
存成「每個欄位一張 date x ticker 寬表」的 parquet —— 這是橫斷面
因子計算最順手的格式（一列一天、一欄一檔，rank 直接沿著欄做）。

輸出到 factor_lab/data/：
    close/open/high/low/volume.parquet   index=日期, columns=ticker
    universes.json                       {"sp100": [...], "sp500": [...]}

已有資料就跳過下載（加 --force 重抓）。

注意：用「當前」成分股清單 → 有存活者偏誤（survivorship bias）。
骨架驗證階段可接受；正式研究需 point-in-time 成分股，列為已知限制。
"""

import json
import sys
from io import StringIO
from pathlib import Path

import pandas as pd
import yfinance as yf

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
START = "2015-01-01"
FIELDS = ["Close", "Open", "High", "Low", "Volume"]
WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_SP100 = "https://en.wikipedia.org/wiki/S%26P_100"


def read_wiki(url):
    """讀 Wikipedia 表格；pandas 直讀失敗就用 requests + UA 重試。"""
    try:
        return pd.read_html(url)
    except Exception:
        import requests
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"},
                            timeout=30).text
        return pd.read_html(StringIO(html))


def extract_symbols(tables):
    """從表格清單中，取第一張含 Symbol/Ticker 欄的表的 ticker。"""
    for tbl in tables:
        for col in tbl.columns:
            if "Symbol" in str(col) or "Ticker" in str(col):
                return sorted(set(tbl[col].astype(str).str.strip()))
    return []


def to_yahoo(t):
    """Wikipedia ticker -> Yahoo 格式（BRK.B -> BRK-B）。"""
    return t.replace(".", "-").strip()


def main():
    force = "--force" in sys.argv
    DATA.mkdir(parents=True, exist_ok=True)

    if not force and all((DATA / f"{f.lower()}.parquet").exists() for f in FIELDS):
        close = pd.read_parquet(DATA / "close.parquet")
        print(f"[SKIP] 資料已存在：{close.shape[0]} 天 x {close.shape[1]} 檔"
              f"（--force 可重抓）")
        return

    print("[1/3] Wikipedia 取成分股清單 ...")
    sp500 = extract_symbols(read_wiki(WIKI_SP500))
    sp100 = extract_symbols(read_wiki(WIKI_SP100))
    print(f"      S&P 500: {len(sp500)} 檔   S&P 100: {len(sp100)} 檔")
    if not sp500:
        print("[ERROR] 抓不到 S&P 500 清單，中止")
        return

    universe = sorted(set(sp500) | set(sp100))
    yahoo = sorted(set(to_yahoo(t) for t in universe))
    sp100_y = sorted(set(to_yahoo(t) for t in sp100))
    print(f"      下載宇宙（聯集）：{len(yahoo)} 檔")

    print(f"[2/3] Yahoo Finance 抓日線（{START} 起，auto-adjust）...")
    raw = yf.download(yahoo, start=START, auto_adjust=True,
                      group_by="column", threads=True, progress=False)
    if raw is None or len(raw) == 0:
        print("[ERROR] yfinance 沒抓到資料")
        return

    print("[3/3] 整理成寬表並存檔 ...")
    saved = {}
    for field in FIELDS:
        if isinstance(raw.columns, pd.MultiIndex):
            if field not in raw.columns.get_level_values(0):
                print(f"      [WARN] 缺欄位 {field}")
                continue
            wide = raw[field]
        else:
            wide = raw
        wide.to_parquet(DATA / f"{field.lower()}.parquet")
        saved[field] = wide

    (DATA / "universes.json").write_text(json.dumps(
        {"sp500": sorted(set(to_yahoo(t) for t in sp500)),
         "sp100": sp100_y, "start": START}, indent=2), encoding="utf-8")

    # ── B1 完成報告 ──────────────────────────────
    close = saved.get("Close")
    print(f"\n{'='*62}")
    print("  B1 完成 — 成分股日線資料")
    print(f"{'='*62}")
    if close is not None:
        have = [t for t in close.columns if close[t].notna().sum() > 0]
        miss = sorted(set(yahoo) - set(have))
        print(f"  價格寬表 : {close.shape[0]} 天 x {close.shape[1]} 檔")
        print(f"  日期範圍 : {close.index.min().date()} -> {close.index.max().date()}")
        print(f"  有效     : {len(have)} / {len(yahoo)} 檔有資料")
        if miss:
            print(f"  抓不到({len(miss)}): {', '.join(miss[:12])}"
                  + (" ..." if len(miss) > 12 else ""))
    print(f"  S&P 100  : {len(sp100_y)} 檔（橫斷面研究的主宇宙）")
    print(f"  存到     : {DATA}")
    print(f"{'='*62}\n")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
