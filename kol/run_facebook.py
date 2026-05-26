"""
run_facebook.py — Facebook KOL scraper batch runner

依設定 KOL list 抓 N 則最新貼文，輸出 unified RawPost JSONL。
冪等：已存在的 post_id 不重複抓（後續加 dedup 會處理）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources.facebook import fetch_posts  # noqa: E402

load_dotenv()

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "data" / "raw" / "fb"

# 我們追蹤的 KOL 名單（Page URL → 內部 kol id）
KOLS = {
    "panzheng_king":   ("盤整之王",        "https://www.facebook.com/profile.php?id=61567875730267"),
    "uncle_us_notes":  ("Uncle 大叔美股",  "https://www.facebook.com/Unclestocknotess"),
    # "8zz":           ("巴逆逆",          "https://www.facebook.com/8zz"),  # 私人 profile，公開抓不到
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("-n", type=int, default=20, help="每位 KOL 抓最新 N 則")
    p.add_argument("--kol", help="只抓指定 kol id（預設全跑）")
    p.add_argument("--since", help="只抓比此時間新的貼文（ISO 或 '2 days'）")
    args = p.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = {args.kol: KOLS[args.kol]} if args.kol else KOLS

    total_posts = 0
    for kol_id, (display, url) in targets.items():
        print(f"\n=== {display} ({kol_id}) ===")
        posts = fetch_posts(url, kol_id, max_posts=args.n, only_newer_than=args.since)
        print(f"  fetched {len(posts)} posts")

        out = OUT_DIR / f"{kol_id}_posts.jsonl"
        with open(out, "w", encoding="utf-8") as f:
            for post in posts:
                f.write(json.dumps(post.to_dict(), ensure_ascii=False) + "\n")
        print(f"  → {out}")
        total_posts += len(posts)

        # 顯示時間範圍
        if posts:
            print(f"  範圍: {posts[-1].timestamp.date()} ~ {posts[0].timestamp.date()}")
            print(f"  平均互動: likes={sum(p.extra['likes'] for p in posts)/len(posts):.0f}, "
                  f"comments={sum(p.extra['comments'] for p in posts)/len(posts):.0f}")

    print(f"\n[total] {total_posts} posts across {len(targets)} KOLs")


if __name__ == "__main__":
    main()
