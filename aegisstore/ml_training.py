"""
ml_training.py

Training and evaluation for AegisStore's
FutureUsageProbability model.

IMPORTANT:
The dataset is synthetic and is used for
prototype/hackathon evaluation.
"""

import random

import numpy as np

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from aegisstore.future_usage_model import train_model


def generate_training_data(samples=3000, seed=42):

    rng = random.Random(seed)

    X = []
    y = []

    for _ in range(samples):

        access_7d = rng.randint(0, 30)

        access_30d = (
            access_7d + rng.randint(0, 70)
        )

        access_90d = (
            access_30d + rng.randint(0, 180)
        )

        total_access = (
            access_90d + rng.randint(0, 100)
        )

        days_since_last_access = rng.uniform(
            0, 120
        )

        recent_ratio = (
            access_7d / access_30d
            if access_30d > 0
            else 0
        )

        size_bytes = rng.randint(
            1_000,
            500_000_000
        )

        days_since_modified = rng.uniform(
            0, 365
        )

        # Behavioral target.
        score = (
            access_7d * 0.35
            + access_30d * 0.08
            + access_90d * 0.015
            + recent_ratio * 8
            - days_since_last_access * 0.10
            - days_since_modified * 0.01
        )

        noise = rng.gauss(0, 0.8)

        future_use = int(
            score + noise >= 3.0
        )

        X.append([
            access_7d,
            access_30d,
            access_90d,
            total_access,
            min(days_since_last_access, 9999),
            recent_ratio,
            size_bytes,
            days_since_modified,
        ])

        y.append(future_use)

    return np.array(X), np.array(y)


def evaluate_model(model, X_test, y_test):

    predictions = model.predict(X_test)

    probabilities = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(
            y_test,
            predictions
        ),

        "precision": precision_score(
            y_test,
            predictions,
            zero_division=0
        ),

        "recall": recall_score(
            y_test,
            predictions,
            zero_division=0
        ),

        "f1": f1_score(
            y_test,
            predictions,
            zero_division=0
        ),

        "roc_auc": roc_auc_score(
            y_test,
            probabilities
        ),
    }

    return metrics


def build_and_evaluate():

    X, y = generate_training_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = train_model(
        X_train,
        y_train
    )

    metrics = evaluate_model(
        model,
        X_test,
        y_test
    )

    return model, metrics, X_test, y_test


if __name__ == "__main__":

    X, y = generate_training_data()

    print()
    print("AegisStore ML Evaluation")
    print("=" * 60)

    print(
        "Total samples:",
        len(X)
    )

    print(
        "Future-use samples:",
        int(y.sum())
    )

    print(
        "Non-future-use samples:",
        int(len(y) - y.sum())
    )

    model, metrics, X_test, y_test = (
        build_and_evaluate()
    )

    print()
    print("Test Set Metrics")
    print("-" * 60)

    for name, value in metrics.items():

        print(
            f"{name.upper():<12}: "
            f"{value * 100:.2f}%"
        )

    print()
    print("Classification Report")
    print("-" * 60)

    predictions = model.predict(X_test)

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "No Future Use",
                "Future Use"
            ],
            zero_division=0,
        )
    )

    print("Model evaluation: SUCCESS")
