"""
predictor.py — Pillar 2: Predictive Intelligence.
Forecasts when disk usage will hit warning thresholds, using linear regression
on historical usage snapshots logged in SQLite. Falls back gracefully when
there isn't enough history yet (e.g. first run of the night).
"""
from datetime import datetime, timedelta

import numpy as np

from . import db

THRESHOLDS = [0.85, 0.90, 0.95]  # 85% / 90% / 95% capacity


def forecast(path: str, min_points: int = 3):
    """
    Returns a dict with current usage %, growth rate (bytes/day), and predicted
    days-until-threshold for each threshold in THRESHOLDS. Returns None if there
    isn't enough historical data yet.
    """
    rows = db.usage_series(path)
    if len(rows) < min_points:
        return None

    timestamps = np.array([r["timestamp"] for r in rows])
    used = np.array([r["used_bytes"] for r in rows])
    total = rows[-1]["total_bytes"]

    days = (timestamps - timestamps[0]) / 86400.0
    slope, intercept = np.polyfit(days, used, 1)
    current_used = used[-1]
    current_pct = current_used / total

    predictions = {}
    for threshold in THRESHOLDS:
        target_bytes = total * threshold
        if slope <= 0:
            predictions[threshold] = None
            continue
        if current_used >= target_bytes:
            predictions[threshold] = 0
            continue
        days_needed = (target_bytes - current_used) / slope
        predictions[threshold] = round(days_needed, 1)

    return {
        "current_usage_pct": current_pct,
        "growth_rate_bytes_per_day": slope,
        "growth_rate_gb_per_day": slope / (1024 ** 3),
        "predictions_days": predictions,
        "sample_count": len(rows),
    }


def seed_synthetic_history(path: str, total_bytes: int, current_used_bytes: int,
                            daily_growth_gb: float = 1.8, days_back: int = 14):
    """
    Demo helper: backfills N days of synthetic usage history so the forecast
    has something to work with on the very first run tonight. The trend is
    anchored to END at today's real (current) usage, so a genuine disk-usage
    reading logged afterward continues the line instead of contradicting it.
    Real usage, logged over multiple actual days, replaces the need for this.
    """
    now = datetime.now()
    daily_growth_bytes = daily_growth_gb * (1024 ** 3)
    start_used = max(0, current_used_bytes - daily_growth_bytes * days_back)

    for i in range(days_back, -1, -1):
        ts = (now - timedelta(days=i)).timestamp()
        used = start_used + daily_growth_bytes * (days_back - i)
        used = min(used, total_bytes * 0.98)
        conn = db.get_conn()
        conn.execute(
            "INSERT INTO usage_history (timestamp, path, used_bytes, total_bytes) VALUES (?,?,?,?)",
            (ts, str(path), int(used), int(total_bytes)),
        )
        conn.commit()
        conn.close()
