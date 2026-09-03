"""
future_usage_model.py

AegisStore Future Usage Probability model.

Predicts:
    P(file will be accessed again within the next 30 days)

The model is intentionally advisory.
It does NOT authorize deletion or modification of files.
"""

from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier


FEATURES = [
    "access_count_7d",
    "access_count_30d",
    "access_count_90d",
    "total_access_count",
    "days_since_last_access",
    "recent_access_ratio",
    "size_bytes",
    "days_since_modified",
]


def build_feature_vector(record):
    """
    Convert a file record into the numerical features
    expected by the ML model.
    """

    return [
        float(record.get("access_count_7d", 0)),
        float(record.get("access_count_30d", 0)),
        float(record.get("access_count_90d", 0)),
        float(record.get("total_access_count", 0)),
        min(float(record.get("days_since_last_access", 9999)), 9999),
        float(record.get("recent_access_ratio", 0)),
        float(record.get("size_bytes", 0)),
        float(record.get("days_since_modified", 0)),
    ]


def train_model(X, y):
    """
    Train the Random Forest model.

    X = feature matrix
    y = target:
        1 -> accessed again within 30 days
        0 -> not accessed again within 30 days
    """

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        random_state=42,
        class_weight="balanced",
    )

    model.fit(X, y)

    return model


def predict_probability(model, record):
    """
    Return probability that the file will be accessed
    again within 30 days.
    """

    features = np.array(
        [build_feature_vector(record)],
        dtype=float,
    )

    probability = model.predict_proba(features)[0]

    # Find probability belonging to class 1.
    classes = list(model.classes_)

    if 1 in classes:
        index = classes.index(1)
        result = probability[index]
    else:
        result = 0.0

    return round(float(result), 4)


def classify_probability(probability):
    """
    Human-readable interpretation of model probability.
    """

    if probability >= 0.80:
        return "HIGH_FUTURE_USE"

    if probability >= 0.50:
        return "MEDIUM_FUTURE_USE"

    if probability >= 0.20:
        return "LOW_FUTURE_USE"

    return "VERY_LOW_FUTURE_USE"


def explain_prediction(probability, record):
    """
    Generate a transparent explanation for the prediction.
    """

    accesses_7d = record.get("access_count_7d", 0)
    accesses_30d = record.get("access_count_30d", 0)
    last_access = record.get("days_since_last_access", 9999)

    if probability >= 0.80:
        reason = (
            f"High predicted future use because the file shows "
            f"strong recent activity ({accesses_7d} accesses in 7 days "
            f"and {accesses_30d} in 30 days)."
        )

    elif probability >= 0.50:
        reason = (
            f"Moderate predicted future use based on its historical "
            f"access pattern ({accesses_30d} accesses in 30 days)."
        )

    elif probability >= 0.20:
        reason = (
            f"Low predicted future use because recent activity is limited "
            f"and the last recorded access was {last_access:.1f} days ago."
        )

    else:
        reason = (
            f"Very low predicted future use because the file has little "
            f"recent access activity and was last accessed "
            f"{last_access:.1f} days ago."
        )

    return reason


def predict_record(model, record):
    """
    Add ML prediction fields to a file record.
    """

    probability = predict_probability(model, record)

    return {
        **record,
        "future_usage_probability": probability,
        "future_usage_class": classify_probability(probability),
        "future_usage_explanation": explain_prediction(
            probability,
            record,
        ),
    }
