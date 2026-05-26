"""Benchmark: GPU (int8) + BatchedInferencePipeline on the same MP3.

Outputs alongside the original:
  - segments_fast.json
  - transcript_fast.txt
  - Prints total elapsed at the end
"""
import io
import json
import os
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)

# Make bundled CUDA DLLs from pip packages loadable on Windows
if sys.platform == "win32":
    import nvidia.cublas, nvidia.cudnn
    dll_dirs = []
    for pkg in (nvidia.cublas, nvidia.cudnn):
        for root in pkg.__path__:
            bin_dir = Path(root) / "bin"
            if bin_dir.exists():
                dll_dirs.append(str(bin_dir))
                os.add_dll_directory(str(bin_dir))
    # Also prepend to PATH so C extensions find transitive deps
    os.environ["PATH"] = os.pathsep.join(dll_dirs) + os.pathsep + os.environ.get("PATH", "")

from faster_whisper import WhisperModel, BatchedInferencePipeline

AUDIO = Path(r"C:\Users\stans\Projects\quant\AI 2026 AI1_.mp3")
OUT_DIR = Path(r"C:\Users\stans\Projects\quant\kol\transcription")
MODEL = r"C:\Users\stans\Projects\quant\kol\transcription\models\large-v3-turbo"

print("LOAD model + BatchedInferencePipeline (GPU int8)", flush=True)
t0 = time.time()
base = WhisperModel(MODEL, device="cuda", compute_type="int8")
pipe = BatchedInferencePipeline(model=base)
print(f"LOADED in {time.time()-t0:.1f}s", flush=True)

print(f"TRANSCRIBE {AUDIO.name}", flush=True)
t0 = time.time()
segments_iter, info = pipe.transcribe(
    str(AUDIO),
    language="zh",
    batch_size=16,
    vad_filter=True,
    vad_parameters={"min_silence_duration_ms": 500},
)
print(f"INFO duration={info.duration:.1f}s lang={info.language}", flush=True)

total_sec = info.duration
all_segments = []
last_print = 0.0
for seg in segments_iter:
    all_segments.append({"start": seg.start, "end": seg.end, "text": seg.text.strip()})
    if seg.end - last_print >= 60.0 or seg.end >= total_sec - 1:
        pct = 100.0 * seg.end / total_sec
        elapsed = time.time() - t0
        eta = elapsed / max(seg.end, 1.0) * (total_sec - seg.end)
        print(f"PROG {pct:5.1f}%  audio={seg.end/60:.1f}min  elapsed={elapsed/60:.2f}min  eta={eta/60:.1f}min", flush=True)
        last_print = seg.end

elapsed = time.time() - t0
speed = total_sec / elapsed
print(f"DONE segments={len(all_segments)} elapsed={elapsed/60:.2f}min  speed={speed:.1f}x realtime", flush=True)

(OUT_DIR / "segments_fast.json").write_text(
    json.dumps({"language": info.language, "duration": info.duration, "segments": all_segments}, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

def fmt(s):
    h = int(s // 3600); m = int((s % 3600) // 60); ss = int(s % 60)
    return f"{h:02d}:{m:02d}:{ss:02d}" if h else f"{m:02d}:{ss:02d}"

with (OUT_DIR / "transcript_fast.txt").open("w", encoding="utf-8") as f:
    for s in all_segments:
        f.write(f"[{fmt(s['start'])}] {s['text']}\n")

print(f"WROTE segments_fast.json and transcript_fast.txt", flush=True)
