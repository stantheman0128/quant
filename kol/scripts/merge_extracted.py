"""
合併所有 chunk_*_extracted.jsonl → 單一 jsonl，
方便下游 ingest_unified.py 處理。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IN_DIR = ROOT / "data" / "extracted"
OUT_DIR = ROOT / "data" / "extracted"


def main():
    # 按 KOL 分組合併
    by_kol = {}
    for f in sorted(IN_DIR.glob("chunk_*_extracted.jsonl")):
        # chunk_NNN_<kol>_extracted.jsonl
        parts = f.stem.split("_")
        kol = "_".join(parts[2:-1])  # everything between "chunk_NNN" and "extracted"
        by_kol.setdefault(kol, []).append(f)

    summary = {}
    for kol, files in by_kol.items():
        out = OUT_DIR / f"{kol}_extracted.jsonl"
        n_posts = n_market = n_targets = 0
        with open(out, "w", encoding="utf-8") as fout:
            for f in files:
                for line in open(f, encoding="utf-8"):
                    rec = json.loads(line)
                    fout.write(line if line.endswith("\n") else line + "\n")
                    n_posts += 1
                    ext = rec.get("extraction", {})
                    if ext.get("has_market_content"):
                        n_market += 1
                    n_targets += len(ext.get("targets", []))
        summary[kol] = (len(files), n_posts, n_market, n_targets)
        print(f"  {kol}: {len(files)} chunks → {out.name} ({n_posts} posts, {n_market} market, {n_targets} targets)")

    print(f"\n[done] merged {len(by_kol)} KOLs")
    return summary


if __name__ == "__main__":
    main()
