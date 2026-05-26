"""
數據載入模組 — MT5 Tick CSV / Parquet → OHLCV Resample

優先讀 Parquet（快 5-10x），沒有的話 fallback 到 CSV。
支援的 resample 頻率: '1min', '5min', '15min', '1h', '4h', '1D'
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd


# MT5 tick CSV 欄位型別
_TICK_DTYPES = {
    'time': np.int64,
    'bid': np.float64,
    'ask': np.float64,
    'last': np.float64,
    'volume': np.int64,
    'time_msc': np.int64,
    'flags': np.int64,
    'volume_real': np.float64,
}


def load_ticks(path: str | Path) -> pd.DataFrame:
    """
    載入 tick 數據（自動判斷 CSV 或 Parquet）。
    回傳含 datetime index + bid, ask, mid 欄位的 DataFrame。
    """
    path = Path(path)
    if path.suffix == '.parquet':
        return _load_parquet(path)
    return _load_csv(path)


def _load_csv(path: Path) -> pd.DataFrame:
    """載入 MT5 tick CSV"""
    df = pd.read_csv(
        path,
        dtype=_TICK_DTYPES,
        usecols=['time_msc', 'bid', 'ask'],
    )
    df['datetime'] = pd.to_datetime(df['time_msc'], unit='ms', utc=True)
    df.set_index('datetime', inplace=True)
    df.drop(columns=['time_msc'], inplace=True)
    df['mid'] = (df['bid'] + df['ask']) / 2
    return df


def _load_parquet(path: Path) -> pd.DataFrame:
    """載入已轉換的 Parquet（已含 mid, datetime index）"""
    return pd.read_parquet(path, engine='pyarrow')


def resample_ohlcv(ticks: pd.DataFrame, freq: str = '1h') -> pd.DataFrame:
    """
    Tick DataFrame → OHLCV (基於 mid price)。

    Parameters
    ----------
    ticks : DataFrame with 'mid' column and datetime index
    freq  : resample 頻率 ('1min', '5min', '15min', '1h', '4h', '1D')
    """
    ohlcv = ticks['mid'].resample(freq).agg(
        open='first',
        high='max',
        low='min',
        close='last',
    )
    ohlcv['tick_count'] = ticks['mid'].resample(freq).count()
    ohlcv.dropna(subset=['open'], inplace=True)

    ohlcv['spread'] = (
        ticks['ask'].resample(freq).last() - ticks['bid'].resample(freq).last()
    ).reindex(ohlcv.index)

    return ohlcv


def load_and_resample(path: str | Path, freq: str = '1h', cache_dir: Path | None = None) -> pd.DataFrame:
    """
    一步到位：載入 tick → resample 成 OHLCV。
    如果指定 cache_dir，會快取 OHLCV 結果，下次直接讀取（<10ms）。
    """
    path = Path(path)

    # 嘗試讀快取
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_file = cache_dir / f"{path.stem}_{freq}.parquet"
        if cache_file.exists():
            return pd.read_parquet(cache_file, engine='pyarrow')

    ticks = load_ticks(path)
    ohlcv = resample_ohlcv(ticks, freq)

    # 寫入快取
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        ohlcv.to_parquet(cache_file, engine='pyarrow')

    return ohlcv


def list_available_symbols(data_dir: str | Path) -> dict[str, list[str]]:
    """
    掃描數據目錄，回傳可用的 {symbol: [years]}。
    優先掃 parquet 目錄，再補 CSV 目錄。
    """
    data_dir = Path(data_dir)
    symbols: dict[str, list[str]] = {}

    csv_pattern = re.compile(r'^(.+)_1y_(\d{2})\.csv$')
    pq_pattern = re.compile(r'^(.+)_1y_(\d{2})\.parquet$')

    for sub in sorted(data_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith(('__', '.', 'backtest')):
            continue
        for f in sorted(sub.iterdir()):
            for pat in (pq_pattern, csv_pattern):
                m = pat.match(f.name)
                if m:
                    sym, year = m.group(1), m.group(2)
                    if sym not in symbols:
                        symbols[sym] = []
                    if year not in symbols[sym]:
                        symbols[sym].append(year)
                    break

    return symbols


def find_data_file(data_dir: str | Path, symbol: str, year: str) -> Path:
    """
    根據 symbol + year 找到數據檔案。
    優先找 Parquet，沒有就找 CSV。
    """
    data_dir = Path(data_dir)

    # 優先 Parquet
    pq_path = data_dir / f"1y_{year}_parquet" / f"{symbol}_1y_{year}.parquet"
    if pq_path.exists():
        return pq_path

    # Fallback CSV
    csv_path = data_dir / f"1y_{year}" / f"{symbol}_1y_{year}.csv"
    if csv_path.exists():
        return csv_path

    raise FileNotFoundError(
        f"找不到 {symbol} 20{year} 的數據檔案。\n"
        f"  嘗試過: {pq_path}\n"
        f"  嘗試過: {csv_path}"
    )
