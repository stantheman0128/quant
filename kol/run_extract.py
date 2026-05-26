"""
run_extract.py — 對 RawPost JSONL 跑 LLM 抽取，輸出 ExtractedPost JSONL

關鍵優化：
  - Anthropic prompt caching：SYSTEM_PROMPT 加 cache_control，省 90% input tokens
  - Resumable：已處理的 post uid 會跳過
  - Per-source 統計：抽出 targets 數、has_market_content 比例
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))
load_dotenv()

ROOT = Path(__file__).resolve().parent

SYSTEM_PROMPT = """你是台股/美股市場分析助手，從財經 KOL 貼文 / podcast 逐字稿中
抽取結構化的「市場觀點」資料。我們不假設 KOL 是反指標還是正指標 ——
僅忠實記錄她/他「對什麼資產表達了什麼動作 / 觀點」，方向預測由下游模型決定。

## 抽取規則

1. **僅抽取明確提到的標的**：個股代碼、公司名、ETF、原物料、指數
   - 模糊指涉（「電子股」、「科技股」）只在沒有具體標的時才用，type='產業'
   - 暱稱必須轉正式名稱（「股王」→ 上下文判斷）
   - **嚴禁腦補**：KOL 沒提就不要加

2. **動作分類 action**：
   - 已執行：買入 / 加碼 / 賣出 / 停損 / 放空 / All in
   - 持有狀態：持有 / 被套 / 抱緊
   - 觀點性質：看多 / 看空 / 看好 / 看衰 / 觀察
   - 計畫性：計畫買入 / 計畫賣出 / 計畫加碼

3. **觀點方向 view**：
   - bullish：認為會漲 / 看好 / 買入 / 加碼 / 持有看好
   - bearish：認為會跌 / 看衰 / 賣出 / 放空
   - holding_long：持有多單但無強烈方向觀點（可能套牢）
   - exit：停損 / 認賠 / 出清
   - neutral：純資訊分享或討論，無明確方向

4. **conviction 強度**：
   - high：All in、重押、明確篤定（「絕對」「必漲」「梭哈」）
   - mid：明確動作 / 觀點但無強烈措辭
   - low：「考慮」「可能」「觀察中」「猶豫」「或許」

5. **market 區分**：'TW' (台股) | 'US' (美股) | 'CRYPTO' | 'OTHER'
   依標的所在市場，不是 KOL 國籍

6. **code_hint**：若你有把握知道代碼（如 0050、AAPL、5274），填入；否則 null

7. **reasoning**：一句話描述 KOL 的理由（KOL 自己給的，不是你補的）

## 輸出 JSON 格式

{
  "has_market_content": true/false,
  "targets": [
    {
      "name": "信驊",
      "code_hint": "5274",
      "market": "TW",
      "type": "個股 | ETF | 指數 | 原物料 | 產業",
      "action": "買入",
      "view": "bullish",
      "conviction": "mid",
      "reasoning": "認為 AI 伺服器需求強勁"
    }
  ],
  "summary": "一句話摘要（適合推送）"
}

若內容與市場標的完全無關（純閒聊、生活、廣告、感謝信），
has_market_content=false，targets=[]，summary 給原因（例如「廣告：New Balance」）。
"""


def call_anthropic(text: str, model: str, ctx: str) -> dict:
    """直接呼叫 Anthropic API（用 Messages API + cache_control）。"""
    import anthropic
    client = anthropic.Anthropic()
    user_msg = f"{ctx}\n\n以下是內容：\n\n{text}" if ctx else text
    msg = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.2,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = msg.content[0].text
    # extract JSON
    fence = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw)
    j = fence.group(1) if fence else (re.search(r"\{[\s\S]*\}", raw) or [None])[0]
    if not j:
        raise ValueError(f"no JSON in response: {raw[:200]}")
    return json.loads(j)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="RawPost JSONL 路徑（可多個用逗號分隔）")
    p.add_argument("--output", required=True, help="ExtractedPost JSONL 輸出路徑")
    p.add_argument("--model", default="claude-haiku-4-5-20251001")
    p.add_argument("--limit", type=int, default=None, help="只跑前 N 筆（debug 用）")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("請先在 .env 設 ANTHROPIC_API_KEY")

    inputs = [Path(p) for p in args.input.split(",")]
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 已處理的 uid（resume）
    done_uids = set()
    if out_path.exists():
        for line in open(out_path, encoding="utf-8"):
            try:
                done_uids.add(json.loads(line)["uid"])
            except (json.JSONDecodeError, KeyError):
                pass
        print(f"[resume] {len(done_uids)} 筆已處理，將跳過")

    fout = open(out_path, "a", encoding="utf-8")
    total, skipped, ok, errs = 0, 0, 0, 0
    cache_hits, cache_creates, input_tokens, output_tokens = 0, 0, 0, 0
    t0 = time.time()

    for inp in inputs:
        print(f"\n=== {inp.name} ===")
        for line in open(inp, encoding="utf-8"):
            post = json.loads(line)
            total += 1
            if args.limit and total > args.limit:
                break
            if post["uid"] in done_uids:
                skipped += 1
                continue
            ctx = f"來源：{post['source']}/{post['kol']}（{post['timestamp'][:10]}）"
            try:
                ext = call_anthropic(post["text"], args.model, ctx)
                rec = {**post, "extraction": ext}
                fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fout.flush()
                ok += 1
                tag = "★" if ext.get("targets") else "·"
                summary = ext.get("summary", "")[:50]
                print(f"  {tag} {post['uid'][:20]:20} targets={len(ext.get('targets', [])):>2} | {summary}")
            except Exception as e:
                errs += 1
                print(f"  ✗ {post['uid'][:20]:20} ERROR: {e}")
                continue

    elapsed = time.time() - t0
    print(f"\n[done] total={total} ok={ok} skipped={skipped} errs={errs} in {elapsed:.1f}s")
    fout.close()


if __name__ == "__main__":
    main()
