"""
decision_engine.py — The Risk-Adaptive Decision Engine (core innovation).

Combines: data importance, AI confidence, context signals, and real-time system
workload into ONE risk tier + action. This is the module every teammate should
be able to explain to a judge.
"""

LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"


def assess(candidate: dict, ctx: dict, load: dict, system_busy: bool) -> dict:
    """
    candidate: output of scanner.classify()  (classification, confidence, size_bytes, ...)
    ctx:       output of context.enrich()    (active_process, package_owned, git_tracked)
    load:      output of safety_gate.read_system_load()
    system_busy: output of safety_gate.is_system_busy(load)
    Returns: {"risk_tier": ..., "action": ..., "reason": ...}
    """
    # Hard stops — never touch these regardless of confidence
    if ctx["active_process"]:
        return _result(HIGH, "SKIP", "File is currently open by a running process.")
    if ctx["package_owned"]:
        return _result(HIGH, "SKIP", "File is owned by an installed system package.")
    if ctx["git_tracked"]:
        return _result(HIGH, "DEFER", "File is tracked in an active Git repository — needs human review.")

    is_redundant = "Redundant" in candidate["classification"] or "Cold" in candidate["classification"]
    confidence = candidate["confidence"]

    # Base risk purely from data intelligence
    if is_redundant and confidence >= 0.9:
        base_tier = LOW
    elif is_redundant and confidence >= 0.75:
        base_tier = MEDIUM
    else:
        base_tier = HIGH

    # Real-time override: live system load can only make things SAFER to defer, never riskier to act
    if system_busy and base_tier == LOW:
        return _result(
            MEDIUM, "DEFER",
            f"Data risk was LOW (confidence {confidence:.0%}), but system is busy right now "
            f"(CPU {load['cpu_percent']:.0f}%, I/O wait {load['io_wait_percent']:.0f}%) — deferring."
        )
    if system_busy and base_tier == MEDIUM:
        return _result(HIGH, "DEFER", "Borderline risk plus high current system load — deferring.")

    if base_tier == LOW:
        return _result(LOW, "AUTOMATE", f"Redundant/cold data, high confidence ({confidence:.0%}), system load normal.")
    if base_tier == MEDIUM:
        return _result(MEDIUM, "SCHEDULE", f"Moderate confidence ({confidence:.0%}) — schedule for a safe window or confirm.")
    return _result(HIGH, "APPROVAL_REQUIRED", f"Low confidence ({confidence:.0%}) or ambiguous ownership — needs approval.")


def _result(tier, action, reason):
    return {"risk_tier": tier, "action": action, "reason": reason}
