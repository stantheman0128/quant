"""
等多個 Apify runs 完成 + 拉 dataset + 存 RawPost JSONL。

用法:
  python scripts/wait_and_save.py panzheng_king:MalEN37xEpb4eElBD uncle_us_notes:mbO0WbaNiIqgB4KOg
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv()

from sources.facebook import _fetch_dataset, _wait_for_run  # noqa: E402
from sources.base import RawPost  # noqa: E402

import os
TOKEN = os.environ["APIFY_TOKEN"]
OUT = ROOT / "data" / "raw" / "fb"
OUT.mkdir(parents=True, exist_ok=True)


def items_to_posts(items: list[dict], kol: str, page_url: str) -> list[RawPost]:
    posts = []
    for item in items:
        if "error" in item:
            continue
        raw_text = item.get("text") or item.get("message") or ""
        ocr = "\n".join((m.get("ocrText") or "") for m in (item.get("media") or []) if m.get("ocrText"))
        caption = "\n".join((m.get("captionText") or "") for m in (item.get("media") or []) if m.get("captionText")) or item.get("captionText") or ""
        full_text = "\n\n".join(filter(None, [raw_text, caption, ocr]))
        if not full_text.strip():
            continue
        ts_str = item.get("time") or item.get("timestamp") or ""
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            ts = datetime.now()
        media = (item.get("media") or [{}])[0]
        media_type = (media.get("__typename") or "Photo").lower()
        posts.append(RawPost(
            source="fb", kol=kol,
            post_id=str(item.get("postId") or item.get("id") or item.get("url", "")),
            url=item.get("url", page_url), timestamp=ts, text=full_text, media_type=media_type,
            extra={
                "likes": item.get("likes", 0), "comments": item.get("comments", 0),
                "shares": item.get("shares", 0), "raw_text": raw_text,
                "caption_text": caption, "ocr_text": ocr,
            },
        ))
    return posts


def main():
    pairs = [arg.split(":") for arg in sys.argv[1:]]
    for kol, run_id in pairs:
        print(f"\n=== {kol} ({run_id}) ===")
        ds_id = _wait_for_run(TOKEN, run_id, poll_interval=20, max_wait=2400)
        items = _fetch_dataset(TOKEN, ds_id)
        page_url = items[0].get("inputUrl", "") if items else ""
        posts = items_to_posts(items, kol, page_url)
        out = OUT / f"{kol}_posts.jsonl"
        with open(out, "w", encoding="utf-8") as f:
            for p in posts:
                f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")
        print(f"→ {out}: {len(posts)} posts")
        if posts:
            print(f"   範圍: {posts[-1].timestamp.date()} ~ {posts[0].timestamp.date()}")


if __name__ == "__main__":
    main()
