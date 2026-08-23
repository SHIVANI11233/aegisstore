"""
cli.py — Ties every module together and runs the live demo flow end to end.
Usage:
    python -m aegisstore.cli scan <directory>
    python -m aegisstore.cli undo <quarantine_file_path>
    python -m aegisstore.cli audit
"""
import shutil
import sys

from . import context, db, decision_engine, executor, safety_gate, scanner, storage_story


def human(n_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} PB"


def run_scan(target_dir: str):
    db.init_db()
    print(f"\n=== AegisStore scan: {target_dir} ===\n")

    total, used, _free = shutil.disk_usage(target_dir)
    print(f"Disk usage: {used/total:.0%}  ({human(used)} / {human(total)})")
    db.log_usage(target_dir, used, total)

    print("\nScanning filesystem...")
    records = scanner.scan_and_classify(target_dir)
    candidates, reclaimable = scanner.reclaimable_summary(records)
    print(f"Found {len(records)} files. Potential reclaimable: {human(reclaimable)} across {len(candidates)} candidate(s).\n")

    if not candidates:
        print("No optimization candidates found. Try pointing at a directory with old/duplicate files.")
        return

    load = safety_gate.read_system_load()
    busy = safety_gate.is_system_busy(load)
    print(f"Current system load: CPU {load['cpu_percent']:.0f}%, I/O wait {load['io_wait_percent']:.0f}%  "
          f"-> {'BUSY (safety gate ACTIVE)' if busy else 'normal'}\n")

    results = []
    for c in sorted(candidates, key=lambda r: r["size_bytes"], reverse=True)[:15]:
        ctx = context.enrich(str(c["path"]))
        decision = decision_engine.assess(c, ctx, load, busy)

        cid = db.save_candidate(c)
        db.save_decision(cid, {**ctx, "cpu_percent": load["cpu_percent"],
                                "io_wait_percent": load["io_wait_percent"], **decision})

        print(f"- {c['path'].name}")
        print(f"    size={human(c['size_bytes'])}  age={c['age_days']}d  class={c['classification']}  "
              f"confidence={c['confidence']:.0%}  duplicate={'yes' if c['duplicate_of'] else 'no'}")
        print(f"    active_process={ctx['active_process']}  package_owned={ctx['package_owned']}  "
              f"git_tracked={ctx['git_tracked']}")
        print(f"    -> RISK: {decision['risk_tier']}  ACTION: {decision['action']}  ({decision['reason']})\n")

        if decision["action"] == "AUTOMATE":
            info = executor.quarantine_file(str(c["path"]), decision["reason"])
            print(f"    QUARANTINED -> {info['quarantine_path']}  integrity_verified={info['integrity_verified']}\n")

        results.append({**c, **decision})

    automated = [r for r in results if r["action"] == "AUTOMATE"]
    deferred = [r for r in results if r["action"] == "DEFER"]
    avg_conf = sum(r["confidence"] for r in results) / len(results)
    top_class = max(set(r["classification"] for r in results), key=lambda c: sum(1 for r in results if r["classification"] == c))

    summary = {
        "total_candidates": len(results),
        "total_reclaimable_gb": reclaimable / (1024 ** 3),
        "top_reason": f"{top_class.lower()} data",
        "deferred_count": len(deferred),
        "automated_count": len(automated),
        "avg_confidence": avg_conf,
    }

    print("=== Storage Story ===")
    print(storage_story.generate_story(summary))
    print()


def run_audit():
    db.init_db()
    rows = db.recent_audit()
    print("\n=== Recent AegisStore Actions ===")
    for r in rows:
        print(f"[{r['action']}] {r['path']}  reversible={bool(r['reversible'])}  detail={r['detail']}")
    print()


def run_undo(quarantine_path: str):
    db.init_db()
    result = executor.undo_last(quarantine_path)
    print(f"Restored: {result['restored_to']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "scan" and len(sys.argv) >= 3:
        run_scan(sys.argv[2])
    elif cmd == "audit":
        run_audit()
    elif cmd == "undo" and len(sys.argv) >= 3:
        run_undo(sys.argv[2])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
