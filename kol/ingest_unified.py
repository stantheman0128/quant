"""
ingest_unified.py — 把所有資料源合併成統一 panel

Sources:
  1. banini-public.db → 8zz 已處理過的 305 predictions（已含 OHLC）
  2. data/raw/fb/*_extracted.jsonl → 新 FB KOL（需現抓 OHLC）
  3. data/raw/podcast/*_extracted.jsonl → podcast KOL（需現抓 OHLC）

統一 schema (unified_predictions.parquet):
  prediction_uid, kol, source, post_id, post_url, created_date,
  symbol_name, symbol_code, market, symbol_type,
  action, view, conviction, reasoning,
  base_price, ret_1d..5d, max_ret_5d, min_ret_5d,
  engagement (likes/comments/shares 來自 FB; null for others)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources.price import compute_returns

ROOT = Path(__file__).resolve().parent
BANINI_DB = ROOT / "data" / "banini-public.db"
EXTRACTED_DIR = ROOT / "data" / "extracted"
OUT = ROOT / "data" / "unified_predictions.parquet"


def load_banini() -> pd.DataFrame:
    """從 banini-public.db 讀取 + price_snapshots 計 ret_1..5d"""
    conn = sqlite3.connect(BANINI_DB)
    p = pd.read_sql(
        "SELECT id, post_id, post_url, symbol_name, symbol_code, symbol_type, "
        "her_action, reverse_view, base_price, created_at, status "
        "FROM predictions WHERE base_price IS NOT NULL AND symbol_code IS NOT NULL",
        conn,
    )
    ps = pd.read_sql("SELECT * FROM price_snapshots", conn)
    conn.close()

    # pivot price_snapshots
    pvt = ps.pivot_table(index="prediction_id", columns="day_number",
                         values=["close_price", "high_price", "low_price"])
    pvt.columns = [f"{k}_d{d}" for k, d in pvt.columns]
    df = p.set_index("id").join(pvt, how="left")

    # ret_1..5d
    for d in range(1, 6):
        col = f"close_price_d{d}"
        if col in df.columns:
            df[f"ret_{d}d"] = df[col] / df["base_price"] - 1
    high_cols = [f"high_price_d{d}" for d in range(1, 6) if f"high_price_d{d}" in df.columns]
    low_cols = [f"low_price_d{d}" for d in range(1, 6) if f"low_price_d{d}" in df.columns]
    if high_cols:
        df["max_ret_5d"] = df[high_cols].max(axis=1) / df["base_price"] - 1
    if low_cols:
        df["min_ret_5d"] = df[low_cols].min(axis=1) / df["base_price"] - 1
    df = df.drop(columns=high_cols + low_cols + [f"close_price_d{d}" for d in range(1, 6)
                 if f"close_price_d{d}" in df.columns])

    # 對齊統一 schema
    df = df.reset_index().rename(columns={
        "id": "prediction_uid",
        "post_id": "post_id",
        "her_action": "action",
        "reverse_view": "raw_reverse_view",  # 留著但不直接用方向
    })
    df["prediction_uid"] = "banini_" + df["prediction_uid"].astype(str)
    df["kol"] = "8zz"
    df["source"] = "banini-tracker"
    df["created_date"] = pd.to_datetime(df["created_at"]).dt.tz_localize(None).dt.normalize()
    df["market"] = "TW"  # banini 全為台股
    df["conviction"] = "mid"  # banini DB 沒這欄
    df["reasoning"] = None

    # banini 的 reverse_view → view 中性化
    # 反指標 reverse_view='空' = 她「持有/看好」(我們記成 holding_long)
    # 反指標 reverse_view='多' = 她「停損/看衰」(我們記成 exit/bearish)
    # 但這裡為了統一，我們改記 KOL 的「實際立場」（反向 reverse_view）
    df["view"] = df["raw_reverse_view"].map({"空": "bullish", "多": "bearish"}).fillna("neutral")
    df["engagement"] = 0  # banini 沒留

    return df[["prediction_uid", "kol", "source", "post_id", "post_url", "created_date",
               "symbol_name", "symbol_code", "market", "symbol_type",
               "action", "view", "conviction", "reasoning",
               "base_price", "ret_1d", "ret_2d", "ret_3d", "ret_4d", "ret_5d",
               "max_ret_5d", "min_ret_5d", "engagement"]]


def load_extracted_jsonl(path: Path, raw_dir: Path | None = None) -> pd.DataFrame:
    """讀 extract pipeline 輸出 (僅 uid + extraction)，
    用 uid JOIN raw posts JSONL 補回 source/kol/timestamp/url/engagement."""
    raw_dir = raw_dir or (Path(__file__).resolve().parent / "data" / "raw" / "fb")
    # Build uid → raw post lookup from all raw JSONL files
    uid_lookup: dict[str, dict] = {}
    for rf in raw_dir.glob("*_posts.jsonl"):
        for line in open(rf, encoding="utf-8"):
            p = json.loads(line)
            uid_lookup[p["uid"]] = p

    rows = []
    for line in open(path, encoding="utf-8"):
        rec = json.loads(line)
        ext = rec.get("extraction", {})
        if not ext.get("has_market_content"):
            continue
        raw = uid_lookup.get(rec["uid"])
        if not raw:
            print(f"  [warn] uid not found in raw: {rec['uid']}")
            continue
        for tgt in ext.get("targets", []):
            rows.append({
                "prediction_uid": f"{raw['source']}_{raw['kol']}_{rec['uid'][-8:]}_{tgt['name'][:20]}",
                "kol": raw["kol"],
                "source": raw["source"],
                "post_id": raw["post_id"],
                "post_url": raw["url"],
                "created_date": pd.to_datetime(raw["timestamp"]).tz_localize(None).normalize(),
                "symbol_name": tgt["name"],
                "symbol_code": tgt.get("code_hint"),
                "market": tgt.get("market", "TW"),
                "symbol_type": tgt["type"],
                "action": tgt["action"],
                "view": tgt["view"],
                "conviction": tgt["conviction"],
                "reasoning": tgt.get("reasoning"),
                "engagement": raw.get("extra", {}).get("likes", 0)
                              + 2 * raw.get("extra", {}).get("comments", 0),
            })
    return pd.DataFrame(rows)


def attach_returns(df: pd.DataFrame) -> pd.DataFrame:
    """對缺 base_price 的列即時抓 OHLC."""
    out = df.copy()
    cols = ["base_price", "ret_1d", "ret_2d", "ret_3d", "ret_4d", "ret_5d",
            "max_ret_5d", "min_ret_5d"]
    for c in cols:
        if c not in out.columns:
            out[c] = None

    need = out[out["base_price"].isna() & out["symbol_code"].notna()]
    print(f"[returns] 需要抓 {len(need)} 筆價格...")
    for idx, row in need.iterrows():
        d = row["created_date"].date() if hasattr(row["created_date"], "date") else row["created_date"]
        r = compute_returns(row["symbol_code"], row["market"], d)
        if not r:
            continue
        for c in cols:
            if c in r:
                out.at[idx, c] = r[c]
    return out


def main():
    pieces = []
    print("=== loading banini ===")
    bani = load_banini()
    print(f"  {len(bani)} predictions from 8zz")
    pieces.append(bani)

    if EXTRACTED_DIR.exists():
        for f in sorted(EXTRACTED_DIR.glob("*.jsonl")):
            print(f"=== loading {f.name} ===")
            df = load_extracted_jsonl(f)
            print(f"  {len(df)} (post × target) rows")
            df = attach_returns(df)
            pieces.append(df)
    else:
        print(f"[warn] {EXTRACTED_DIR} 不存在；只有 banini 資料")

    unified = pd.concat(pieces, ignore_index=True)
    print(f"\n[unified] {len(unified)} total rows across {unified['kol'].nunique()} KOLs")
    print(unified.groupby("kol").size().to_string())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    unified.to_parquet(OUT, index=False)
    print(f"→ {OUT}")


if __name__ == "__main__":
    main()
