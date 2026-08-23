"""
executor.py — Safe & Explainable Execution (Pillar 4).
Nothing is hard-deleted. Files move to a quarantine folder first, with a JSON
sidecar recording where they came from, so every action is reversible.
Supports single quarantine, batch execution, and recovery management.
"""
import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Optional

from . import db, safety_gate

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


def batch_quarantine(candidates: list[dict], load: dict, verify_safety: bool = True) -> dict:
    """
    Execute batch quarantine of multiple candidates with safety verification.
    
    Args:
        candidates: List of candidate dicts with 'path' and 'reason' keys
        load: Current system load dict (from safety_gate.read_system_load)
        verify_safety: If True, re-check system safety before execution
    
    Returns:
        {
            "executed": [{path, size_bytes, quarantine_path}],
            "failed": [{path, error}],
            "skipped": [{path, reason}],
            "total_bytes_recovered": int,
            "safety_cleared": bool,
        }
    """
    results = {"executed": [], "failed": [], "skipped": [], "total_bytes_recovered": 0, "safety_cleared": False}
    
    if verify_safety:
        if safety_gate.is_system_busy(load):
            results["skipped"] = [{"path": c.get("path"), "reason": "System is busy; cleanup deferred"} for c in candidates]
            results["safety_cleared"] = False
            return results
        results["safety_cleared"] = True
    
    for candidate in candidates:
        path_str = candidate.get("path")
        reason = candidate.get("reason", "Batch cleanup")
        
        if not path_str or not Path(path_str).exists():
            results["failed"].append({"path": path_str, "error": "Path does not exist or is invalid"})
            continue
        
        try:
            info = quarantine_file(path_str, reason)
            results["executed"].append({
                "path": path_str,
                "size_bytes": info["recovered_bytes"],
                "quarantine_path": info["quarantine_path"],
            })
            results["total_bytes_recovered"] += info["recovered_bytes"]
        except Exception as e:
            results["failed"].append({"path": path_str, "error": str(e)})
    
    return results


def list_quarantine(limit: int = 100) -> list[dict]:
    """
    List all quarantined files with their metadata.
    
    Returns:
        List of {quarantine_path, original_path, timestamp, reason, size_bytes, sha256, integrity_verified}
    """
    if not QUARANTINE_DIR.exists():
        return []
    
    items = []
    for meta_file in sorted(QUARANTINE_DIR.glob("*.meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
        try:
            meta = json.loads(meta_file.read_text())
            quarantine_path = Path(meta["quarantine_path"])
            size_bytes = quarantine_path.stat().st_size if quarantine_path.exists() else 0
            items.append({
                "quarantine_path": meta["quarantine_path"],
                "original_path": meta["original_path"],
                "timestamp": meta["timestamp"],
                "reason": meta["reason"],
                "size_bytes": size_bytes,
                "sha256": meta.get("sha256", "N/A"),
                "integrity_verified": meta.get("integrity_verified", False),
            })
        except Exception:
            pass
    
    return items


def recovery_stats() -> dict:
    """Calculate total bytes in quarantine and count of items."""
    if not QUARANTINE_DIR.exists():
        return {"total_bytes": 0, "file_count": 0, "integrity_ok": 0}
    
    total_bytes = 0
    integrity_ok = 0
    file_count = 0
    
    for meta_file in QUARANTINE_DIR.glob("*.meta.json"):
        try:
            meta = json.loads(meta_file.read_text())
            quarantine_path = Path(meta["quarantine_path"])
            if quarantine_path.exists():
                total_bytes += quarantine_path.stat().st_size
                if meta.get("integrity_verified"):
                    integrity_ok += 1
                file_count += 1
        except Exception:
            pass
    
    return {"total_bytes": total_bytes, "file_count": file_count, "integrity_ok": integrity_ok}

