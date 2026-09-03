"""
recommendation_engine.py

AegisStore recommendation intelligence.

Combines:
- Future usage probability
- Duplicate status
- File size
- Reproducibility
- Usage profile

Output:
    CLEANUP
    ARCHIVE
    KEEP
    REVIEW

This module recommends actions only.
It never deletes or modifies files.
"""

from pathlib import Path


def reproducibility_score(record):
    """
    Estimate how easily the file could be recreated.

    Score:
        0   = difficult / irreplaceable
        100 = highly reproducible
    """

    path = Path(record["path"])

    extension = path.suffix.lower()

    # Easily reproducible/generated data.
    reproducible_extensions = {
        ".py",
        ".cpp",
        ".c",
        ".js",
        ".ts",
        ".java",
        ".log",
        ".tmp",
        ".cache",
        ".o",
        ".obj",
        ".class",
    }

    # Source/project files are generally valuable
    # even though they may be reproducible.
    source_extensions = {
        ".py",
        ".cpp",
        ".c",
        ".js",
        ".ts",
        ".java",
    }

    if extension in source_extensions:
        return 40

    if extension in reproducible_extensions:
        return 80

    if record.get("is_duplicate", False):
        return 90

    return 30


def storage_impact_score(record):
    """
    Convert file size into a simple 0-100
    storage impact score.
    """

    size = int(record.get("size_bytes", 0))

    if size >= 1_000_000_000:
        return 100

    if size >= 500_000_000:
        return 85

    if size >= 100_000_000:
        return 70

    if size >= 10_000_000:
        return 50

    if size >= 1_000_000:
        return 30

    return 10


def recommend(record):
    """
    Generate a recommendation for a file.

    No filesystem modification is performed.
    """

    probability = float(
        record.get(
            "future_usage_probability",
            0.5,
        )
    )

    duplicate = bool(
        record.get("is_duplicate", False)
    )

    profile = record.get(
        "usage_profile",
        "INACTIVE",
    )

    reproducibility = reproducibility_score(
        record
    )

    storage_impact = storage_impact_score(
        record
    )

    # ---------------------------------------------
    # High-confidence keep
    # ---------------------------------------------

    if probability >= 0.75:
        action = "KEEP"
        reason = (
            "High predicted future use. "
            "The file should remain available."
        )

    # ---------------------------------------------
    # Duplicate with low future use
    # ---------------------------------------------

    elif duplicate and probability < 0.50:
        action = "CLEANUP"
        reason = (
            "Duplicate file with relatively low "
            "predicted future use."
        )

    # ---------------------------------------------
    # Low future use + reproducible
    # ---------------------------------------------

    elif (
        probability < 0.25
        and reproducibility >= 70
    ):
        action = "CLEANUP"
        reason = (
            "Low predicted future use and high "
            "reproducibility."
        )

    # ---------------------------------------------
    # Cold data with meaningful storage impact
    # ---------------------------------------------

    elif (
        probability < 0.50
        and storage_impact >= 50
    ):
        action = "ARCHIVE"
        reason = (
            "Low predicted future use with "
            "meaningful storage impact. "
            "Archiving preserves the data while "
            "reducing active-storage pressure."
        )

    # ---------------------------------------------
    # Moderate uncertainty
    # ---------------------------------------------

    elif probability < 0.60:
        action = "REVIEW"
        reason = (
            "Usage signals are uncertain. "
            "Human review is recommended before "
            "taking action."
        )

    # ---------------------------------------------
    # Default
    # ---------------------------------------------

    else:
        action = "KEEP"
        reason = (
            "Current usage signals do not provide "
            "enough evidence for cleanup or archiving."
        )

    return {
        **record,
        "reproducibility_score": reproducibility,
        "storage_impact_score": storage_impact,
        "recommendation": action,
        "recommendation_reason": reason,
    }


def recommend_records(records):
    """
    Generate recommendations for multiple files.
    """

    return [
        recommend(record)
        for record in records
    ]
