"""
run_podcast.py — 股癌 podcast pipeline (manual stage runner)

Stages（每個 stage 各自冪等，可單獨跑）：
  --stage list        : 列出 RSS 中的最新 N 集
  --stage download    : 下載最新 N 集 mp3
  --stage transcribe  : 對已下載的 mp3 跑 Whisper（重 CPU）
  --stage extract     : 對 transcripts 跑 LLM 抽取（要 API key）
  --stage all         : 上述全跑

預設只跑近 N=1 集，避免意外大量計算 / 費用。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources.podcast import (
    chunk_segments, download_episode, episode_to_posts,
    parse_feed, transcribe_episode,
)

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw" / "podcast" / "gooaye"
WHISPER_MODEL = ROOT / "transcription" / "models" / "large-v3-turbo"
KOL = "gooaye"


def stage_list(n: int) -> None:
    feed = RAW / "feed.xml"
    if not feed.exists():
        sys.exit(f"找不到 RSS：{feed}")
    eps = parse_feed(feed)
    print(f"[list] 總集數 {len(eps)}，顯示最新 {n}：")
    for e in eps[:n]:
        dur = f"{e.duration_sec//60}min" if e.duration_sec else "?"
        print(f"  {e.pub_date.date()} | {e.ep_id:>10} | {dur:>5} | {e.title[:50]}")


def stage_download(n: int) -> None:
    eps = parse_feed(RAW / "feed.xml")
    for e in eps[:n]:
        download_episode(e, RAW)


def stage_transcribe(n: int) -> None:
    if not WHISPER_MODEL.exists():
        sys.exit(f"找不到 Whisper model：{WHISPER_MODEL}\n"
                 f"先跑 transcription/download_model.py")
    eps = parse_feed(RAW / "feed.xml")
    for e in eps[:n]:
        mp3 = RAW / e.safe_filename()
        if not mp3.exists():
            print(f"[transcribe] 跳過 {e.ep_id}（mp3 未下載）")
            continue
        transcribe_episode(mp3, str(WHISPER_MODEL), RAW)


def stage_extract(n: int) -> None:
    """對近 n 集已 transcribe 的內容跑 LLM 抽取，輸出統一 RawPost JSONL。"""
    from extract.llm import extract  # noqa: imports here to avoid early API client init

    eps = parse_feed(RAW / "feed.xml")
    out_jsonl = ROOT / "data" / "raw" / "podcast" / "gooaye_posts.jsonl"
    out_jsonl.parent.mkdir(exist_ok=True, parents=True)

    written = 0
    with open(out_jsonl, "w", encoding="utf-8") as fout:
        for e in eps[:n]:
            seg_path = RAW / f"{e.ep_id}.segments.json"
            if not seg_path.exists():
                print(f"[extract] 跳過 {e.ep_id}（segments 不存在）")
                continue
            with open(seg_path, encoding="utf-8") as f:
                segments = json.load(f)["segments"]
            chunks = chunk_segments(segments, chunk_sec=300)
            posts = episode_to_posts(e, KOL, chunks)
            print(f"[extract] {e.ep_id}: {len(chunks)} chunks → LLM ...")
            for post in posts:
                ctx = f"來源：股癌 podcast {e.ep_id}（{e.pub_date.date()}）"
                try:
                    ext = extract(post.text, context=ctx)
                except Exception as ex:
                    print(f"  ✗ chunk{post.extra['chunk_idx']:03d} 失敗：{ex}")
                    continue
                rec = post.to_dict()
                rec["extraction"] = {
                    "has_market_content": ext.has_market_content,
                    "summary": ext.summary,
                    "targets": [t.__dict__ for t in ext.targets],
                }
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                written += 1
                tag = "★" if ext.targets else "·"
                print(f"  {tag} chunk{post.extra['chunk_idx']:03d} "
                      f"targets={len(ext.targets):>2} | {ext.summary[:50]}")
    print(f"[extract] → {out_jsonl} ({written} records)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True,
                   choices=["list", "download", "transcribe", "extract", "all"])
    p.add_argument("-n", type=int, default=1, help="處理最新 N 集（預設 1）")
    args = p.parse_args()

    if args.stage in ("list", "all"):
        stage_list(args.n)
    if args.stage in ("download", "all"):
        stage_download(args.n)
    if args.stage in ("transcribe", "all"):
        stage_transcribe(args.n)
    if args.stage in ("extract", "all"):
        stage_extract(args.n)


if __name__ == "__main__":
    main()
