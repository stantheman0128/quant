"""
切分 RawPost JSONL 成多個小 chunk 給平行 subagent 處理。

用法:
  python scripts/split_for_extract.py --chunk-size 80 --out-dir data/extract_chunks
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="data/raw/fb")
    p.add_argument("--out-dir", default="data/extract_chunks")
    p.add_argument("--chunk-size", type=int, default=80)
    args = p.parse_args()

    in_dir = ROOT / args.input_dir
    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    chunks_meta = []
    chunk_idx = 0
    for f in sorted(in_dir.glob("*_posts.jsonl")):
        kol_id = f.stem.replace("_posts", "")
        posts = [json.loads(line) for line in open(f, encoding="utf-8")]
        print(f"{kol_id}: {len(posts)} posts → ", end="")

        for i in range(0, len(posts), args.chunk_size):
            chunk = posts[i:i + args.chunk_size]
            out = out_dir / f"chunk_{chunk_idx:03d}_{kol_id}.jsonl"
            with open(out, "w", encoding="utf-8") as g:
                for p_ in chunk:
                    g.write(json.dumps(p_, ensure_ascii=False) + "\n")
            chunks_meta.append({
                "chunk_id": f"{chunk_idx:03d}",
                "kol": kol_id,
                "n_posts": len(chunk),
                "file": str(out.relative_to(ROOT)),
            })
            chunk_idx += 1
        print(f"{(len(posts) + args.chunk_size - 1) // args.chunk_size} chunks")

    # write manifest
    manifest = out_dir / "manifest.json"
    with open(manifest, "w", encoding="utf-8") as g:
        json.dump(chunks_meta, g, ensure_ascii=False, indent=2)
    print(f"\n→ manifest: {manifest} ({len(chunks_meta)} chunks total)")


if __name__ == "__main__":
    main()
