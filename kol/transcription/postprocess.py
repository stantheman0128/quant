"""Post-process faster-whisper output.

Steps:
  1. Read segments.json (simplified Chinese)
  2. Convert to Traditional Chinese (Taiwan, with idiom mapping) via OpenCC s2twp
  3. Write:
     - segments_tw.json  (structured, with timestamps)
     - transcript_tw.txt (readable, [HH:MM:SS] line format)
     - transcript_tw.md  (markdown with clickable timestamps + every N segments merged into paragraphs)
"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

import opencc

BASE = Path(r"C:\Users\stans\Projects\quant\kol\transcription")
src = json.loads((BASE / "segments.json").read_text(encoding="utf-8"))

cc = opencc.OpenCC("s2twp")

def fmt(s):
    h = int(s // 3600); m = int((s % 3600) // 60); ss = int(s % 60)
    return f"{h:02d}:{m:02d}:{ss:02d}"

segs_tw = []
for s in src["segments"]:
    segs_tw.append({"start": s["start"], "end": s["end"], "text": cc.convert(s["text"])})

(BASE / "segments_tw.json").write_text(
    json.dumps({"language": src["language"], "duration": src["duration"], "segments": segs_tw}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

with (BASE / "transcript_tw.txt").open("w", encoding="utf-8") as f:
    for s in segs_tw:
        f.write(f"[{fmt(s['start'])}] {s['text']}\n")

# Also produce a "paragraph-merged" version: every ~30s into one block
merged = []
cur_start = None
cur_texts = []
BLOCK_SEC = 30.0
for s in segs_tw:
    if cur_start is None:
        cur_start = s["start"]
    cur_texts.append(s["text"])
    if s["end"] - cur_start >= BLOCK_SEC:
        merged.append((cur_start, " ".join(cur_texts)))
        cur_start = None
        cur_texts = []
if cur_texts:
    merged.append((cur_start, " ".join(cur_texts)))

with (BASE / "transcript_tw.md").open("w", encoding="utf-8") as f:
    f.write(f"# AI 2026 直播論壇 逐字稿（繁體）\n\n")
    f.write(f"- 音訊長度：{src['duration']/60:.1f} 分鐘\n")
    f.write(f"- 段落數：{len(segs_tw)}\n\n")
    for t, text in merged:
        f.write(f"## [{fmt(t)}]\n\n{text}\n\n")

print(f"WROTE segments_tw.json, transcript_tw.txt, transcript_tw.md (merged into {len(merged)} paragraphs)", flush=True)
print(f"Total traditional-chinese chars: {sum(len(s['text']) for s in segs_tw)}", flush=True)
