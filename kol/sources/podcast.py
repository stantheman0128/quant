"""
sources/podcast.py — Podcast RSS → episode list → mp3 download → transcript chunks

設計：
  - parse_feed(): RSS XML → 結構化 episode list (Episode dataclass)
  - download_episode(): mp3 → 本地檔
  - transcribe_episode(): 呼叫 Whisper (faster-whisper) 產 segments
  - chunk_segments(): 把 segments 分組成 ~5min 的文字塊（給 LLM）
  - episode_to_posts(): Episode → list[RawPost] (每個 chunk 一筆)
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

from .base import RawPost

NS = {"itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd"}


@dataclass
class Episode:
    ep_id: str
    title: str
    pub_date: datetime
    duration_sec: int | None
    audio_url: str

    def safe_filename(self) -> str:
        return f"{self.ep_id}.mp3"


def parse_feed(feed_path: Path) -> list[Episode]:
    """RSS XML → Episode list（按時間新到舊）。"""
    root = ET.parse(feed_path).getroot()
    items = root.findall(".//item")
    episodes = []
    for it in items:
        title = (it.find("title").text or "").strip()
        pub = parsedate_to_datetime(it.find("pubDate").text)
        enc = it.find("enclosure")
        if enc is None or "url" not in enc.attrib:
            continue
        audio_url = enc.attrib["url"]
        # 從 title 提 EP 編號（e.g. "EP654 | 🌵"）
        ep_id = title.split("|")[0].strip().replace(" ", "_") or audio_url.rsplit("/", 1)[-1].split(".")[0]

        dur = it.find("itunes:duration", NS)
        dur_sec = None
        if dur is not None and dur.text:
            try:
                dur_sec = int(dur.text)
            except ValueError:
                # HH:MM:SS format
                parts = [int(p) for p in dur.text.split(":")]
                dur_sec = sum(p * 60**i for i, p in enumerate(reversed(parts)))

        episodes.append(Episode(
            ep_id=ep_id, title=title, pub_date=pub,
            duration_sec=dur_sec, audio_url=audio_url,
        ))
    return episodes


def download_episode(ep: Episode, out_dir: Path) -> Path:
    """下載 mp3 到 out_dir/<ep_id>.mp3。已存在則跳過。"""
    out = out_dir / ep.safe_filename()
    if out.exists() and out.stat().st_size > 1024:
        return out
    print(f"[podcast] DOWNLOAD {ep.ep_id} ({ep.duration_sec or '?'}s) → {out.name}")
    r = requests.get(ep.audio_url, stream=True, timeout=60)
    r.raise_for_status()
    with open(out, "wb") as f:
        for chunk in r.iter_content(chunk_size=64 * 1024):
            f.write(chunk)
    return out


def transcribe_episode(
    mp3_path: Path,
    model_path: str,
    out_dir: Path,
    compute: str = "int8",
    lang: str = "zh",
) -> list[dict]:
    """呼叫 faster-whisper 轉錄 → segments JSON。已存在則跳過。"""
    out_json = out_dir / f"{mp3_path.stem}.segments.json"
    if out_json.exists():
        with open(out_json, encoding="utf-8") as f:
            return json.load(f)["segments"]

    from faster_whisper import WhisperModel
    print(f"[podcast] TRANSCRIBE {mp3_path.name} (compute={compute})")
    model = WhisperModel(model_path, device="cpu", compute_type=compute)
    segs_iter, info = model.transcribe(
        str(mp3_path), language=lang, beam_size=5,
        vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
    )
    segments = [
        {"start": s.start, "end": s.end, "text": s.text}
        for s in segs_iter
    ]
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"duration": info.duration, "language": info.language, "segments": segments},
                  f, ensure_ascii=False)
    print(f"[podcast] DONE → {out_json.name} ({len(segments)} segments)")
    return segments


def chunk_segments(segments: list[dict], chunk_sec: int = 300) -> list[dict]:
    """把 segments 分組成每塊 ~chunk_sec 秒。
    回傳 [{start, end, text}, ...]
    """
    chunks = []
    cur_text = []
    cur_start = None
    cur_end = None
    for s in segments:
        if cur_start is None:
            cur_start = s["start"]
        cur_end = s["end"]
        cur_text.append(s["text"].strip())
        if cur_end - cur_start >= chunk_sec:
            chunks.append({"start": cur_start, "end": cur_end, "text": " ".join(cur_text)})
            cur_text = []
            cur_start = None
    if cur_text:
        chunks.append({"start": cur_start or 0, "end": cur_end or 0, "text": " ".join(cur_text)})
    return chunks


def episode_to_posts(ep: Episode, kol: str, chunks: list[dict]) -> list[RawPost]:
    posts = []
    for i, c in enumerate(chunks):
        posts.append(RawPost(
            source="podcast",
            kol=kol,
            post_id=f"{ep.ep_id}_chunk{i:03d}",
            url=ep.audio_url + f"#t={int(c['start'])}",
            timestamp=ep.pub_date,
            text=c["text"],
            media_type="audio",
            extra={"ep_id": ep.ep_id, "ep_title": ep.title,
                   "chunk_idx": i, "chunk_start": c["start"], "chunk_end": c["end"]},
        ))
    return posts
