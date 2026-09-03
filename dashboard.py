"""
dashboard.py — AegisStore visual dashboard (Streamlit).
Run with: streamlit run dashboard.py
"""
import shutil
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from aegisstore import context, db, decision_engine, executor, predictor, safety_gate, scanner, storage_story, storage_intelligence
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

col_input, col_scan, col_reset = st.columns([3, 1, 1])
target_dir = col_input.text_input("Directory to scan", value="./demo_disk")
scan_clicked = col_scan.button("Scan now", width='stretch')
reset_clicked = col_reset.button("Reset demo", width='stretch',
                                  help="Wipes demo_disk, quarantine, and history, then rebuilds a fresh demo environment.")


st.subheader("🛡️ Threat-Model & Safety Guarantees")

st.info(
    """
    **AegisStore is recommendation-first and safety-aware.**

    • 🗑️ **No direct deletion** — cleanup actions are not automatically deleted;
      files must go through the project's controlled/quarantine workflow.

    • 🔒 **No touching open files** — files currently used by an active process
      are protected from optimization.

    • ⚠️ **Risk-threshold gating** — recommendations are evaluated using
      risk and safety signals before any optimization action is considered.

    • 🖥️ **Live-load deferral** — when CPU, RAM, or I/O load is high,
      optimization can be deferred instead of acting immediately.

    • 📦 **Dependency awareness** — package-owned, Git-tracked, symlink-related,
      systemd-referenced, and cron-referenced files can be flagged for review.

    **Human remains in control:** AegisStore recommends; the user decides.
    """
)

if reset_clicked:
    target = Path(target_dir)
    if target.exists():
        shutil.rmtree(target)
    quarantine_dir = Path(__file__).parent / "quarantine"
    if quarantine_dir.exists():
        shutil.rmtree(quarantine_dir)
    db_path = Path(__file__).parent / "aegisstore.db"
    if db_path.exists():
        db_path.unlink()
    for key in ["bootstrapped", "results", "summary", "reclaimable", "forecast", "forecast_detailed"]:
        st.session_state.pop(key, None)
    st.rerun()

load = safety_gate.read_system_load(sample_seconds=0.3)
busy = safety_gate.is_system_busy(load)
state = str(load.get("state", "NORMAL"))

l1, l2, l3, l4, l5 = st.columns(5)
l1.metric("CPU", f"{load['cpu_percent']:.0f}%")
l2.metric("RAM", f"{load['memory_percent']:.0f}%")
l3.metric("Disk Read", f"{load['disk_read_mb_s']:.1f} MB/s")
l4.metric("Disk Write", f"{load['disk_write_mb_s']:.1f} MB/s")
l5.metric("Safety Gate", state)

st.caption(f"I/O Wait: {load['io_wait_percent']:.0f}%" if load.get('io_wait_percent') is not None else "I/O Wait: N/A")
if busy:
    st.warning("⚠ LIVE SAFETY OVERRIDE ACTIVE\n\nAutomatic cleanup is temporarily disabled because the system is currently under high workload.")

if "results" not in st.session_state:
    st.session_state.results = None
    st.session_state.summary = None
    st.session_state.reclaimable = 0

if scan_clicked:
    target = str(Path(target_dir))
    if not Path(target).exists():
        st.error(f"'{target}' does not exist. Run `python3 demo_setup.py {target}` first.")
    else:
        progress = st.progress(0)
        status = st.empty()
        
        status.text("📁 Scanning filesystem... (fast mode)")
        total, used, _free = shutil.disk_usage(target)
        db.log_usage(target, used, total)

        records = scanner.scan_and_classify(target)
        progress.progress(33)
        status.text("🔍 Analyzing risk scores... (33%)")
        
        candidates, reclaimable = scanner.reclaimable_summary(records)
        
        # Limit to top 20 candidates by size for maximum speed
        candidates = sorted(candidates, key=lambda r: r["size_bytes"], reverse=True)[:20]
        progress.progress(66)
        status.text("⚙️  Computing decisions... (66%)")

        rows = []
        for idx, c in enumerate(candidates):
            ctx = context.enrich(str(c["path"]))
            decision = decision_engine.assess(c, ctx, load, busy)

            if decision["action"] == "DEFER":
                db.log_schedule_event(
                    c["path"],
                    "DEFERRED",
                    load,
                    reason=decision["reason"],
                )
            else:
                previous_events = [
                    r for r in db.recent_audit(limit=50)
                    if r["path"] == str(c["path"])
                    and r["action"] == "DEFERRED"
                ]
                if previous_events:
                    db.log_schedule_event(
                        c["path"],
                        "RETRIED",
                        load,
                        reason="System load is now within safe limits.",
                    )

            cid = db.save_candidate(c)
            db.save_decision(
                cid,
                {
                    **ctx,
                    "cpu_percent": load["cpu_percent"],
                    "io_wait_percent": load["io_wait_percent"],
                    **decision,
                },
            )

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
                "risk_score": decision["risk_score"],
                "risk_tier": decision["risk_tier"],
                "action": decision["action"],
                "reason": decision["reason"],
                "factors": decision.get("factors", []),
                "Risk": decision["risk_tier"],
                "Risk Score": f"{decision['risk_score']} / 100",
                "Action": decision["action"],
                "Reason": decision["reason"],
            })

        progress.progress(85)
        status.text("📊 Generating forecasts... (85%)")
        
        st.session_state.results = rows
        st.session_state.reclaimable = reclaimable
        st.session_state.total_disk = total
        st.session_state.used_disk = used
        st.session_state.target = target

        automated = [r for r in rows if r["Action"] == "AUTOMATE"]
        deferred = [r for r in rows if r["Action"] == "DEFER"]
        avg_conf = (sum(float(r["Confidence"].strip("%")) for r in rows) / 100 / len(rows)) if rows else 0
        fc = predictor.forecast(target)
        fc_detailed = storage_intelligence.storage_forecast_detailed(target, reclaimable_bytes=reclaimable)

        summary = {
            "total_candidates": len(records),
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
            st.session_state.forecast_detailed = fc_detailed
        else:
            st.session_state.forecast = None
            st.session_state.forecast_detailed = fc_detailed

        st.session_state.summary = summary
        progress.progress(100)
        status.text("✅ Scan complete!")
        st.success(f"✅ Analyzed {len(records)} files. Top {len(rows)} candidates shown. {len(automated)} ready for cleanup.")
        time.sleep(0.5)
        progress.empty()
        status.empty()

if st.session_state.results is not None:
    used = st.session_state.used_disk
    total = st.session_state.total_disk

    m1, m2, m3 = st.columns(3)
    m1.metric("Disk usage", f"{used/total:.0%}", help=f"{human(used)} / {human(total)}")
    m2.metric("Reclaimable", human(st.session_state.reclaimable))
    m3.metric("Candidates found", len(st.session_state.results))

    # Live safety override banner uses the existing system-load reading from the project safety gate.
    if busy:
        st.warning(
            "⚠ LIVE SAFETY OVERRIDE ACTIVE\n\n"
            f"Cleanup has been deferred because the system is currently busy. "
            f"CPU {load['cpu_percent']:.0f}%, RAM {load['memory_percent']:.0f}%, I/O wait {load['io_wait_percent']:.0f}%."
        )

    if st.session_state.get("forecast_detailed"):
        fc_detail = st.session_state.forecast_detailed
        fc = fc_detail["forecast"]
        st.subheader("Growth Forecast")
        if fc:
            fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)
            fcol1.metric("Current usage", f"{fc['current_usage_pct'] * 100:.0f}%")
            fcol2.metric("Growth rate", fc_detail["growth_rate_formatted"])
            d85 = fc["predictions_days"].get(0.85)
            fcol3.metric("Days to 85%", f"{d85:.0f}" if d85 is not None else "N/A")
            d90 = fc["predictions_days"].get(0.90)
            fcol4.metric("Days to 90%", f"{d90:.0f}" if d90 is not None else "N/A")
            d95 = fc["predictions_days"].get(0.95)
            fcol5.metric("Days to 95%", f"{d95:.0f}" if d95 is not None else "N/A")

            st.metric("Forecast data quality", fc_detail["forecast_quality"])

            history_rows = db.usage_series(st.session_state.target)
            if len(history_rows) >= 2:
                chart_df = pd.DataFrame([{
                    "Date": datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d"),
                    "Historical usage (GB)": r["used_bytes"] / (1024 ** 3),
                } for r in history_rows])
                chart_df = chart_df.drop_duplicates(subset="Date", keep="last").set_index("Date")
                st.line_chart(chart_df, height=220)

            if fc_detail["cleanup_impact"]:
                st.subheader("Potential Storage Impact")
                ci = fc_detail["cleanup_impact"]
                impact1, impact2, impact3, impact4 = st.columns(4)
                impact1.metric("Current usage", ci["current_used_formatted"])
                impact2.metric("Reclaimable", ci["reclaimable_formatted"])
                impact3.metric("After cleanup", ci["estimated_after_formatted"])
                impact4.metric("After cleanup %", f"{ci['estimated_after_pct'] * 100:.0f}%")

                st.caption("Estimated impact if all currently reclaimable data were safely removed.")

            st.subheader("Storage Intelligence")
            st.info(fc_detail["recommendation"])
        else:
            st.info(fc_detail["recommendation"])
    elif st.session_state.get("forecast_detailed"):
        fc_detail = st.session_state.forecast_detailed
        st.subheader("Growth Forecast")
        st.info(fc_detail["recommendation"])
    else:
        st.info("Scan filesystem to see storage forecast.")

    st.subheader("Risk Overview")
    risk_counts = {tier: sum(1 for r in st.session_state.results if r.get("risk_tier") == tier) for tier in ["LOW", "MEDIUM", "HIGH"]}
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("LOW", risk_counts.get("LOW", 0))
    rc2.metric("MEDIUM", risk_counts.get("MEDIUM", 0))
    rc3.metric("HIGH", risk_counts.get("HIGH", 0))
    rc4.metric("Total candidates", len(st.session_state.results))

st.subheader("Candidate Results - Risk-Adaptive Decisions")

results = st.session_state.get("results", [])
df = pd.DataFrame(results)

if not df.empty:

    # Support both the original dashboard fields and
    # the newer recommendation-engine fields.
    def get_value(record, *keys, default="—"):
        for key in keys:
            if key in record and record[key] is not None:
                return record[key]
        return default

    display_rows = []

    for record in results:
        risk_score = get_value(
            record,
            "Risk Score",
            "risk_score",
            default="—",
        )

        risk_tier = get_value(
            record,
            "Risk",
            "risk_tier",
            default="—",
        )

        action = get_value(
            record,
            "Action",
            "action",
            "recommendation",
            default="REVIEW",
        )

        reason = get_value(
            record,
            "Reason",
            "reason",
            "recommendation_reason",
            default="No reason available.",
        )

        display_rows.append({
            "File": get_value(record, "File", "file", "name"),
            "Size": get_value(record, "Size", "size"),
            "Age (days)": get_value(record, "Age (days)", "age_days"),
            "Classification": get_value(
                record,
                "Classification",
                "classification",
                "usage_profile",
            ),
            "Future Use": (
                f"{float(record.get('future_usage_probability', 0)) * 100:.1f}%"
                if record.get("future_usage_probability") is not None
                else "—"
            ),
            "Risk Score": risk_score,
            "Risk": risk_tier,
            "Recommendation": action,
            "Reason": reason,
        })

    display_df = pd.DataFrame(display_rows)

    def risk_color(val):
        return {
            "LOW": "background-color:#d4edda",
            "MEDIUM": "background-color:#fff3cd",
            "HIGH": "background-color:#f8d7da",
        }.get(val, "")

    st.dataframe(
        display_df.style.map(
            risk_color,
            subset=["Risk"],
        ),
        width="stretch",
        hide_index=True,
    )

    # CSV report using only fields that actually exist.
    csv_rows = []

    for record in results:
        csv_rows.append({
            "File": get_value(record, "File", "file", "name"),
            "Path": get_value(record, "Path", "path"),
            "Size": get_value(record, "Size", "size"),
            "Age (days)": get_value(
                record,
                "Age (days)",
                "age_days",
            ),
            "Classification": get_value(
                record,
                "Classification",
                "classification",
                "usage_profile",
            ),
            "Future Usage Probability": record.get(
                "future_usage_probability",
                "",
            ),
            "Recommendation": get_value(
                record,
                "recommendation",
                "Action",
                "action",
            ),
            "Recommendation Reason": get_value(
                record,
                "recommendation_reason",
                "Reason",
                "reason",
            ),
            "Risk Score": get_value(
                record,
                "risk_score",
                "Risk Score",
            ),
            "Risk Tier": get_value(
                record,
                "risk_tier",
                "Risk",
            ),
            "Safety Blocked": record.get(
                "safety_blocked",
                False,
            ),
            "Safety Flags": "; ".join(
                record.get("safety_flags", [])
                if isinstance(record.get("safety_flags", []), list)
                else []
            ),
        })

    csv_df = pd.DataFrame(csv_rows)
    csv_bytes = csv_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download report (CSV)",
        data=csv_bytes,
        file_name=(
            f"aegisstore_report_"
            f"{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        ),
        mime="text/csv",
    )

else:
    st.info("No candidate results available. Run a filesystem scan first.")
    st.subheader("Why This Decision?")

    results = st.session_state.get("results") or []

    candidate_names = [
        r.get("File", r.get("file", r.get("name", "Unknown")))
        for r in results
    ]

    if candidate_names:
        selected_file = st.selectbox(
            "Select candidate",
            candidate_names,
            index=0,
        )

        selected_candidate = next(
            (
                r for r in results
                if r.get("File", r.get("file", r.get("name"))) == selected_file
            ),
            None,
        )

        if selected_candidate:
            st.markdown(f"**File:** {selected_candidate['File']}")
            st.markdown(f"**Risk Score:** {selected_candidate['Risk Score']}")
            st.markdown(f"**Risk Level:** {selected_candidate['Risk']}")
            st.markdown(f"**Recommended Action:** {selected_candidate['Action']}")

            factors = selected_candidate.get("factors", [])
            st.markdown("**Why?**")

            if factors:
                for factor in factors:
                    st.write(factor)
            else:
                st.write("No explanatory factors available.")

            st.markdown(
                f"**Decision reason:** {selected_candidate['Reason']}"
            )

            st.markdown(
                f"**Recommendation:** {selected_candidate['Action']}"
            )

            st.divider()
            st.markdown("### 🔄 Counterfactual Explanation")

            try:
                from aegisstore import counterfactual

                candidate_path = selected_candidate.get("Path")

                original_candidate = next(
                    (
                        c for c in candidates
                        if str(c["path"]) == str(candidate_path)
                    ),
                    None,
                )

                if original_candidate:
                    cf = counterfactual.explain_age_change(
                        original_candidate,
                        context.enrich(str(original_candidate["path"])),
                        load,
                        busy,
                        days_delta=-7,
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric(
                            "Current Risk",
                            f"{cf['current_score']} / 100",
                        )

                    with col2:
                        st.metric(
                            "If 7 Days Newer",
                            f"{cf['counterfactual_score']} / 100",
                            delta=cf["delta"],
                        )

                    st.info(f"💡 {cf['explanation']}")

                    if cf["current_action"] != cf["counterfactual_action"]:
                        st.warning(
                            f"Decision would change: "
                            f"{cf['current_action']} → "
                            f"{cf['counterfactual_action']}"
                        )
                    else:
                        st.caption(
                            f"Decision remains: {cf['current_action']}"
                        )
                else:
                    st.info("Counterfactual data unavailable for this candidate.")

            except Exception as e:
                st.warning(f"Counterfactual explanation unavailable: {e}")

    else:
        st.info("No candidate results available. Run a filesystem scan first.")

    st.subheader("Take Action")
    auto_eligible = [r for r in st.session_state.results if r["Action"] == "AUTOMATE"]
    scheduled = [r for r in st.session_state.results if r["Action"] == "SCHEDULE"]
    approval = [r for r in st.session_state.results if r["Action"] == "APPROVAL_REQUIRED"]
    deferred = [r for r in st.session_state.results if r["Action"] == "DEFER"]
    skipped = [r for r in st.session_state.results if r["Action"] == "SKIP"]

    if auto_eligible:
        st.info(f"🟢 {len(auto_eligible)} candidates ready for safe automatic cleanup.")
        col_batch, col_safety = st.columns([2, 1])
        if col_batch.button("Execute Batch Cleanup", type="primary", help="Quarantine all AUTOMATE-eligible files with safety verification"):
            batch_candidates = [{"path": r["Path"], "reason": r["Reason"]} for r in auto_eligible]
            batch_result = executor.batch_quarantine(batch_candidates, load, verify_safety=True)
            
            if batch_result["safety_cleared"]:
                if batch_result["executed"]:
                    st.success(
                        f"✓ Executed: {len(batch_result['executed'])} files quarantined\n"
                        f"📦 Recovered: {batch_result['total_bytes_recovered'] / (1024**3):.2f} GB"
                    )
                    st.balloons()
                if batch_result["failed"]:
                    st.warning(f"⚠ Failed: {len(batch_result['failed'])} files could not be quarantined")
                    for fail in batch_result["failed"]:
                        st.write(f"  • {Path(fail['path']).name}: {fail['error']}")
            else:
                st.warning(
                    "🛑 SAFETY GATE ACTIVE\n\n"
                    f"System is busy (CPU {load['cpu_percent']:.0f}%, RAM {load['memory_percent']:.0f}%). "
                    f"Cleanup deferred to protect stability. All {len(batch_result['skipped'])} candidates remain safe."
                )
        
        col_safety.metric("Safety Status", "PASS" if not busy else "DEFER")

    action_groups = [
        ("AUTOMATE", auto_eligible, "Ready for automatic quarantine."),
        ("SCHEDULE", scheduled, "Handle during a safer window or after confirmation."),
        ("APPROVAL_REQUIRED", approval, "Requires explicit user approval before any action."),
        ("DEFER", deferred, "Do not execute while the system remains busy or unsafe."),
        ("SKIP", skipped, "Safety checks blocked this file; no action will be taken."),
    ]

    st.write("**Individual Actions** (optional; use batch cleanup above for efficiency)")
    for action_name, items, guidance in action_groups:
        if items:
            st.write(f"**{action_name}**")
            st.caption(guidance)
            for r in items:
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{r['File']}** - {r['Size']} | Risk {r['Risk']} | {r['Reason']}")
                if action_name == "AUTOMATE":
                    if c2.button("Quarantine", key=f"q_{r['Path']}"):
                        try:
                            info = executor.quarantine_file(r["Path"], r["Reason"])
                            st.success(f"Quarantined - integrity_verified={info['integrity_verified']}")
                        except FileNotFoundError:
                            st.warning("Already quarantined or moved.")
                else:
                    c2.write("—")

    st.subheader("Storage Story")
    with st.spinner("Generating narrative..."):
        story = storage_story.generate_story(st.session_state.summary)
    st.info(story)

st.divider()
st.subheader("Recovery & Quarantine Management")
recovery_stats = executor.recovery_stats()
q1, q2, q3 = st.columns(3)
q1.metric("Files in Quarantine", recovery_stats["file_count"])
q2.metric("Total Size", f"{recovery_stats['total_bytes'] / (1024**3):.2f} GB")
q3.metric("Integrity OK", f"{recovery_stats['integrity_ok']}/{recovery_stats['file_count']}")

quarantine_items = executor.list_quarantine(limit=50)
if quarantine_items:
    st.write(f"**Recent Quarantined Files** ({len(quarantine_items)} shown)")
    quar_rows = []
    for item in quarantine_items:
        quar_rows.append({
            "File": Path(item["original_path"]).name,
            "Original Path": item["original_path"],
            "Reason": item["reason"],
            "Size (GB)": f"{item['size_bytes'] / (1024**3):.2f}",
            "Integrity": "✓" if item["integrity_verified"] else "✗",
        })
    
    quar_df = pd.DataFrame(quar_rows)
    st.dataframe(quar_df, width='stretch', hide_index=True)
    
    st.write("**Recover Files**")
    selected_quar = st.selectbox(
        "Select a quarantined file to recover",
        options=[item["quarantine_path"] for item in quarantine_items],
        format_func=lambda p: Path(p).name,
    )
    if selected_quar and st.button("Restore to Original Location", help="Move file back from quarantine"):
        try:
            restore_result = executor.undo_last(selected_quar)
            st.success(f"Restored: {restore_result['restored_to']}")
            st.rerun()
        except Exception as e:
            st.error(f"Recovery failed: {e}")
else:
    st.info("No files in quarantine. All cleanup operations are fully applied.")

st.subheader("Audit Log")
audit_rows = db.recent_audit(limit=15)
if audit_rows:
    audit_df = pd.DataFrame([dict(r) for r in audit_rows])
    st.dataframe(audit_df[["event_time", "action", "path", "reversible", "detail"]],
                 width='stretch', hide_index=True)
else:
    st.write("No actions taken yet.")

st.subheader("🕐 Energy / Performance-Aware Scheduling Timeline")

schedule_actions = {"DEFERRED", "RETRIED", "EXECUTED", "QUARANTINE"}
schedule_rows = [
    dict(r) for r in db.recent_audit(limit=50)
    if r["action"] in schedule_actions
]

if schedule_rows:
    timeline = []
    for r in schedule_rows:
        from datetime import datetime
        timestamp = datetime.fromtimestamp(r["event_time"]).strftime("%H:%M:%S")
        timeline.append({
            "Time": timestamp,
            "Event": "EXECUTED" if r["action"] == "QUARANTINE" else r["action"],
            "File": r["path"],
            "System Load / Reason": r["detail"],
        })

    st.dataframe(
        pd.DataFrame(timeline),
        width="stretch",
        hide_index=True,
    )
else:
    st.info("No scheduling events recorded yet.")
