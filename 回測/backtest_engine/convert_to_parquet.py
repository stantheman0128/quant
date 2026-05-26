"""
一次性腳本：將所有 tick CSV 轉換為 Parquet 格式。

Parquet 優勢：
- 讀取速度快 5-10x（列式壓縮 + 跳過不需要的欄位）
- 檔案大小約為 CSV 的 30-50%
- 保留 dtype，不用每次 parse

用法: python -m backtest_engine.convert_to_parquet
"""

import time
from pathlib import Path

import pandas as pd
import numpy as np

from .data_loader import _TICK_DTYPES


def convert_csv_to_parquet(csv_path: Path, output_dir: Path) -> Path:
    """單檔 CSV → Parquet，只保留需要的欄位。"""
    df = pd.read_csv(
        csv_path,
        dtype=_TICK_DTYPES,
        usecols=['time_msc', 'bid', 'ask'],
    )
    df['datetime'] = pd.to_datetime(df['time_msc'], unit='ms', utc=True)
    df.set_index('datetime', inplace=True)
    df.drop(columns=['time_msc'], inplace=True)
    df['mid'] = (df['bid'] + df['ask']) / 2

    output_path = output_dir / csv_path.with_suffix('.parquet').name
    df.to_parquet(output_path, engine='pyarrow', compression='snappy')
    return output_path


def convert_all(data_dir: str | Path = None) -> None:
    """轉換所有 CSV 到對應的 parquet 目錄。"""
    if data_dir is None:
        data_dir = Path(__file__).parent.parent

    data_dir = Path(data_dir)

    for sub in sorted(data_dir.iterdir()):
        if not sub.is_dir() or sub.name.startswith(('__', '.', 'backtest')):
            continue

        csv_files = sorted(sub.glob('*.csv'))
        if not csv_files:
            continue

        # 建立 parquet 目錄
        pq_dir = data_dir / f"{sub.name}_parquet"
        pq_dir.mkdir(exist_ok=True)

        print(f"\n轉換 {sub.name}/ → {pq_dir.name}/ ({len(csv_files)} 檔案)")

        for i, csv_path in enumerate(csv_files, 1):
            t0 = time.perf_counter()
            pq_path = convert_csv_to_parquet(csv_path, pq_dir)

            csv_size = csv_path.stat().st_size / 1024 / 1024
            pq_size = pq_path.stat().st_size / 1024 / 1024
            elapsed = time.perf_counter() - t0
            ratio = pq_size / csv_size * 100

            print(f"  [{i:2d}/{len(csv_files)}] {csv_path.stem}: "
                  f"{csv_size:.0f}MB → {pq_size:.0f}MB ({ratio:.0f}%) | {elapsed:.1f}s")

    print("\n轉換完成！")


if __name__ == '__main__':
    convert_all()
