"""
scanner.py — Pillar 1 (part 1): Data Collection Layer.
Walks a target directory, collects size/atime/mtime, and groups duplicates by content hash.
"""
import hashlib
import os
import time
from pathlib import Path

COLD_DAYS_THRESHOLD = 30      # files untouched this long are "Cold"
HASH_CHUNK = 1024 * 1024      # hash in 1MB chunks so large files don't blow up memory


def _hash_file(path: Path, restore_atime: float = None, mtime: float = None) -> str:
    """Hashes file content. Reading a file updates its atime, which would corrupt
    the very 'last accessed' signal we rely on for classification — so we restore
    the original atime/mtime immediately after hashing."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(HASH_CHUNK):
                h.update(chunk)
        if restore_atime is not None and mtime is not None:
            try:
                os.utime(path, (restore_atime, mtime))
            except OSError:
                pass
        return h.hexdigest()
    except (PermissionError, FileNotFoundError, OSError):
        return ""


def scan_directory(root: str, skip_dirs=(".git", "node_modules", "__pycache__", ".venv")):
    """Returns a list of file records: path, size, atime, mtime, hash."""
    root = Path(root)
    records = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            try:
                st = fpath.stat()
            except (FileNotFoundError, PermissionError, OSError):
                continue
            records.append({
                "path": fpath,
                "size_bytes": st.st_size,
                "atime": st.st_atime,
                "mtime": st.st_mtime,
                "hash": _hash_file(fpath, restore_atime=st.st_atime, mtime=st.st_mtime) if st.st_size > 0 else "",
            })
    return records


def find_duplicates(records):
    """Groups records by hash; marks all but the first in each group as a duplicate of the first."""
    by_hash = {}
    for r in records:
        if not r["hash"]:
            continue
        by_hash.setdefault(r["hash"], []).append(r)

    for group in by_hash.values():
        if len(group) > 1:
            original = group[0]
            for dup in group[1:]:
                dup["duplicate_of"] = str(original["path"])
        for r in group:
            r.setdefault("duplicate_of", None)
    for r in records:
        r.setdefault("duplicate_of", None)
    return records


def classify(record):
    """Hot -> Warm -> Cold -> Redundant -> Potentially removable, with a simple confidence score."""
    now = time.time()
    age_days = (now - record["atime"]) / 86400
    is_duplicate = record["duplicate_of"] is not None

    if age_days < 7:
        label = "Hot"
        confidence = 0.95
    elif age_days < COLD_DAYS_THRESHOLD:
        label = "Warm"
        confidence = 0.8
    else:
        label = "Cold"
        confidence = 0.85

    if is_duplicate and age_days >= COLD_DAYS_THRESHOLD:
        label = "Cold + Redundant"
        confidence = min(0.97, 0.85 + 0.1)
    elif is_duplicate:
        label = "Redundant"
        confidence = 0.75

    record["classification"] = label
    record["confidence"] = round(confidence, 2)
    record["age_days"] = round(age_days, 1)
    record["last_accessed"] = record["atime"]
    return record


def scan_and_classify(root: str):
    records = scan_directory(root)
    records = find_duplicates(records)
    return [classify(r) for r in records]


def reclaimable_summary(records, min_age_days=COLD_DAYS_THRESHOLD):
    """Total bytes for anything Cold or Redundant — the 'potential recovery' headline number."""
    candidates = [r for r in records if "Cold" in r["classification"] or "Redundant" in r["classification"]]
    total = sum(r["size_bytes"] for r in candidates)
    return candidates, total
