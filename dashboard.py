"""
dashboard.py — AegisStore visual dashboard (Streamlit).
Run with: streamlit run dashboard.py
"""
import shutil
import time
from pathlib import Path

import pandas as pd
import streamlit as st

from aegisstore import context, db, decision_engine, executor, predictor, safety_gate, scanner, storage_story
from demo_setup import build_demo

st.set_page_config(page_title="AegisStore", page_icon="AegisStore", layout="wide")
db.init_db()

DEFAULT_TARGET = Path("./demo_disk")


def ensure_demo_environment(target: Path):
    """Self-bootstraps demo data + growth history on first load, so a deployed
    link works immediately for a judge with zero setup - no terminal needed."""
    if not target.exists():
        build_demo(target)
    total, used, _free = shutil.disk_usage(target)
    db.log_usage(str(target), used, total)
    if predictor.forecast(str(target), min_points=3) is None:
        predictor.seed_synthetic_history(str(target), total, current_used_bytes=used,
                                          daily_growth_gb=1.8, days_back=14)


if "bootstrapped" not in st.session_state:
    ensure_demo_environment(DEFAULT_TARGET)
    st.session_state.bootstrapped = True


def human(n_bytes: float) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n_bytes < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} PB"


st.title("AegisStore")
st.caption("AI understands what can be optimized. AegisStore decides whether it is safe to act.")

col_input, col_scan = st.columns([3, 1])
target_dir = col_input.text_input("Directory to scan", value="./demo_disk")
scan_clicked = col_scan.button("Scan now", width='stretch')

load = safety_gate.read_system_load(sample_seconds=0.3)
busy = safety_gate.is_system_busy(load)

l1, l2, l3 = st.columns(3)
l1.metric("CPU", f"{load['cpu_percent']:.0f}%")
l2.metric("I/O wait", f"{load['io_wait_percent']:.0f}%")
l3.metric("Safety Gate", "BUSY" if busy else "Normal")

if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.summary = None
    st.session_state.reclaimable = 0

if scan_clicked:
    target = str(Path(target_dir))
    if not Path(target).exists():
        st.error(f"'{target}' does not exist. Run `python3 demo_setup.py {target}` first.")
    else:
        with st.spinner("Scanning filesystem..."):
            total, used, _free = shutil.disk_usage(target)
            db.log_usage(target, used, total)

            records = scanner.scan_and_classify(target)
            candidates, reclaimable = scanner.reclaimable_summary(records)

            rows = []
            for c in sorted(candidates, key=lambda r: r["size_bytes"], reverse=True)[:20]:
                ctx = context.enrich(str(c["path"]))
                decision = decision_engine.assess(c, ctx, load, busy)
                cid = db.save_candidate(c)
                db.save_decision(cid, {**ctx, "cpu_percent": load["cpu_percent"],
                                        "io_wait_percent": load["io_wait_percent"], **decision})
                rows.append({
                    "File": c["path"].name,
                    "Path": str(c["path"]),
                    "Size": human(c["size_bytes"]),
                    "Age (days)": c["age_days"],
                    "Classification": c["classification"],
                    "Confidence": f"{c['confidence']:.0%}",
                    "Active": ctx["active_process"],
                    "Pkg-owned": ctx["package_owned"],
                    "Git-tracked": ctx["git_tracked"],
                    "Risk": decision["risk_tier"],
                    "Action": decision["action"],
                    "Reason": decision["reason"],
                })

            st.session_state.results = rows
            st.session_state.reclaimable = reclaimable
            st.session_state.total_disk = total
            st.session_state.used_disk = used
            st.session_state.target = target

            automated = [r for r in rows if r["Action"] == "AUTOMATE"]
            deferred = [r for r in rows if r["Action"] == "DEFER"]
            avg_conf = (sum(float(r["Confidence"].strip("%")) for r in rows) / 100 / len(rows)) if rows else 0
            fc = predictor.forecast(target)

            summary = {
                "total_candidates": len(rows),
                "total_reclaimable_gb": reclaimable / (1024 ** 3),
                "top_reason": "cold/redundant data",
                "deferred_count": len(deferred),
                "automated_count": len(automated),
                "avg_confidence": avg_conf,
            }
            if fc:
                summary["growth_rate_gb_per_day"] = fc["growth_rate_gb_per_day"]
                summary["days_to_90pct"] = fc["predictions_days"].get(0.90)
                st.session_state.forecast = fc
            else:
                st.session_state.forecast = None

            st.session_state.summary = summary

if st.session_state.results is not None:
    used = st.session_state.used_disk
    total = st.session_state.total_disk

    m1, m2, m3 = st.columns(3)
    m1.metric("Disk usage", f"{used/total:.0%}", help=f"{human(used)} / {human(total)}")
    m2.metric("Reclaimable", human(st.session_state.reclaimable))
    m3.metric("Candidates found", len(st.session_state.results))

    if st.session_state.forecast:
        fc = st.session_state.forecast
        st.subheader("Growth Forecast")
        fcol1, fcol2, fcol3 = st.columns(3)
        fcol1.metric("Growth rate", f"{fc['growth_rate_gb_per_day']:.2f} GB/day")
        d90 = fc["predictions_days"].get(0.90)
        fcol2.metric("Days to 90% capacity", f"{d90:.0f}" if d90 else "N/A")
        d95 = fc["predictions_days"].get(0.95)
        fcol3.metric("Days to 95% capacity", f"{d95:.0f}" if d95 else "N/A")

    st.subheader("Scan Results - Risk-Adaptive Decisions")
    df = pd.DataFrame(st.session_state.results)

    def risk_color(val):
        return {"LOW": "background-color:#d4edda", "MEDIUM": "background-color:#fff3cd",
                "HIGH": "background-color:#f8d7da"}.get(val, "")

    st.dataframe(
        df.drop(columns=["Path"]).style.map(risk_color, subset=["Risk"]),
        width='stretch', hide_index=True,
    )

    st.subheader("Take Action")
    low_risk = [r for r in st.session_state.results if r["Action"] == "AUTOMATE"]
    if low_risk:
        st.write(f"{len(low_risk)} candidate(s) are LOW risk and eligible for automatic quarantine:")
        for r in low_risk:
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{r['File']}** - {r['Size']}, {r['Reason']}")
            if c2.button("Quarantine", key=f"q_{r['Path']}"):
                try:
                    info = executor.quarantine_file(r["Path"], r["Reason"])
                    st.success(f"Quarantined - integrity_verified={info['integrity_verified']}")
                except FileNotFoundError:
                    st.warning("Already quarantined or moved.")
    else:
        st.write("No auto-eligible (LOW risk) candidates from this scan.")

    st.subheader("Storage Story")
    with st.spinner("Generating narrative..."):
        story = storage_story.generate_story(st.session_state.summary)
    st.info(story)

st.divider()
st.subheader("Audit Log")
audit_rows = db.recent_audit(limit=15)
if audit_rows:
    audit_df = pd.DataFrame([dict(r) for r in audit_rows])
    st.dataframe(audit_df[["event_time", "action", "path", "reversible", "detail"]],
                 width='stretch', hide_index=True)
else:
    st.write("No actions taken yet.")
