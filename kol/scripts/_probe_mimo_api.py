#!/usr/bin/env python3
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

KEY = "tp-sxvpczf3k2f60xksb46llm7qsaqefqaoncv5i26g5vxgylmo"
BASE = "https://token-plan-sgp.xiaomimimo.com/v1"
OUT = Path(__file__).with_name("_probe_mimo_api_report.json")


def req(method: str, path: str, payload: dict | None = None) -> tuple[int, str]:
    headers = {"Authorization": f"Bearer {KEY}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def chat(model: str, **extra) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "用一句話回答：你是什麼模型？"}],
        "max_tokens": 256,
        **extra,
    }
    t0 = time.time()
    code, body = req("POST", "/chat/completions", payload)
    result = {"http_code": code, "elapsed": round(time.time() - t0, 2)}
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        result["raw"] = body[:1000]
        return result
    if code != 200:
        result["error"] = data
        return result
    msg = data["choices"][0]["message"]
    result.update({
        "content": msg.get("content", ""),
        "reasoning": msg.get("reasoning_content", ""),
        "usage": data.get("usage", {}),
        "finish_reason": data["choices"][0].get("finish_reason"),
    })
    return result


def main() -> None:
    report: dict = {"base_url": BASE, "key_prefix": KEY[:8] + "..."}

    code, body = req("GET", "/models")
    report["models_list"] = {"http_code": code, "body": json.loads(body) if code == 200 else body}

    model_ids = [m["id"] for m in report["models_list"]["body"].get("data", [])]
    report["chat_tests"] = {m: chat(m) for m in model_ids}

    report["pro_feature_tests"] = {
        "stream": chat("mimo-v2-pro", stream=True),
        "tools": chat(
            "mimo-v2-pro",
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "get weather",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }],
            tool_choice="auto",
        ),
        "json_mode": chat("mimo-v2-pro", response_format={"type": "json_object"}),
        "long_output_4k": chat("mimo-v2-pro", max_tokens=4096, messages=[
            {"role": "user", "content": "用繁體中文寫 800 字分析台股記憶體族群。"}
        ]),
    }

    report["other_endpoints"] = {}
    for path in ["/embeddings", "/audio/speech", "/audio/transcriptions"]:
        c, b = req("GET", path)
        report["other_endpoints"][path] = {"http_code": c, "body": b[:500]}

    # TTS probe
    report["tts_test"] = chat("mimo-v2-tts", messages=[
        {"role": "user", "content": "你好，這是一段語音合成測試。"}
    ])

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
