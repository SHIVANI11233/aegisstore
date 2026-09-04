"""
decision_engine.py — The Risk-Adaptive Decision Engine (core innovation).

Combines: data importance, AI confidence, context signals, and real-time system
workload into ONE numeric risk score, risk tier, action, and explainable factors.
The output stays backward-compatible with the older {risk_tier, action, reason}
shape while adding the stronger 0–100 scoring model required by the demo.
"""

LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"


def assess(candidate: dict, ctx: dict, load: dict, system_busy: bool) -> dict:
    """
    candidate: output of scanner.classify()  (classification, confidence, size_bytes, ...)
    ctx:       output of context.enrich()    (active_process, package_owned, git_tracked)
    load:      output of safety_gate.read_system_load()
    system_busy: output of safety_gate.is_system_busy(load)
    Returns: {
        "risk_score": 0-100,
        "risk_tier": "LOW|MEDIUM|HIGH",
        "action": "AUTOMATE|SCHEDULE|APPROVAL_REQUIRED|DEFER|SKIP",
        "reason": string,
        "factors": [strings],
    }
    """
    classification = candidate.get("classification", "Unknown")
    confidence = float(candidate.get("confidence", 0.0))
    age_days = float(candidate.get("age_days", 0.0))
    duplicate = bool(candidate.get("duplicate_of"))
    cpu = float(load.get("cpu_percent", 0.0))
    io_wait = float(load.get("io_wait_percent", 0.0))
    memory = float(load.get("memory_percent", 0.0))

    # Start from a neutral risk level.
    # The score represents risk of making an unsafe optimization decision:
    # higher = more risky, lower = safer.
    score = 50
    factors = []

    # Hard stops: active or package-owned files must never be optimized.
    if ctx.get("active_process"):
        return _result(
            100,
            HIGH,
            "SKIP",
            "File is currently open by a running process.",
            ["⚠ Active process detected", "⚠ Cleanup skipped for safety"],
        )
    if ctx.get("package_owned"):
        return _result(
            100,
            HIGH,
            "SKIP",
            "File is owned by an installed system package.",
            ["⚠ Package-owned file", "⚠ System package ownership detected"],
        )

    # Age / recency
    if age_days >= 90:
        score -= 12
        factors.append(f"✓ Very old ({age_days:.0f} days)")
    elif age_days < 7:
        score += 15
        factors.append("⚠ Recently used")
    else:
        score -= 3
        factors.append(f"✓ Older file ({age_days:.0f} days)")

    # Usage classification
    if "Hot" in classification:
        score += 15
        factors.append("⚠ Hot data")
    elif "Warm" in classification:
        score += 5
        factors.append("✓ Warm data")
    elif "Cold" in classification:
        score -= 8
        factors.append("✓ Cold data")

    # Redundancy
    if "Redundant" in classification or duplicate:
        score -= 10
        factors.append("✓ Redundant data")

    # Prediction confidence
    if confidence >= 0.9:
        score -= 5
        factors.append(f"✓ High confidence ({confidence:.0%})")
    elif confidence >= 0.75:
        factors.append(f"✓ Moderate confidence ({confidence:.0%})")
    else:
        score += 10
        factors.append(f"⚠ Low confidence ({confidence:.0%})")

    # Safety context.
    if not ctx.get("active_process"):
        factors.append("✓ Not actively used")
    if not ctx.get("package_owned"):
        factors.append("✓ Not package-owned")

    if not ctx.get("git_tracked"):
        factors.append("✓ Not Git tracked")
    else:
        # Git-tracked files are explicitly high risk and should not
        # be automatically optimized.
        score = max(score, 70)
        factors.append("⚠ Git tracked")

    if system_busy:
        factors.append(f"⚠ High CPU ({cpu:.0f}%)")
        factors.append(f"⚠ High I/O wait ({io_wait:.0f}%)")
        factors.append(f"⚠ RAM at {memory:.0f}%")
        factors.append(f"⚠ Live safety override: {str(load.get('state') or 'BUSY').upper()}")
    else:
        factors.append("✓ System load normal")

    # Clamp and classify risk.
    score = max(0, min(100, round(score)))
    risk_tier = _tier_for_score(score)

    # Policy decisions.
    if ctx.get("active_process"):
        action = "SKIP"
    elif ctx.get("package_owned"):
        action = "SKIP"
    elif ctx.get("git_tracked"):
        action = "DEFER"
    elif system_busy:
        action = "DEFER"
    elif risk_tier == LOW:
        action = "AUTOMATE"
    elif risk_tier == MEDIUM:
        action = "SCHEDULE"
    else:
        action = "APPROVAL_REQUIRED"

    system_state = str(load.get("state") or "NORMAL")
    reason = _reason_for_decision(risk_tier, action, confidence, system_busy, cpu, io_wait, system_state)
    return {
        "risk_score": score,
        "risk_tier": risk_tier,
        "action": action,
        "reason": reason,
        "factors": factors,
    }


def _tier_for_score(score: int) -> str:
    if score >= 66:
        return HIGH
    if score >= 31:
        return MEDIUM
    return LOW


def _reason_for_decision(risk_tier, action, confidence, system_busy, cpu, io_wait, system_state="NORMAL"):
    if action == "SKIP":
        return "Safety check blocked this candidate because it is currently in active use or package-owned."
    if action == "DEFER":
        if system_state == "CRITICAL":
            return (
                f"Cleanup deferred because the system is currently under critical workload "
                f"(CPU {cpu:.0f}%, I/O wait {io_wait:.0f}%, state={system_state}). "
                f"File risk may be low, but the current system safety gate is blocking automation."
            )
        return (
            f"Cleanup is deferred because the system is currently busy "
            f"(CPU {cpu:.0f}%, I/O wait {io_wait:.0f}%, state={system_state}) or the file is Git tracked; "
            f"this should be re-checked when the system is stable."
        )
    if risk_tier == LOW:
        return f"Low-risk, stale, and/or redundant data with high confidence ({confidence:.0%}) is safe to automate."
    if risk_tier == MEDIUM:
        return f"Moderate risk due to confidence or file type; schedule cleanup during a safe window."
    return f"High-risk candidate requiring approval because confidence is low or ownership is ambiguous."


def _result(score, tier, action, reason, factors):
    return {
        "risk_score": int(score),
        "risk_tier": tier,
        "action": action,
        "reason": reason,
        "factors": factors,
    }
