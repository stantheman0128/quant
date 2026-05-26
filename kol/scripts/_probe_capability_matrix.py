#!/usr/bin/env python3
"""Compare unique capabilities across MiMo Token Plan models."""
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

KEY = "tp-sxvpczf3k2f60xksb46llm7qsaqefqaoncv5i26g5vxgylmo"
BASE = "https://token-plan-sgp.xiaomimimo.com/v1"
OUT = Path(__file__).with_name("_probe_capability_matrix.json")

IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/120px-Cat03.jpg"


def post(payload, wait=3):
    time.sleep(wait)
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode()
            if payload.get("stream"):
                return {"ok": True, "code": 200, "stream": body[:300]}
            data = json.loads(body)
            msg = data["choices"][0]["message"]
            return {
                "ok": True,
                "code": 200,
                "content": (msg.get("content") or "")[:300],
                "reasoning": (msg.get("reasoning_content") or "")[:150],
                "tool_calls": msg.get("tool_calls"),
                "audio": bool(msg.get("audio")),
                "usage": data.get("usage"),
            }
    except urllib.error.HTTPError as e:
        return {"ok": False, "code": e.code, "error": e.read().decode()[:500]}


report = {}

# vision: pro vs v2.5 vs omni
for model in ["mimo-v2.5-pro", "mimo-v2-pro", "mimo-v2.5", "mimo-v2-omni"]:
    report[f"vision_{model}"] = post({
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "用一句話描述圖片"},
                {"type": "image_url", "image_url": {"url": IMAGE}},
            ],
        }],
        "max_tokens": 128,
    })

# TTS models
report["tts_v2"] = post({
    "model": "mimo-v2-tts",
    "messages": [
        {"role": "user", "content": "請用台灣腔念：今天台股大盤創新高。"},
        {"role": "assistant", "content": "好的，我來為您播報。"},
    ],
    "max_tokens": 256,
})

report["tts_v25"] = post({
    "model": "mimo-v2.5-tts",
    "messages": [
        {"role": "user", "content": "請用興奮語氣念：NVDA 創新高！"},
        {"role": "assistant", "content": "沒問題！"},
    ],
    "max_tokens": 256,
})

report["tts_voiceclone"] = post({
    "model": "mimo-v2.5-tts-voiceclone",
    "messages": [
        {"role": "user", "content": "clone test"},
        {"role": "assistant", "content": "test"},
    ],
    "max_tokens": 128,
})

report["tts_voicedesign"] = post({
    "model": "mimo-v2.5-tts-voicedesign",
    "messages": [{"role": "user", "content": "設計一個沉穩男聲播報財經新聞"}],
    "max_tokens": 128,
})

# tools on v2.5 (not just pro)
report["tools_v25"] = post({
    "model": "mimo-v2.5",
    "messages": [{"role": "user", "content": "查台北天氣"}],
    "tools": [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        },
    }],
    "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
    "max_tokens": 128,
})

OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
