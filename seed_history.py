"""
seed_history.py — Backfills 14 days of synthetic disk-usage history so the
growth forecast has something to work with on the very first demo run tonight.
Real usage, logged over multiple actual scans/days, replaces the need for this.

Usage: python3 seed_history.py [target_dir] [daily_growth_gb] [days_back]
  Defaults: target_dir=./demo_disk  daily_growth_gb=1.8  days_back=14

Note: the "days until threshold" number depends on your WHOLE disk's total
size (shutil.disk_usage reports the full mount, not just target_dir), so on
a large disk the ETA will look distant even with a decent growth rate — that
is realistic behavior. If you want a punchier number for the live demo,
increase daily_growth_gb, e.g.:
  python3 seed_history.py ./demo_disk 12
"""
import shutil
import sys
from pathlib import Path

from aegisstore import db, predictor


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("./demo_disk")
    daily_growth_gb = float(sys.argv[2]) if len(sys.argv) > 2 else 1.8
    days_back = int(sys.argv[3]) if len(sys.argv) > 3 else 14

    if not target.exists():
        print(f"{target} does not exist — run demo_setup.py first.")
        return

    db.init_db()
    total, used, _free = shutil.disk_usage(target)
    predictor.seed_synthetic_history(str(Path(target)), total, current_used_bytes=used,
                                      daily_growth_gb=daily_growth_gb, days_back=days_back)
    print(f"Seeded {days_back} days of synthetic growth history for {target} "
          f"({daily_growth_gb} GB/day, ending at today's real usage).")
    print("Now run: python3 -m aegisstore.cli scan", target)


if __name__ == "__main__":
    main()
