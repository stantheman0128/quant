"""Transcribe a local audio file with faster-whisper large-v3-turbo.

Prints one progress line per segment so a Monitor wrapper can stream status.
Outputs:
  - segments.json  (raw structured segments, UTF-8)
  - transcript.txt (human-readable, [MM:SS] text per line)
"""
import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

from faster_whisper import WhisperModel

AUDIO = Path(r"C:\Users\stans\Projects\quant\AI 2026 AI1_.mp3")
OUT_DIR = Path(r"C:\Users\stans\Projects\quant\kol\transcription")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = r"C:\Users\stans\Projects\quant\kol\transcription\models\large-v3-turbo"
COMPUTE = "int8"
LANG = "zh"

print(f"LOAD model={MODEL_NAME} compute={COMPUTE}", flush=True)
t0 = time.time()
model = WhisperModel(MODEL_NAME, device="cpu", compute_type=COMPUTE)
print(f"LOADED in {time.time()-t0:.1f}s", flush=True)

print(f"TRANSCRIBE {AUDIO.name} size={AUDIO.stat().st_size/1e6:.1f}MB", flush=True)
t0 = time.time()

segments_iter, info = model.transcribe(
    str(AUDIO),
    language=LANG,
    beam_size=5,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500},
    condition_on_previous_text=True,
)

print(f"INFO duration={info.duration:.1f}s lang={info.language} prob={info.language_probability:.2f}", flush=True)

total_sec = info.duration
all_segments = []
last_print = 0.0
for seg in segments_iter:
    all_segments.append({
        "start": seg.start,
        "end": seg.end,
        "text": seg.text.strip(),
    })
    # Progress: every ~30s of audio covered, emit a line
    if seg.end - last_print >= 30.0 or seg.end >= total_sec - 1:
        pct = 100.0 * seg.end / total_sec
        elapsed = time.time() - t0
        eta = elapsed / max(seg.end, 1.0) * (total_sec - seg.end)
        print(f"PROG {pct:5.1f}%  audio={seg.end/60:.1f}min  elapsed={elapsed/60:.1f}min  eta={eta/60:.1f}min  last={seg.text.strip()[:40]}", flush=True)
        last_print = seg.end

print(f"DONE segments={len(all_segments)} elapsed={(time.time()-t0)/60:.1f}min", flush=True)

# Persist
(OUT_DIR / "segments.json").write_text(
    json.dumps({"language": info.language, "duration": info.duration, "segments": all_segments}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

def fmt(s):
    h = int(s // 3600); m = int((s % 3600) // 60); ss = int(s % 60)
    return f"{h:02d}:{m:02d}:{ss:02d}" if h else f"{m:02d}:{ss:02d}"

with (OUT_DIR / "transcript.txt").open("w", encoding="utf-8") as f:
    for s in all_segments:
        f.write(f"[{fmt(s['start'])}] {s['text']}\n")

print(f"WROTE segments.json ({len(all_segments)} segments) and transcript.txt", flush=True)
