"""
build_clean_schema.py
---------------------
把現有 unified_predictions.parquet 轉換成 4 欄位 clean schema：

    {
      "timestamp": ISO-8601 with timezone,
      "id":        標的代號 (entity-disambiguated),
      "direction": -1 / 0 / +1,
      "weight":    KOL 在該時點的 walk-forward 歷史 hit rate ∈ [0, 1]
    }

設計原則：
  1. 嚴格 walk-forward：weight 只用「該 prediction 之前」的資料算
  2. 樣本不足時 weight=0.5 (中性)，至少 30 prior samples 才估
  3. 細粒度 weight：用 (KOL × market) 切片，因為 panzheng 在 TW vs US skill 差異大
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from skill_score import VIEW_TO_DIRECTION  # noqa: E402

OUT = ROOT / "data" / "clean_schema.jsonl"
META = ROOT / "data" / "clean_schema_meta.json"
MIN_PRIOR_SAMPLES = 30


# === Entity disambiguation ===

# 台股名稱 → 代碼（從 banini-tracker 的 stock-map + 我們資料補充）
TW_NAME_TO_CODE = {
    "台積電": "2330", "信驊": "5274", "聯發科": "2454", "鴻海": "2317",
    "台達電": "2308", "南亞科": "2408", "華邦電": "2344", "玉山金": "2884",
    "聯電": "2303", "中華電": "2412", "群聯": "8299", "穎崴": "6515",
    "鈦昇": "8027", "欣興": "3037", "旺宏": "2337", "智邦": "2345",
    "聯亞": "3081", "健策": "3653", "景碩": "3189", "力旺": "3529",
    "穩懋": "3105", "台燿": "6274", "宜鼎": "5289", "威剛": "3260",
    "波若威": "3163", "昇達科": "3491", "緯穎": "6669", "鴻勁": "6890",
    "精測": "6510", "PCB": "3037",  # PCB 概念多取 欣興 為代表
    "原油正二": "00715L", "0050": "0050", "00981A": "00981A",
    "00735": "00735", "00713": "00713", "00992A": "00992A",
    "00922": "00922", "00935": "00935", "006201": "006201",
    "006204": "006204", "00891": "00891", "00892": "00892",
    "00913": "00913", "00988A": "00988A", "00878": "00878",
    "00631L": "00631L", "00715L": "00715L", "00909": "00909",
    "0053": "0053", "饗賓集團": "2729", "南亞": "1303", "台泥": "1101",
    "亞泥": "1102", "中鋼": "2002", "長榮": "2603", "陽明": "2609",
    "華航": "2610",
}

# 美股常見公司中文 → ticker
US_NAME_TO_TICKER = {
    "Intuitive Surgical": "ISRG", "ISRG": "ISRG",
    "ADBE": "ADBE", "Adobe": "ADBE",
    "Palantir": "PLTR", "PLTR": "PLTR",
    "NVDA": "NVDA", "NVIDIA": "NVDA", "輝達": "NVDA",
    "AAPL": "AAPL", "Apple": "AAPL", "蘋果": "AAPL",
    "GOOGL": "GOOGL", "GOOG": "GOOGL", "Google": "GOOGL", "Alphabet": "GOOGL",
    "META": "META", "Meta": "META",
    "TSLA": "TSLA", "Tesla": "TSLA", "特斯拉": "TSLA",
    "AMZN": "AMZN", "Amazon": "AMZN", "亞馬遜": "AMZN",
    "MSFT": "MSFT", "Microsoft": "MSFT", "微軟": "MSFT",
    "WMT": "WMT", "Walmart": "WMT", "沃爾瑪": "WMT",
    "COST": "COST", "Costco": "COST",
    "AVGO": "AVGO", "Broadcom": "AVGO", "博通": "AVGO",
    "MU": "MU", "Micron": "MU", "美光": "MU",
    "SNDK": "SNDK", "TSM": "TSM", "台積 ADR": "TSM",
    "ORCL": "ORCL", "Oracle": "ORCL",
    "PLTR": "PLTR", "BTC": "BTC-USD", "比特幣": "BTC-USD",
    "ETH": "ETH-USD", "以太幣": "ETH-USD",
    "GLD": "GLD", "黃金": "GLD",
    "SLV": "SLV", "白銀": "SLV",
    "QQQ": "QQQ", "VOO": "VOO", "VT": "VT",
    "QLD": "QLD", "SOXL": "SOXL", "SOXX": "SOXX",
}


def normalize_id(symbol_name: str, code_hint: str | None, market: str) -> str | None:
    """正規化標的 ID。"""
    if code_hint:
        # banini & 部分 LLM 已給 code → 直接用
        return code_hint.strip().upper() if market == "US" else code_hint.strip()
    name = (symbol_name or "").strip()
    if not name:
        return None
    if market == "TW":
        return TW_NAME_TO_CODE.get(name, name)  # fallback to name
    if market == "US":
        return US_NAME_TO_TICKER.get(name, name.upper())
    return name


def compute_walk_forward_weight(df: pd.DataFrame) -> pd.DataFrame:
    """
    對每個 prediction 算 walk-forward weight：
      weight = 該 KOL × market 在「此時點之前」的 hit_rate (順著做)
    """
    df = df.sort_values(["kol", "market", "created_date"]).reset_index(drop=True)
    df["weight"] = np.nan

    # 分組計算 expanding hit rate
    for (kol, mkt), grp in df.groupby(["kol", "market"], observed=True):
        idxs = grp.index
        # only use rows with valid ret_5d & non-zero direction for skill estimation
        valid_mask = grp["ret_5d"].notna() & (grp["direction"] != 0)
        valid = grp[valid_mask].copy()
        if valid.empty:
            df.loc[idxs, "weight"] = 0.5
            continue
        valid["aligned"] = (np.sign(valid["ret_5d"]) == valid["direction"]).astype(int)
        # cumulative count and hits up to (but NOT including) current row
        cum_n = valid["aligned"].expanding().count() - 1  # exclude self
        cum_hits = valid["aligned"].cumsum() - valid["aligned"]  # exclude self
        wf_hr = (cum_hits / cum_n).where(cum_n >= MIN_PRIOR_SAMPLES, 0.5)
        df.loc[valid.index, "weight"] = wf_hr.values
        # rows that lacked ret_5d also keep 0.5 default (cannot estimate)
        df.loc[idxs.difference(valid.index), "weight"] = 0.5

    return df


def main() -> None:
    df = pd.read_parquet(ROOT / "data" / "unified_predictions.parquet")
    print(f"[load] {len(df)} predictions across {df['kol'].nunique()} KOLs")

    # 1) direction 從 view 映射
    df["direction"] = df["view"].map(VIEW_TO_DIRECTION).fillna(0).astype(int)

    # 2) id 實體消歧
    df["id"] = df.apply(
        lambda r: normalize_id(r["symbol_name"], r.get("symbol_code"), r["market"]),
        axis=1,
    )
    n_unmapped = (df["id"].astype(str).str.len() > 6).sum()
    print(f"[id] {df['id'].notna().sum()} mapped, "
          f"{n_unmapped} 可能未消歧（保留原名）")

    # 3) walk-forward weight
    df = compute_walk_forward_weight(df)
    print(f"[weight] mean={df['weight'].mean():.3f}, "
          f"non-default (=0.5) {(df['weight'] != 0.5).sum()} rows")

    # 4) timestamp ISO-8601 with timezone (Taipei)
    df["timestamp"] = pd.to_datetime(df["created_date"]).dt.tz_localize("Asia/Taipei")
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    # fix tz format ±HH:MM
    df["timestamp"] = df["timestamp"].str.replace(
        r"(\+|-)(\d{2})(\d{2})$", r"\1\2:\3", regex=True,
    )

    # 5) output JSONL
    out_records = df[["timestamp", "id", "direction", "weight"]].to_dict("records")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for rec in out_records:
            # round weight to 3 decimals for readability
            rec["weight"] = round(float(rec["weight"]), 3)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[out] {len(out_records)} records → {OUT}")

    # 6) metadata
    meta = {
        "n_records": len(out_records),
        "n_kols": int(df["kol"].nunique()),
        "n_unique_ids": int(df["id"].nunique()),
        "date_range": [str(df["created_date"].min().date()),
                       str(df["created_date"].max().date())],
        "direction_distribution": df["direction"].value_counts().to_dict(),
        "weight_quantiles": {
            f"q{q}": float(df["weight"].quantile(q / 100))
            for q in [5, 25, 50, 75, 95]
        },
        "kols": df["kol"].value_counts().to_dict(),
        "schema": {
            "timestamp": "ISO-8601 with timezone (Asia/Taipei)",
            "id": "entity-disambiguated symbol code (TW: 4-digit, US: ticker)",
            "direction": "-1 (空) / 0 (觀望) / +1 (多)",
            "weight": "walk-forward hit rate (順著做) of (KOL × market) at this time, [0,1]",
        },
        "min_prior_samples_for_weight": MIN_PRIOR_SAMPLES,
    }
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"[meta] → {META}")
    print(f"\n=== summary ===")
    for k, v in meta.items():
        if isinstance(v, dict):
            print(f"{k}:")
            for kk, vv in v.items():
                print(f"  {kk}: {vv}")
        else:
            print(f"{k}: {v}")


if __name__ == "__main__":
    main()
