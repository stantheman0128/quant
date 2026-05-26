"""
ingest.py — banini-public.db → enriched predictions parquet

讀取 predictions + price_snapshots，產出每個預測在 T+1..T+5 的報酬。

Output schema:
    prediction_id, symbol_code, symbol_name, symbol_type,
    her_action, reverse_view, conviction_tier, created_date,
    base_price, ret_1d, ret_2d, ret_3d, ret_5d, max_ret_5d, min_ret_5d,
    direction (+1=反指標看漲, -1=反指標看跌)
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent / "output"

# her_action 強度分層：用文字關鍵字推斷 conviction（公開 DB 沒有 confidence 欄位）
CONVICTION_TIERS = {
    "high": ["all in", "重押", "梭哈", "全力", "加碼", "確定"],
    "mid":  ["買入", "賣出", "停損", "放空", "看多", "看空", "看好", "看衰", "持有"],
    "low":  ["計畫", "考慮", "觀察", "預期", "猶豫", "可能"],
}


def classify_conviction(action: str) -> str:
    """low 與 high 是修飾詞，優先匹配；mid 是預設動作層。"""
    a = (action or "").lower()
    for tier in ("low", "high", "mid"):
        if any(kw.lower() in a for kw in CONVICTION_TIERS[tier]):
            return tier
    return "mid"  # default


def load_predictions(db_path: Path) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    p = pd.read_sql(
        "SELECT id, symbol_code, symbol_name, symbol_type, her_action, "
        "reverse_view, base_price, created_at, status "
        "FROM predictions WHERE base_price IS NOT NULL AND symbol_code IS NOT NULL",
        conn,
    )
    ps = pd.read_sql("SELECT * FROM price_snapshots", conn)
    conn.close()
    return p, ps


def build_returns_panel(predictions: pd.DataFrame, snapshots: pd.DataFrame) -> pd.DataFrame:
    """把 5 個 day_number 的 close_price 攤平成欄位，計算各天累積報酬。"""
    # pivot day → flat columns
    snap_pvt = snapshots.pivot_table(
        index="prediction_id", columns="day_number",
        values=["close_price", "high_price", "low_price"],
    )
    snap_pvt.columns = [f"{kind}_d{d}" for kind, d in snap_pvt.columns]

    df = predictions.set_index("id").join(snap_pvt, how="left")
    df.index.name = "prediction_id"

    # 計算 T+N close 報酬（vs base_price）
    for d in range(1, 6):
        col = f"close_price_d{d}"
        if col in df.columns:
            df[f"ret_{d}d"] = df[col] / df["base_price"] - 1.0

    # 5 日內最高/最低報酬（path-dependent）
    high_cols = [f"high_price_d{d}" for d in range(1, 6) if f"high_price_d{d}" in df.columns]
    low_cols = [f"low_price_d{d}" for d in range(1, 6) if f"low_price_d{d}" in df.columns]
    if high_cols:
        df["max_ret_5d"] = df[high_cols].max(axis=1) / df["base_price"] - 1.0
    if low_cols:
        df["min_ret_5d"] = df[low_cols].min(axis=1) / df["base_price"] - 1.0

    # 丟掉中間欄位
    df = df.drop(columns=high_cols + low_cols + [f"close_price_d{d}" for d in range(1, 6) if f"close_price_d{d}" in df.columns])
    return df.reset_index()


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    df["created_date"] = pd.to_datetime(df["created_at"]).dt.tz_localize(None).dt.normalize()
    df["conviction_tier"] = df["her_action"].apply(classify_conviction)

    # direction：reverseView 是「反指標方向」
    #   "空" → 反指標認為會跌 → 我們 short → direction = -1
    #   "多" → 反指標認為會漲 → 我們 long → direction = +1
    df["direction"] = df["reverse_view"].map({"多": +1, "空": -1}).fillna(0).astype(int)
    return df


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    p, ps = load_predictions(DATA_DIR / "banini-public.db")
    print(f"[ingest] predictions: {len(p)}, snapshots: {len(ps)}")

    panel = build_returns_panel(p, ps)
    panel = enrich(panel)

    # 過濾掉沒有 ret_5d 的（追蹤未滿 5 日）
    valid = panel.dropna(subset=["ret_5d"]).copy()
    print(f"[ingest] valid (with ret_5d): {len(valid)} / {len(panel)}")

    out_path = OUT_DIR / "banini_predictions.parquet"
    valid.to_parquet(out_path, index=False)
    print(f"[ingest] → {out_path}")

    # 速覽
    print("\n[summary]")
    print(f"  date range: {valid['created_date'].min().date()} ~ {valid['created_date'].max().date()}")
    print(f"  unique symbols: {valid['symbol_code'].nunique()}")
    print(f"  by symbol_type:\n{valid['symbol_type'].value_counts().to_string()}")
    print(f"  by direction:\n{valid['direction'].value_counts().to_string()}")
    print(f"  by conviction_tier:\n{valid['conviction_tier'].value_counts().to_string()}")
    print(f"  ret_5d mean / std: {valid['ret_5d'].mean():.4f} / {valid['ret_5d'].std():.4f}")


if __name__ == "__main__":
    main()
