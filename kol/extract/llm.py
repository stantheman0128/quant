"""
extract/llm.py — 把 banini-tracker 的 analyze.ts prompt 移植到 Python

關鍵差異：
  1. 不預設「反指標」框架 —— 改成中性「KOL 觀點 + 動作」抽取
  2. 方向交給後續 skill score 模型決定
  3. 同 schema 與 banini predictions：name, type, action, view, conviction, reasoning
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from openai import OpenAI


SYSTEM_PROMPT = """你是台股市場分析助手，從財經 KOL 的貼文 / 訪談 / podcast 逐字稿中
抽取結構化的「市場觀點」資料。我們不假設 KOL 是反指標還是正指標 ——
僅忠實記錄她/他「對什麼資產、做了什麼動作 / 表達什麼觀點」，方向預測由下游模型決定。

## 抽取規則

1. **僅抽取明確提到的標的**：個股代碼或公司名、ETF、原物料、指數。
   - 模糊指涉（「電子股」、「科技股」）只在沒有具體標的可抽時才用，type='產業'
   - 暱稱必須轉正式名稱（「股王」→ 上下文判斷是台積電 / 信驊 / etc）
   - **嚴禁腦補**：如 KOL 沒提就不要加

2. **動作分類**（her_action / his_action 都記成 action）：
   - 已執行：買入 / 加碼 / 賣出 / 停損 / 放空 / All in
   - 持有狀態：持有 / 被套 / 抱緊
   - 觀點性質：看多 / 看空 / 看好 / 看衰 / 觀察
   - 計畫性：計畫買入 / 計畫賣出 / 計畫加碼

3. **觀點方向 view**：根據 action 與語意，標記 KOL 對該資產的「直觀方向」
   - bullish：認為會漲 / 看好 / 買入 / 加碼 / 持有看好
   - bearish：認為會跌 / 看衰 / 賣出 / 放空
   - holding_long：持有多單但無強烈觀點（可能套牢）
   - exit：停損 / 認賠 / 出清

4. **conviction 強度**：
   - high：All in、重押、明確篤定（「絕對」「必漲」「梭哈」）
   - mid：明確動作但無強烈措辭
   - low：「考慮」「可能」「觀察中」「猶豫」

5. **reasoning**：一句話描述 KOL 的理由（KOL 自己給的，不是你補的）

## 輸出 JSON 格式

{
  "has_market_content": true/false,
  "targets": [
    {
      "name": "信驊",
      "code_hint": "5274",        // 若你有把握；否則 null
      "type": "個股 | ETF | 指數 | 原物料 | 產業",
      "action": "買入",
      "view": "bullish",
      "conviction": "high | mid | low",
      "reasoning": "認為 AI 伺服器需求強勁"
    }
  ],
  "summary": "一句話摘要這段內容"
}

若該段內容與市場標的完全無關（純閒聊、生活、廣告），has_market_content=false，
targets=[]，僅給 summary。"""


@dataclass
class ExtractedTarget:
    name: str
    code_hint: str | None
    type: str
    action: str
    view: str
    conviction: str
    reasoning: str


@dataclass
class Extraction:
    has_market_content: bool
    targets: list[ExtractedTarget]
    summary: str
    raw_json: str  # 原始 LLM 回應，方便 debug


def _build_client() -> OpenAI:
    """根據環境變數選 LLM provider。預設用 Anthropic 相容端點。"""
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.anthropic.com/v1/")
    if not api_key:
        raise RuntimeError("請設 LLM_API_KEY 或 ANTHROPIC_API_KEY")
    return OpenAI(api_key=api_key, base_url=base_url)


def extract(text: str, model: str | None = None, context: str = "") -> Extraction:
    """對單段文字做抽取。context 可填「來源 KOL / 時間」之類資訊。"""
    model = model or os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
    client = _build_client()
    user_msg = f"{context}\n\n以下是內容：\n\n{text}" if context else text
    res = client.chat.completions.create(
        model=model, temperature=0.2,
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": user_msg}],
    )
    content = res.choices[0].message.content or ""
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", content)
    raw = fence.group(1) if fence else (re.search(r"\{[\s\S]*\}", content) or [None])[0]
    if not raw:
        raise ValueError(f"LLM 回應找不到 JSON: {content[:300]}")
    try:
        d = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON parse error: {e}; raw={raw[:300]}") from e
    targets = [ExtractedTarget(**{**t, "code_hint": t.get("code_hint")}) for t in d.get("targets", [])]
    return Extraction(
        has_market_content=bool(d.get("has_market_content")),
        targets=targets,
        summary=d.get("summary", ""),
        raw_json=raw,
    )
