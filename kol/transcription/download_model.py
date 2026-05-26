"""Download faster-whisper-large-v3-turbo into a local dir (no symlinks).

Avoids Windows symlink permission errors by using local_dir copy mode.
"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

from huggingface_hub import snapshot_download

REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
LOCAL_DIR = Path(r"C:\Users\stans\Projects\quant\kol\transcription\models\large-v3-turbo")
LOCAL_DIR.mkdir(parents=True, exist_ok=True)

print(f"Downloading {REPO} -> {LOCAL_DIR}", flush=True)
path = snapshot_download(
    repo_id=REPO,
    local_dir=str(LOCAL_DIR),
)
print(f"DONE path={path}", flush=True)
