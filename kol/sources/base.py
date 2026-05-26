"""
sources/base.py — 多源 KOL 資料的統一型別

每個資料源（FB / Threads / Podcast / YouTube）都產出 RawPost 序列，
再交給 extract/llm.py 做 LLM 抽取，最後與 banini 同 schema 入庫。
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RawPost:
    """從任一平台抓下來的原始貼文 / 段落。"""
    source: str           # "fb" | "threads" | "podcast" | "youtube"
    kol: str              # KOL 識別字串，e.g. "gooaye", "uncle_us_notes"
    post_id: str          # 平台內唯一 ID
    url: str              # 原始連結
    timestamp: datetime   # 發文 / 錄製時間
    text: str             # 文字內容（podcast/YT 為 transcript chunk）
    media_type: str = "text"  # text | audio | video
    extra: dict[str, Any] = field(default_factory=dict)  # 平台特定欄位

    def uid(self) -> str:
        """跨平台唯一 ID = source:kol:hash(post_id)"""
        h = hashlib.md5(f"{self.source}:{self.kol}:{self.post_id}".encode()).hexdigest()[:12]
        return f"{self.source}_{self.kol}_{h}"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        d["uid"] = self.uid()
        return d
