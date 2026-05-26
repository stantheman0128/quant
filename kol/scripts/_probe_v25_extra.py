import json
import time
import urllib.error
import urllib.request
from pathlib import Path

KEY = "tp-sxvpczf3k2f60xksb46llm7qsaqefqaoncv5i26g5vxgylmo"
BASE = "https://token-plan-sgp.xiaomimimo.com/v1"
MODEL = "mimo-v2.5-pro"
OUT = Path(__file__).with_name("_probe_v25_extra.json")


def post(payload, timeout=120):
    time.sleep(4)
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            if payload.get("stream"):
                return resp.status, body
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


results = {}

code, data = post({
    "model": MODEL,
    "messages": [{"role": "user", "content": "台北天氣"}],
    "tools": [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "weather",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]},
        },
    }],
    "tool_choice": {"type": "function", "function": {"name": "get_weather"}},
    "max_tokens": 128,
})
results["tools_forced"] = {
    "code": code,
    "tool_calls": data.get("choices", [{}])[0].get("message", {}).get("tool_calls") if code == 200 else data[:300],
}

code, data = post({"model": MODEL, "messages": [{"role": "user", "content": "hi"}], "stream": True, "max_tokens": 32})
results["stream"] = {"code": code, "sample": data[:250] if isinstance(data, str) else "json"}

code, data = post({
    "model": MODEL,
    "messages": [{"role": "system", "content": "json only"}, {"role": "user", "content": 'return {"a":1}'}],
    "response_format": {"type": "json_object"},
    "max_tokens": 64,
})
results["json_mode"] = {
    "code": code,
    "content": data.get("choices", [{}])[0].get("message", {}).get("content") if code == 200 else data[:300],
}

code, data = post({
    "model": MODEL,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "describe"},
            {"type": "image_url", "image_url": {"url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/120px-Cat03.jpg"}},
        ],
    }],
    "max_tokens": 64,
})
results["vision"] = {
    "code": code,
    "content": data.get("choices", [{}])[0].get("message", {}).get("content") if code == 200 else data[:400],
}

for param in ["web_search", "enable_search", "search"]:
    code, data = post({"model": MODEL, "messages": [{"role": "user", "content": "今天 NVIDIA 股價"}], param: True, "max_tokens": 128})
    if code == 200:
        msg = data.get("choices", [{}])[0].get("message", {})
        results[f"search_{param}"] = {"code": code, "content": (msg.get("content") or "")[:300], "usage": data.get("usage")}
    else:
        results[f"search_{param}"] = {"code": code, "error": data[:300]}

code, data = post({
    "model": MODEL,
    "messages": [{"role": "user", "content": "17*23=? only number"}],
    "thinking": {"type": "disabled"},
    "max_tokens": 32,
})
if code == 200:
    msg = data.get("choices", [{}])[0].get("message", {})
    results["thinking_disabled"] = {"code": code, "content": msg.get("content"), "reasoning": msg.get("reasoning_content"), "usage": data.get("usage")}
else:
    results["thinking_disabled"] = {"code": code, "error": data[:300]}

OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
