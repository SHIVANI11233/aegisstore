"""
usage_analyzer.py

Combines filesystem scan metadata with file usage history.
"""

from pathlib import Path

from aegisstore import usage_history


# ============================================================
# ANALYZE ONE FILE
# ============================================================

def analyze_file(record):
    """Combine scanner information with historical usage."""

    path = Path(record["path"])

    usage = usage_history.analyze_usage(path)

    result = {
        **record,

        # File identity
        "file_name": path.name,

        # Usage history
        "access_count_7d": usage["access_count_7d"],
        "access_count_30d": usage["access_count_30d"],
        "access_count_90d": usage["access_count_90d"],
        "total_access_count": usage["total_access_count"],

        # Recency
        "days_since_last_access": usage[
            "days_since_last_access"
        ],

        # Usage trend
        "recent_access_ratio": usage[
            "recent_access_ratio"
        ],

        # Current deterministic profile
        "usage_profile": usage[
            "usage_profile"
        ],
    }

    return result


# ============================================================
# ANALYZE MULTIPLE FILES
# ============================================================

def analyze_records(records):
    """Analyze all scanned files."""

    return [
        analyze_file(record)
        for record in records
    ]


# ============================================================
# SUMMARY
# ============================================================

def summarize(records):
    """
    Create a usage summary.

    Returns file counts and storage size for:
        HOT
        WARM
        COLD
        INACTIVE
    """

    summary = {
        "HOT": {
            "files": 0,
            "bytes": 0,
        },
        "WARM": {
            "files": 0,
            "bytes": 0,
        },
        "COLD": {
            "files": 0,
            "bytes": 0,
        },
        "INACTIVE": {
            "files": 0,
            "bytes": 0,
        },
    }

    for record in records:

        profile = record.get(
            "usage_profile",
            "INACTIVE",
        )

        size = int(
            record.get(
                "size_bytes",
                0,
            )
        )

        if profile not in summary:
            profile = "INACTIVE"

        summary[profile]["files"] += 1
        summary[profile]["bytes"] += size

    return summary
