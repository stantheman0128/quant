"""
sources/facebook.py — Apify facebook-posts-scraper adapter

設計：
  - fetch_posts(): 呼叫 Apify, 回傳 list[RawPost]
  - 額外保留 engagement (likes, comments, shares) 與 OCR 欄位
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests

from .base import RawPost

ACTOR = "apify~facebook-posts-scraper"
BASE = "https://api.apify.com/v2"

# 5 分鐘以下用 sync（簡單），以上用 async + polling
SYNC_THRESHOLD_POSTS = 50


def _start_async_run(token: str, body: dict) -> str:
    """非同步啟動 actor run，回傳 run_id。"""
    r = requests.post(
        f"{BASE}/acts/{ACTOR}/runs",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body, timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"]["id"]


def _wait_for_run(token: str, run_id: str, poll_interval: int = 15,
                  max_wait: int = 1800) -> str:
    """Poll 到 run 完成，回傳 dataset_id。"""
    import time
    start = time.time()
    while True:
        r = requests.get(f"{BASE}/actor-runs/{run_id}",
                         headers={"Authorization": f"Bearer {token}"}, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]
        status = data["status"]
        items = data.get("stats", {}).get("datasetItemCount", "?")
        elapsed = int(time.time() - start)
        print(f"  [poll {elapsed:>4}s] status={status} items={items}")
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            if status != "SUCCEEDED":
                raise RuntimeError(f"Apify run {status}: {data.get('exitCode')}")
            return data["defaultDatasetId"]
        if elapsed > max_wait:
            raise TimeoutError(f"Apify run 超過 {max_wait}s 仍未完成")
        time.sleep(poll_interval)


def _fetch_dataset(token: str, dataset_id: str) -> list[dict]:
    """抓 dataset 全部 items（自動分頁）。"""
    items, offset = [], 0
    while True:
        r = requests.get(f"{BASE}/datasets/{dataset_id}/items",
                         headers={"Authorization": f"Bearer {token}"},
                         params={"format": "json", "offset": offset, "limit": 1000},
                         timeout=60)
        r.raise_for_status()
        chunk = r.json()
        items.extend(chunk)
        if len(chunk) < 1000:
            break
        offset += 1000
    return items


def fetch_posts(
    page_url: str,
    kol: str,
    max_posts: int = 50,
    only_newer_than: str | None = None,
    only_older_than: str | None = None,
    timeout: int = 600,
    existing_run_id: str | None = None,
) -> list[RawPost]:
    """從 Apify 抓 FB 貼文 → RawPost list。

    < SYNC_THRESHOLD_POSTS 用 run-sync (簡單)，否則用 async + polling。
    existing_run_id：若 specified，直接 wait 既有 run 並抓 dataset（recover orphan）。
    """
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("請在 .env 設 APIFY_TOKEN")

    body: dict[str, Any] = {
        "startUrls": [{"url": page_url}],
        "resultsLimit": max_posts,
        "captionText": True,
    }
    if only_newer_than:
        body["onlyPostsNewerThan"] = only_newer_than
    if only_older_than:
        body["onlyPostsOlderThan"] = only_older_than

    if existing_run_id:
        print(f"  [recover] 接管既有 run {existing_run_id}")
        dataset_id = _wait_for_run(token, existing_run_id)
        items = _fetch_dataset(token, dataset_id)
    elif max_posts <= SYNC_THRESHOLD_POSTS:
        r = requests.post(
            f"{BASE}/acts/{ACTOR}/run-sync-get-dataset-items",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=body, timeout=timeout,
        )
        r.raise_for_status()
        items = r.json()
    else:
        print(f"  [async] 啟動 run for {max_posts} posts ...")
        run_id = _start_async_run(token, body)
        print(f"  [async] run_id={run_id}")
        dataset_id = _wait_for_run(token, run_id)
        items = _fetch_dataset(token, dataset_id)

    posts = []
    for item in items:
        if "error" in item:
            print(f"  [fb] skip error item: {item.get('errorDescription')}")
            continue
        raw_text = item.get("text") or item.get("message") or ""
        # 影片 / 圖片貼文常無正文，但 captionText / OCR 有內容
        ocr = "\n".join(
            (m.get("ocrText") or "") for m in (item.get("media") or [])
            if m.get("ocrText")
        )
        caption = "\n".join(
            (m.get("captionText") or "") for m in (item.get("media") or [])
            if m.get("captionText")
        ) or item.get("captionText") or ""

        # 主文 = text + caption + ocr 的拼接，方便下游 LLM 一次拿到所有資訊
        full_text = "\n\n".join(filter(None, [raw_text, caption, ocr]))
        if not full_text.strip():
            continue

        ts_str = item.get("time") or item.get("timestamp") or ""
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            ts = datetime.now()

        media = (item.get("media") or [{}])[0]
        media_type = (media.get("__typename") or "Photo").lower()  # photo / video / text

        posts.append(RawPost(
            source="fb",
            kol=kol,
            post_id=str(item.get("postId") or item.get("id") or item.get("url", "")),
            url=item.get("url", page_url),
            timestamp=ts,
            text=full_text,
            media_type=media_type,
            extra={
                "likes": item.get("likes", 0),
                "comments": item.get("comments", 0),
                "shares": item.get("shares", 0),
                "raw_text": raw_text,
                "caption_text": caption,
                "ocr_text": ocr,
            },
        ))
    return posts
