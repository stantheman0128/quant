#!/usr/bin/env python3
"""Batch MiMo Token Plan jobs — high-throughput, resumable, token-tracked.

Endpoint: https://token-plan-sgp.xiaomimimo.com/v1
Models:   mimo-v2-pro (256K–1M ctx, 2–4x credits) | mimo-v2-omni (256K, 1x)

Usage:
  set MIMO_API_KEY=tp-...
  python mimo_batch.py enrich-posts --workers 8 --max-tokens 4096
  python mimo_batch.py podcast --file data/raw/podcast/gooaye/EP654.segments.json
  python mimo_batch.py burn --workers 16 --rounds 100   # stress / leftover quota
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "https://token-plan-sgp.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2-pro"

ENRICH_SYSTEM = """你是金融 KOL 貼文結構化分析助手。對每篇貼文輸出 JSON，不要 markdown fence。
欄位：
- uid: 原文 uid
- themes: 主題標籤陣列（如 "半導體","ETF","總經"）
- horizon: 短/中/長 或 null
- sentiment_score: -1 到 1
- conviction_score: 0 到 1
- mentioned_tickers: [{symbol, market, name}]
- macro_view: 一句話總經觀點或 null
- actionable_signals: [{ticker, direction, rationale}]
- risk_flags: 風險提示陣列
只輸出 JSON object。"""

PODCAST_SYSTEM = """你是投資 podcast 逐字稿分析助手。輸出 JSON：
- episode_summary: 500 字以內 executive summary（繁中）
- key_tickers: [{symbol, market, view, rationale}]
- macro_thesis: 總經論點
- sector_calls: [{sector, view, conviction}]
- timestamps: [{approx_minute, topic}] 至少 20 條
- quotes: 3–5 句原話摘錄
只輸出 JSON object。"""


@dataclass
class UsageStats:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    requests: int = 0
    errors: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, usage: dict | None) -> None:
        if not usage:
            return
        with self.lock:
            self.prompt_tokens += usage.get("prompt_tokens", 0)
            self.completion_tokens += usage.get("completion_tokens", 0)
            self.total_tokens += usage.get("total_tokens", 0)
            self.requests += 1

    def add_error(self) -> None:
        with self.lock:
            self.errors += 1

    def report(self) -> str:
        return (
            f"requests={self.requests} errors={self.errors} "
            f"prompt={self.prompt_tokens:,} completion={self.completion_tokens:,} "
            f"total={self.total_tokens:,}"
        )


class MiMoClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        timeout: int = 180,
    ) -> tuple[str, dict | None]:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        content = data["choices"][0]["message"].get("content", "")
        return content, data.get("usage")


def load_done_uids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            done.add(json.loads(line)["uid"])
        except (json.JSONDecodeError, KeyError):
            continue
    return done


def iter_posts(*paths: Path):
    for path in paths:
        for line in path.open(encoding="utf-8"):
            rec = json.loads(line)
            text = rec.get("text", "").strip()
            if len(text) < 20:
                continue
            yield rec


def load_podcast_text(path: Path) -> str:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        parts: list[str] = []
        for seg in raw:
            if isinstance(seg, dict):
                parts.append(seg.get("text") or seg.get("segment") or "")
            elif isinstance(seg, str):
                parts.append(seg)
        return "\n".join(p for p in parts if p)
    if isinstance(raw, dict):
        if "text" in raw:
            return raw["text"]
        if "segments" in raw:
            return "\n".join(s.get("text", "") for s in raw["segments"])
    return path.read_text(encoding="utf-8")


def parse_json_loose(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def run_enrich_posts(args: argparse.Namespace, client: MiMoClient, stats: UsageStats) -> None:
    raw_dir = ROOT / "data" / "raw" / "fb"
    out = ROOT / "data" / "mimo_enriched.jsonl"
    done = load_done_uids(out)

    posts = list(iter_posts(raw_dir / "panzheng_king_posts.jsonl", raw_dir / "uncle_us_notes_posts.jsonl"))
    pending = [p for p in posts if p["uid"] not in done]
    if args.limit:
        pending = pending[: args.limit]

    print(f"posts total={len(posts)} pending={len(pending)} -> {out}")

    def work(post: dict) -> tuple[str, dict | None, str | None]:
        user = (
            f"uid: {post['uid']}\n"
            f"kol: {post.get('kol')}\n"
            f"timestamp: {post.get('timestamp')}\n"
            f"likes: {post.get('extra', {}).get('likes', 0)}\n\n"
            f"{post.get('text', '')}"
        )
        try:
            content, usage = client.chat(
                [{"role": "system", "content": ENRICH_SYSTEM}, {"role": "user", "content": user}],
                max_tokens=args.max_tokens,
            )
            parsed = parse_json_loose(content)
            parsed.setdefault("uid", post["uid"])
            return post["uid"], usage, json.dumps({"uid": post["uid"], "enrichment": parsed}, ensure_ascii=False)
        except Exception as exc:  # noqa: BLE001
            return post["uid"], None, json.dumps({"uid": post["uid"], "error": str(exc)}, ensure_ascii=False)

    with out.open("a", encoding="utf-8") as fh, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, p): p["uid"] for p in pending}
        for i, fut in enumerate(as_completed(futures), 1):
            uid, usage, line = fut.result()
            if line:
                fh.write(line + "\n")
                fh.flush()
            if usage:
                stats.add(usage)
            else:
                stats.add_error()
            if i % 10 == 0 or i == len(pending):
                print(f"[{i}/{len(pending)}] {stats.report()}")


def run_podcast(args: argparse.Namespace, client: MiMoClient, stats: UsageStats) -> None:
    src = Path(args.file)
    text = load_podcast_text(src)
    if len(text) < 100:
        raise SystemExit(f"transcript too short: {src}")

    print(f"podcast chars={len(text):,} est_tokens~{len(text)//2:,}")
    content, usage = client.chat(
        [
            {"role": "system", "content": PODCAST_SYSTEM},
            {"role": "user", "content": f"逐字稿如下：\n\n{text}"},
        ],
        max_tokens=args.max_tokens,
        timeout=300,
    )
    stats.add(usage)
    out = ROOT / "data" / f"mimo_podcast_{src.stem}.json"
    try:
        parsed = parse_json_loose(content)
    except json.JSONDecodeError:
        parsed = {"raw": content}
    out.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {out} | {stats.report()}")


def run_burn(args: argparse.Namespace, client: MiMoClient, stats: UsageStats) -> None:
    """Parallel long-output generation — use leftover quota."""

    topics = [
        "台股 2026 記憶體超級循環與 AI 基建",
        "美股 Mag7 vs 小型股輪動",
        "半導體地緣政治與 TSMC 海外布局",
        "日本日銀政策與日股科技",
        "加密貨幣與風險資產相關性",
        "主動式 ETF 溢價折價機制",
        "銅金油大宗商品週期",
        "量化因子：動量 vs 價值 2026",
    ]

    def work(round_idx: int) -> dict | None:
        topic = topics[round_idx % len(topics)]
        prompt = (
            f"第 {round_idx} 輪。請用繁體中文寫一篇 {args.max_tokens // 2} 字以上的深度分析：{topic}。"
            "包含：歷史對照、當前數據假設、3 個情境、可交易標的、風險清單。"
        )
        try:
            _, usage = client.chat([{"role": "user", "content": prompt}], max_tokens=args.max_tokens)
            return usage
        except Exception:  # noqa: BLE001
            return None

    total = args.rounds
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, i) for i in range(total)]
        for i, fut in enumerate(as_completed(futures), 1):
            usage = fut.result()
            if usage:
                stats.add(usage)
            else:
                stats.add_error()
            if i % 5 == 0 or i == total:
                print(f"[{i}/{total}] {stats.report()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MiMo Token Plan batch runner")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--api-key", default=os.environ.get("MIMO_API_KEY", ""))
    common.add_argument("--base-url", default=os.environ.get("MIMO_BASE_URL", DEFAULT_BASE))
    common.add_argument("--model", default=os.environ.get("MIMO_MODEL", DEFAULT_MODEL))
    common.add_argument("--workers", type=int, default=8)
    common.add_argument("--max-tokens", type=int, default=4096)
    common.add_argument("--limit", type=int, default=0, help="max items (0=all)")

    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("enrich-posts", help="deep-enrich ~927 KOL FB posts", parents=[common])
    p_pod = sub.add_parser("podcast", help="analyze long podcast transcript", parents=[common])
    p_pod.add_argument("--file", required=True)
    p_burn = sub.add_parser("burn", help="parallel long-output stress run", parents=[common])
    p_burn.add_argument("--rounds", type=int, default=50)

    args = parser.parse_args()
    if not args.api_key:
        sys.exit("Set MIMO_API_KEY or pass --api-key")

    client = MiMoClient(args.api_key, args.base_url, args.model)
    stats = UsageStats()
    t0 = time.time()

    if args.cmd == "enrich-posts":
        run_enrich_posts(args, client, stats)
    elif args.cmd == "podcast":
        run_podcast(args, client, stats)
    elif args.cmd == "burn":
        run_burn(args, client, stats)

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.0f}s | {stats.report()}")
    if stats.requests:
        print(f"avg {stats.total_tokens / stats.requests:.0f} tokens/request, "
              f"{stats.total_tokens / elapsed:.0f} tokens/sec")


if __name__ == "__main__":
    main()
