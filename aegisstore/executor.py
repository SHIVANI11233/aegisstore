"""
executor.py — Safe & Explainable Execution (Pillar 4).
Nothing is hard-deleted. Files move to a quarantine folder first, with a JSON
sidecar recording where they came from, so every action is reversible.
"""
import hashlib
import json
import shutil
import time
from pathlib import Path

from . import db

QUARANTINE_DIR = Path(__file__).parent.parent / "quarantine"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def quarantine_file(path: str, reason: str) -> dict:
    """Moves a file into quarantine and logs enough metadata to undo the move and verify integrity."""
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(f"{path} does not exist")

    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    before_hash = _sha256(src)
    ts = int(time.time())
    dest = QUARANTINE_DIR / f"{ts}__{src.name}"

    shutil.move(str(src), str(dest))
    after_hash = _sha256(dest)
    integrity_ok = before_hash == after_hash

    sidecar = dest.with_suffix(dest.suffix + ".meta.json")
    meta = {
        "original_path": str(src),
        "quarantine_path": str(dest),
        "timestamp": ts,
        "reason": reason,
        "sha256": after_hash,
        "integrity_verified": integrity_ok,
    }
    sidecar.write_text(json.dumps(meta, indent=2))

    db.log_action(src, "QUARANTINE", reason, quarantine_path=dest, reversible=True)
    return {**meta, "recovered_bytes": dest.stat().st_size}


def undo_last(quarantine_path: str) -> dict:
    """Moves a quarantined file back to its original location."""
    dest = Path(quarantine_path)
    sidecar = dest.with_suffix(dest.suffix + ".meta.json")
    if not sidecar.exists():
        raise FileNotFoundError("No metadata found for this quarantine entry — cannot safely undo.")
    meta = json.loads(sidecar.read_text())
    original = Path(meta["original_path"])
    original.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(dest), str(original))
    sidecar.unlink(missing_ok=True)
    db.log_action(original, "UNDO", "Restored from quarantine", quarantine_path=dest, reversible=False)
    return {"restored_to": str(original)}
