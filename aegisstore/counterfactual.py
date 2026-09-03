"""
Counterfactual explanations for AegisStore decisions.

Re-runs the existing decision engine with one controlled input changed.
No new ML model and no change to the original decision policy.
"""

from copy import deepcopy

from . import decision_engine


def explain_age_change(candidate, ctx, load, system_busy, days_delta=-7):
    """
    Show how the decision changes if the file were days_delta days newer/older.
    """
    original = deepcopy(candidate)

    current = decision_engine.assess(
        original, ctx, load, system_busy
    )

    counterfactual = deepcopy(candidate)
    counterfactual["age_days"] = max(
        0,
        float(candidate.get("age_days", 0)) + days_delta,
    )

    changed = decision_engine.assess(
        counterfactual, ctx, load, system_busy
    )

    delta = changed["risk_score"] - current["risk_score"]

    if delta < 0:
        explanation = (
            f"If the file were {abs(days_delta):.0f} days newer, "
            f"its risk would decrease by {abs(delta)} points."
        )
    elif delta > 0:
        explanation = (
            f"If the file were {abs(days_delta):.0f} days newer, "
            f"its risk would increase by {delta} points."
        )
    else:
        explanation = (
            f"Making the file {abs(days_delta):.0f} days newer "
            f"would not change its risk score."
        )

    return {
        "current_score": current["risk_score"],
        "counterfactual_score": changed["risk_score"],
        "delta": delta,
        "current_action": current["action"],
        "counterfactual_action": changed["action"],
        "explanation": explanation,
    }


def explain_recent_access(candidate, ctx, load, system_busy):
    """
    Counterfactual: treat the file as recently accessed.
    """
    current = decision_engine.assess(
        candidate, ctx, load, system_busy
    )

    counterfactual = deepcopy(candidate)
    counterfactual["age_days"] = 2
    counterfactual["classification"] = "Hot"

    changed = decision_engine.assess(
        counterfactual, ctx, load, system_busy
    )

    delta = changed["risk_score"] - current["risk_score"]

    if delta < 0:
        explanation = (
            f"If this file had been accessed recently, "
            f"risk would decrease by {abs(delta)} points."
        )
    elif delta > 0:
        explanation = (
            f"If this file had been accessed recently, "
            f"risk would increase by {delta} points."
        )
    else:
        explanation = (
            "Recent access would not change the current risk score."
        )

    return {
        "current_score": current["risk_score"],
        "counterfactual_score": changed["risk_score"],
        "delta": delta,
        "current_action": current["action"],
        "counterfactual_action": changed["action"],
        "explanation": explanation,
    }
