"""
storage_intelligence.py — Storage Intelligence layer.
Enhances the basic predictor with forecast quality, cleanup impact,
and deterministic recommendations.
"""

from . import db, predictor


def assess_forecast_quality(sample_count: int, slope: float = 0.0, used_samples=None) -> str:
    """
    Assess forecast data quality based on sample count and trend consistency.
    Returns: HIGH | MEDIUM | LOW | INSUFFICIENT
    """
    if sample_count < 3:
        return "INSUFFICIENT"
    if sample_count < 5:
        return "LOW"
    if sample_count < 10:
        return "MEDIUM"
    return "HIGH"


def format_growth_rate(bytes_per_day: float) -> str:
    """Format growth rate in human-readable form."""
    if abs(bytes_per_day) < 1024:
        return f"{bytes_per_day:.0f} B/day"
    if abs(bytes_per_day) < 1024 * 1024:
        return f"{bytes_per_day / 1024:.1f} KB/day"
    if abs(bytes_per_day) < 1024 * 1024 * 1024:
        return f"{bytes_per_day / (1024 * 1024):.1f} MB/day"
    gb_per_day = bytes_per_day / (1024 ** 3)
    sign = "+" if gb_per_day >= 0 else ""
    return f"{sign}{gb_per_day:.1f} GB/day"


def human_bytes(n_bytes: float) -> str:
    """Format bytes in human-readable form."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(n_bytes) < 1024:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:.1f} PB"


def storage_forecast_detailed(path: str, reclaimable_bytes: int = 0):
    """
    Enhanced forecast that includes cleanup impact and recommendation.
    Returns a dict with:
    - forecast (original predictor output)
    - forecast_quality
    - growth_rate_formatted
    - cleanup_impact
    - recommendation
    """
    fc = predictor.forecast(path, min_points=3)
    if fc is None:
        return {
            "forecast": None,
            "forecast_quality": "INSUFFICIENT",
            "growth_rate_formatted": "N/A",
            "cleanup_impact": None,
            "recommendation": "Not enough historical data. Continue collecting storage history before relying on the forecast.",
        }

    quality = assess_forecast_quality(fc["sample_count"], slope=fc.get("growth_rate_bytes_per_day", 0.0))
    growth_formatted = format_growth_rate(fc["growth_rate_bytes_per_day"])

    cleanup_impact = None
    if reclaimable_bytes > 0:
        current_used = fc["current_usage_pct"] * sum(
            r["total_bytes"] for r in db.usage_series(path)
        ) / max(1, len(db.usage_series(path)))
        estimated_after_cleanup = max(0, current_used - reclaimable_bytes)
        total_bytes = fc["current_usage_pct"] * estimated_after_cleanup if fc["current_usage_pct"] > 0 else 1
        estimated_after_pct = estimated_after_cleanup / total_bytes if total_bytes > 0 else 0

        # Recalculate threshold days with reduced used bytes
        predictions_after = {}
        slope = fc["growth_rate_bytes_per_day"]
        for threshold in [0.85, 0.90, 0.95]:
            target_bytes = total_bytes * threshold
            if slope <= 0:
                predictions_after[threshold] = None
                continue
            if estimated_after_cleanup >= target_bytes:
                predictions_after[threshold] = 0
                continue
            days_needed = (target_bytes - estimated_after_cleanup) / slope
            predictions_after[threshold] = round(days_needed, 1)

        cleanup_impact = {
            "current_used_bytes": current_used,
            "current_used_formatted": human_bytes(current_used),
            "reclaimable_bytes": reclaimable_bytes,
            "reclaimable_formatted": human_bytes(reclaimable_bytes),
            "estimated_after_bytes": estimated_after_cleanup,
            "estimated_after_formatted": human_bytes(estimated_after_cleanup),
            "estimated_after_pct": estimated_after_pct,
            "predictions_after_days": predictions_after,
        }

    # Generate recommendation
    recommendation = _generate_recommendation(fc, quality, reclaimable_bytes, cleanup_impact)

    return {
        "forecast": fc,
        "forecast_quality": quality,
        "growth_rate_formatted": growth_formatted,
        "cleanup_impact": cleanup_impact,
        "recommendation": recommendation,
    }


def _generate_recommendation(forecast_data: dict, quality: str, reclaimable_bytes: int, cleanup_impact: dict) -> str:
    """Generate a deterministic, human-readable recommendation."""
    if forecast_data is None or quality == "INSUFFICIENT":
        return "Not enough historical data. Continue collecting storage history before relying on the forecast."

    current_pct = forecast_data["current_usage_pct"] * 100
    growth_gb_per_day = forecast_data["growth_rate_gb_per_day"]
    predictions_days = forecast_data["predictions_days"]

    # Determine if any threshold is reached soon
    urgent_threshold = None
    for threshold, days in predictions_days.items():
        if days is not None and days > 0 and days <= 7:
            urgent_threshold = threshold
            break

    if growth_gb_per_day < 0:
        return (
            f"Storage is currently shrinking at {abs(growth_gb_per_day):.1f} GB/day. "
            f"No urgent capacity concerns. Cleanup can be deferred."
        )

    if growth_gb_per_day < 0.1:
        return (
            f"Storage growth is minimal ({growth_gb_per_day:.2f} GB/day). "
            f"No urgent capacity threshold projected. Cleanup can be deferred."
        )

    if urgent_threshold:
        threshold_pct = int(urgent_threshold * 100)
        if quality == "LOW":
            return (
                f"Storage is projected to reach {threshold_pct}% capacity within 7 days at current growth rates. "
                f"Forecast confidence is LOW due to limited historical data. Continue observing trends. "
                f"{reclaimable_bytes / (1024**3):.1f} GB of data is potentially reclaimable."
            )
        if reclaimable_bytes > 0:
            delay_days = cleanup_impact["predictions_after_days"].get(urgent_threshold)
            if delay_days is not None and delay_days > predictions_days.get(urgent_threshold, 0):
                delay_amount = delay_days - predictions_days.get(urgent_threshold, 0)
                return (
                    f"Storage is growing at {growth_gb_per_day:.1f} GB/day and will reach {threshold_pct}% capacity soon. "
                    f"Low-risk cleanup of {reclaimable_bytes / (1024**3):.1f} GB could delay the threshold by ~{delay_amount:.0f} days."
                )
        return (
            f"Storage is growing rapidly at {growth_gb_per_day:.1f} GB/day "
            f"and will reach {threshold_pct}% capacity within 7 days. "
            f"Review available cleanup candidates."
        )

    if reclaimable_bytes > 0:
        return (
            f"Storage growth is {growth_gb_per_day:.1f} GB/day. "
            f"No urgent threshold projected, but {reclaimable_bytes / (1024**3):.1f} GB is potentially reclaimable. "
            f"Cleanup can be scheduled during a safe window."
        )

    return (
        f"Storage is growing at {growth_gb_per_day:.1f} GB/day. "
        f"Current forecast quality is {quality}. Continue monitoring."
    )
