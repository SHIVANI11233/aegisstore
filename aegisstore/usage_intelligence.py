"""
usage_intelligence.py

Analyzes how files are actually being used.

Produces:
- file age
- days since last access
- days since modification
- usage profile
- activity score
- storage impact
"""

import time
from pathlib import Path


SECONDS_PER_DAY = 86400


def days_since(timestamp: float) -> float:
    """Return number of days since a Unix timestamp."""
    if not timestamp:
        return 9999.0

    return max(0.0, (time.time() - timestamp) / SECONDS_PER_DAY)


def activity_score(
    days_since_access: float,
    days_since_modified: float,
) -> float:
    """
    Calculate a deterministic activity score from 0-100.

    Recent access is weighted more heavily than modification time.
    """

    access_score = max(
        0.0,
        100.0 - min(days_since_access, 100.0),
    )

    modification_score = max(
        0.0,
        100.0 - min(days_since_modified, 100.0),
    )

    score = (
        access_score * 0.7
        + modification_score * 0.3
    )

    return round(max(0.0, min(100.0, score)), 2)


def usage_profile(
    days_since_access: float,
    days_since_modified: float,
    duplicate: bool = False,
) -> str:
    """
    Classify file usage.

    HOT       = actively used
    WARM      = recently used
    COLD      = little recent activity
    INACTIVE  = essentially unused
    """

    score = activity_score(
        days_since_access,
        days_since_modified,
    )

    if score >= 75:
        profile = "HOT"

    elif score >= 45:
        profile = "WARM"

    elif score >= 15:
        profile = "COLD"

    else:
        profile = "INACTIVE"

    # Duplicate information is intentionally not allowed
    # to override actual usage classification.
    return profile


def analyze_file(record: dict) -> dict:
    """
    Analyze one scanner record.

    Expected scanner fields:
        path
        size_bytes
        last_accessed
        modified
        duplicate_of
    """

    now = time.time()

    path = Path(record["path"])

    last_accessed = record.get(
        "last_accessed",
        record.get("atime", now),
    )

    modified = record.get(
        "modified",
        record.get("mtime", now),
    )

    access_age = days_since(last_accessed)
    modification_age = days_since(modified)

    duplicate = bool(record.get("duplicate_of"))

    score = activity_score(
        access_age,
        modification_age,
    )

    profile = usage_profile(
        access_age,
        modification_age,
        duplicate=duplicate,
    )

    return {
        **record,

        "file_name": path.name,
        "extension": path.suffix.lower(),

        "days_since_access": round(access_age, 2),
        "days_since_modified": round(modification_age, 2),

        "activity_score": score,
        "usage_profile": profile,

        "is_duplicate": duplicate,

        "storage_impact_bytes": int(
            record.get("size_bytes", 0)
        ),
    }


def analyze_records(records: list[dict]) -> list[dict]:
    """Analyze all scanner records."""

    return [
        analyze_file(record)
        for record in records
    ]


def summarize_usage(records: list[dict]) -> dict:
    """Create a high-level usage profile summary."""

    summary = {
        "HOT": 0,
        "WARM": 0,
        "COLD": 0,
        "INACTIVE": 0,
        "total_files": len(records),
        "total_bytes": 0,
    }

    for record in records:
        profile = record.get(
            "usage_profile",
            "INACTIVE",
        )

        if profile in summary:
            summary[profile] += 1

        summary["total_bytes"] += int(
            record.get("size_bytes", 0)
        )

    return summary
