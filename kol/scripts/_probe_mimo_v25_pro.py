#!/usr/bin/env python3
"""Deep capability probe for mimo-v2.5-pro on Token Plan SGP endpoint."""
import json
import urllib.error
import urllib.request
from pathlib import Path

KEY = "tp-sxvpczf3k2f60xksb46llm7qsaqefqaoncv5i26g5vxgylmo"
BASE = "https://token-plan-sgp.xiaomimimo.com/v1"
MODEL = "mimo-v2.5-pro"
OUT = Path(__file__).with_name("_probe_mimo_v25_pro_report.json")


def call(payload: dict, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            return {"ok": True, "status": resp.status, "body": body, "json": json.loads(body)}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "body": e.read().decode()}


def chat(**extra) -> dict:
    payload = {
        "model": MODEL,
        "messages": extra.pop("messages", [{"role": "user", "content": "hi"}]),
        "max_tokens": extra.pop("max_tokens", 512),
        **extra,
    }
    return call(payload, timeout=extra.get("timeout", 120))


report: dict = {"model": MODEL, "base_url": BASE, "tests": {}}

# 1) basic identity
report["tests"]["identity"] = chat(messages=[{"role": "user", "content": "列出你的模型名稱、參數量、上下文長度、支援語言、是否支援推理/工具/多模態。用繁中 bullet list。"}])

# 2) coding
report["tests"]["coding_python"] = chat(
    messages=[{"role": "user", "content": "寫一個 Python function：給定 OHLCV list，算 20 日 SMA 與 RSI(14)，只回 code。"}],
    max_tokens=1024,
)

# 3) structured extraction (finance)
report["tests"]["finance_extract"] = chat(
    messages=[{"role": "user", "content": "從這段文字抽取 JSON：NVDA 看多，目標價 180，因 AI 需求強。欄位 ticker,direction,target,reason"}],
    max_tokens=512,
)

# 4) tools / function calling - force tool use
report["tests"]["tool_call_forced"] = chat(
    messages=[{"role": "user", "content": "台北現在天氣如何？"}],
    tools=[{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather by city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}, "unit": {"type": "string", "enum": ["c", "f"]}},
                "required": ["city"],
            },
        },
    }],
    tool_choice={"type": "function", "function": {"name": "get_weather"}},
    max_tokens=256,
)

# 5) parallel tools
report["tests"]["tool_choice_auto"] = chat(
    messages=[{"role": "user", "content": "查台北天氣，並計算 123*456"}],
    tools=[
        {"type": "function", "function": {"name": "get_weather", "description": "weather", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}},
        {"type": "function", "function": {"name": "calculator", "description": "calc", "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}}},
    ],
    tool_choice="auto",
    max_tokens=512,
)

# 6) json mode
report["tests"]["json_mode"] = chat(
    messages=[
        {"role": "system", "content": "You output JSON only."},
        {"role": "user", "content": "回傳 {\"model\":\"...\",\"skills\":[\"a\",\"b\"]}"},
    ],
    response_format={"type": "json_object"},
    max_tokens=256,
)

# 7) stream
report["tests"]["stream"] = chat(stream=True, max_tokens=128)

# 8) thinking variants
for name, extra in [
    ("thinking_enabled", {"thinking": {"type": "enabled"}}),
    ("thinking_disabled", {"thinking": {"type": "disabled"}}),
    ("enable_thinking_true", {"enable_thinking": True}),
    ("enable_thinking_false", {"enable_thinking": False}),
]:
    report["tests"][name] = chat(messages=[{"role": "user", "content": "17*23=? 只回答數字"}], max_tokens=64, **extra)

# 9) vision / image url
report["tests"]["vision_url"] = chat(
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "描述這張圖"},
            {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/320px-Cat03.jpg"}},
        ],
    }],
    max_tokens=256,
)

# 10) vision base64 small red pixel
import base64
red_png = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
        "0000000c4944415408d763f8ffff3f0005fe02fe0dc69238ef0000000049454e44ae426082"
    )
).decode()
report["tests"]["vision_base64"] = chat(
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "這張圖是什麼顏色？"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{red_png}"}},
        ],
    }],
    max_tokens=128,
)

# 11) web search param guesses
for name, extra in [
    ("web_search", {"web_search": True}),
    ("enable_search", {"enable_search": True}),
    ("search", {"search": True}),
    ("tools_web", {"tools": [{"type": "web_search"}]}),
]:
    report["tests"][f"search_probe_{name}"] = chat(
        messages=[{"role": "user", "content": "今天台積電股價多少？"}],
        max_tokens=256,
        **extra,
    )

# 12) max_tokens upper bound quick probe
for mt in [8192, 16384, 32768, 131072]:
    r = chat(messages=[{"role": "user", "content": "repeat word hello"}], max_tokens=mt)
    report["tests"][f"max_tokens_{mt}"] = {
        "status": r.get("status"),
        "error": None if r.get("ok") else r.get("body", "")[:300],
        "usage": r.get("json", {}).get("usage") if r.get("ok") else None,
        "finish_reason": r.get("json", {}).get("choices", [{}])[0].get("finish_reason") if r.get("ok") else None,
    }

# 13) temperature / top_p bounds
report["tests"]["temperature_0"] = chat(messages=[{"role": "user", "content": "say hi"}], temperature=0, max_tokens=32)
report["tests"]["temperature_1.5"] = chat(messages=[{"role": "user", "content": "say hi"}], temperature=1.5, max_tokens=32)

# 14) multi-turn + system
report["tests"]["multi_turn"] = chat(
    messages=[
        {"role": "system", "content": "你是量化研究助手，回答簡短。"},
        {"role": "user", "content": "什麼是 IC？"},
        {"role": "assistant", "content": "IC 是 Information Coefficient，衡量因子預測力。"},
        {"role": "user", "content": "那 IR 呢？"},
    ],
    max_tokens=256,
)

# 15) compare with v2-pro on same prompt
same = [{"role": "user", "content": "用 3 句話比較 DRAM 與 NAND 週期差異。"}]
for m in ["mimo-v2.5-pro", "mimo-v2-pro", "mimo-v2-omni", "mimo-v2.5"]:
    r = call({"model": m, "messages": same, "max_tokens": 256})
    j = r.get("json") or {}
    msg = (j.get("choices") or [{}])[0].get("message", {})
    report.setdefault("model_compare", {})[m] = {
        "status": r.get("status"),
        "content": msg.get("content", "")[:500],
        "usage": j.get("usage"),
    }

# slim report for readability
slim = {"model": MODEL, "base_url": BASE, "tests": {}}
for k, v in report["tests"].items():
    if not isinstance(v, dict):
        slim["tests"][k] = v
        continue
    entry = {"status": v.get("status"), "ok": v.get("ok")}
    if v.get("ok"):
        j = v["json"]
        msg = j["choices"][0]["message"]
        entry["content"] = (msg.get("content") or "")[:800]
        entry["reasoning"] = (msg.get("reasoning_content") or "")[:400]
        entry["tool_calls"] = msg.get("tool_calls")
        entry["usage"] = j.get("usage")
        entry["finish_reason"] = j["choices"][0].get("finish_reason")
        if v.get("body", "").startswith("data:"):
            entry["stream_sample"] = v["body"][:400]
    else:
        entry["error"] = v.get("body", "")[:500]
    slim["tests"][k] = entry

slim["model_compare"] = report.get("model_compare", {})
OUT.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"saved {OUT}")
