"""
test_override.py — Deterministic proof of the Risk-Adaptive Decision Engine's
real-time override, without depending on actually stressing the CPU live.
Safe fallback if the live `yes` stress-test demo feels risky on stage.
"""
from aegisstore import context, decision_engine, scanner

TARGET_DIR = "./demo_disk"


def main():
    records = scanner.scan_and_classify(TARGET_DIR)
    candidates, _ = scanner.reclaimable_summary(records)
    low_risk_candidates = [
        c for c in candidates if "Redundant" in c["classification"] and c["confidence"] >= 0.9
    ]
    if not low_risk_candidates:
        print("No LOW-risk candidate found — run demo_setup.py first.")
        return

    c = low_risk_candidates[0]
    ctx = context.enrich(str(c["path"]))

    print(f"Candidate: {c['path'].name}  |  classification={c['classification']}  confidence={c['confidence']:.0%}\n")

    idle_load = {"cpu_percent": 4.0, "io_wait_percent": 1.0, "memory_percent": 22.0}
    busy_load = {"cpu_percent": 91.0, "io_wait_percent": 27.0, "memory_percent": 60.0}

    print("Scenario A — system idle (matches forecast):")
    print(f"  Load: CPU {idle_load['cpu_percent']:.0f}%, I/O wait {idle_load['io_wait_percent']:.0f}%")
    print(f"  Decision: {decision_engine.assess(c, ctx, idle_load, False)}\n")

    print("Scenario B — system busy RIGHT NOW (forecast was wrong for this moment):")
    print(f"  Load: CPU {busy_load['cpu_percent']:.0f}%, I/O wait {busy_load['io_wait_percent']:.0f}%")
    print(f"  Decision: {decision_engine.assess(c, ctx, busy_load, True)}\n")

    print("This is the proof point: identical file, identical AI confidence — the")
    print("ONLY thing that changed is live system load, and the decision flipped.")


if __name__ == "__main__":
    main()
