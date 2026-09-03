"""
usage_history.py

AegisStore file-usage history and feature extraction.

This module converts file usage events stored in SQLite into
features that can later be used by the FutureUsageProbability
ML model.
"""

import random
import time
from pathlib import Path

from aegisstore import db


SECONDS_PER_DAY = 86400


# ============================================================
# BASIC EVENT RECORDING
# ============================================================

def record_event(
    path,
    event_type="access",
    timestamp=None,
    source="tracker",
):
    """Record one file usage event."""

    db.log_file_usage(
        path=path,
        event_type=event_type,
        timestamp=timestamp,
        source=source,
    )


def record_access(
    path,
    timestamp=None,
    source="tracker",
):
    """Record a file access event."""

    record_event(
        path=path,
        event_type="access",
        timestamp=timestamp,
        source=source,
    )


def record_modify(
    path,
    timestamp=None,
    source="tracker",
):
    """Record a file modification event."""

    record_event(
        path=path,
        event_type="modify",
        timestamp=timestamp,
        source=source,
    )


# ============================================================
# TIME HELPERS
# ============================================================

def days_ago(days):
    """Return a Unix timestamp representing N days ago."""

    return time.time() - (days * SECONDS_PER_DAY)


def days_since(timestamp):
    """Calculate days since an event."""

    if timestamp is None:
        return 9999.0

    return max(
        0.0,
        (time.time() - float(timestamp)) / SECONDS_PER_DAY,
    )


# ============================================================
# USAGE FEATURES
# ============================================================

def features_for_file(path):
    """
    Calculate usage features for a file.

    Features include:

    - access_count_7d
    - access_count_30d
    - access_count_90d
    - total_access_count
    - days_since_last_access
    - recent_access_ratio
    """

    events = db.file_usage_events(path)

    access_events = [
        event
        for event in events
        if event["event_type"] == "access"
    ]

    now = time.time()

    count_7d = 0
    count_30d = 0
    count_90d = 0

    for event in access_events:

        age = now - float(event["timestamp"])

        if age <= 7 * SECONDS_PER_DAY:
            count_7d += 1

        if age <= 30 * SECONDS_PER_DAY:
            count_30d += 1

        if age <= 90 * SECONDS_PER_DAY:
            count_90d += 1

    total = len(access_events)

    if access_events:

        latest_timestamp = max(
            float(event["timestamp"])
            for event in access_events
        )

        last_access_days = days_since(latest_timestamp)

    else:

        last_access_days = 9999.0

    if count_30d > 0:
        recent_ratio = count_7d / count_30d
    else:
        recent_ratio = 0.0

    return {
        "path": str(path),
        "access_count_7d": count_7d,
        "access_count_30d": count_30d,
        "access_count_90d": count_90d,
        "total_access_count": total,
        "days_since_last_access": round(
            last_access_days,
            2,
        ),
        "recent_access_ratio": round(
            recent_ratio,
            3,
        ),
    }


# ============================================================
# DEMO HISTORY GENERATOR
# ============================================================

def seed_usage_pattern(
    path,
    profile,
    days=90,
    seed=None,
):
    """
    Generate controlled historical access events.

    Profiles:

        HOT
        WARM
        COLD
        INACTIVE

    This is intended for the AegisStore hackathon demo.

    The generated events are explicitly marked as
    source='simulator'.
    """

    rng = random.Random(seed)

    path = str(path)

    # --------------------------------------------------------
    # HOT
    # --------------------------------------------------------

    if profile.upper() == "HOT":

        events_per_day = 3

    # --------------------------------------------------------
    # WARM
    # --------------------------------------------------------

    elif profile.upper() == "WARM":

        events_per_day = 0.5

    # --------------------------------------------------------
    # COLD
    # --------------------------------------------------------

    elif profile.upper() == "COLD":

        events_per_day = 0.08

    # --------------------------------------------------------
    # INACTIVE
    # --------------------------------------------------------

    elif profile.upper() == "INACTIVE":

        events_per_day = 0

    else:

        raise ValueError(
            "profile must be HOT, WARM, COLD or INACTIVE"
        )

    # Generate events from oldest to newest.

    for day in range(days, 0, -1):

        if events_per_day == 0:
            continue

        whole_events = int(events_per_day)

        fractional_probability = (
            events_per_day - whole_events
        )

        event_count = whole_events

        if rng.random() < fractional_probability:
            event_count += 1

        for _ in range(event_count):

            # Random time within the selected day.
            hour_offset = rng.uniform(
                0,
                SECONDS_PER_DAY,
            )

            timestamp = (
                time.time()
                - day * SECONDS_PER_DAY
                + hour_offset
            )

            record_access(
                path,
                timestamp=timestamp,
                source="simulator",
            )


# ============================================================
# USAGE PROFILE
# ============================================================

def usage_profile_from_features(features):
    """
    Classify a file based on observed usage history.

    This is intentionally deterministic for now.

    ML classification comes later.
    """

    count_7d = features["access_count_7d"]
    count_30d = features["access_count_30d"]
    last_access = features["days_since_last_access"]

    if count_7d >= 5:

        return "HOT"

    if count_30d >= 3 and last_access <= 30:

        return "WARM"

    if count_30d > 0 and last_access <= 90:

        return "COLD"

    return "INACTIVE"


# ============================================================
# COMPLETE ANALYSIS
# ============================================================

def analyze_usage(path):
    """Return usage features plus deterministic profile."""

    features = features_for_file(path)

    features["usage_profile"] = usage_profile_from_features(
        features
    )

    return features
