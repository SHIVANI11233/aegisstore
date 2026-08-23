"""
demo_setup.py — Creates a synthetic 'cluttered disk' so you can run and rehearse
the full AegisStore demo tonight without needing real old files lying around.

Usage: python3 demo_setup.py [target_dir]   (default: ./demo_disk)
"""
import os
import sys
import time
from pathlib import Path

BLOCK = os.urandom(1024 * 256)


def make_file(path: Path, size_bytes: int, age_days: float, content_seed: bytes = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    seed = content_seed or BLOCK
    with open(path, "wb") as f:
        written = 0
        while written < size_bytes:
            chunk = seed[: min(len(seed), size_bytes - written)]
            f.write(chunk)
            written += len(chunk)
    old_time = time.time() - age_days * 86400
    os.utime(path, (old_time, old_time))


def build_demo(target: Path):
    target.mkdir(parents=True, exist_ok=True)
    make_file(target / "active_project" / "current_work.db", 50 * 1024 * 1024, age_days=0.2)
    dup_seed = os.urandom(1024 * 256)
    make_file(target / "datasets" / "large_dataset.zip", 40 * 1024 * 1024, age_days=143, content_seed=dup_seed)
    make_file(target / "backups" / "large_dataset_copy.zip", 40 * 1024 * 1024, age_days=140, content_seed=dup_seed)
    make_file(target / "build" / "artifact_2025_03.tar", 15 * 1024 * 1024, age_days=187)
    make_file(target / "build" / "artifact_2025_04.tar", 12 * 1024 * 1024, age_days=175)
    make_file(target / "var_log" / "app.log.1", 5 * 1024 * 1024, age_days=95)
    make_file(target / "var_log" / "app.log.2", 4 * 1024 * 1024, age_days=120)
    make_file(target / "misc" / "maybe_needed.csv", 3 * 1024 * 1024, age_days=20)


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./demo_disk")
    print(f"Building demo clutter in {target.resolve()} ...")
    build_demo(target)
    print("Done. Try:")
    print(f"  python3 -m aegisstore.cli scan {target}")


if __name__ == "__main__":
    main()
