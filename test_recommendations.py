from pathlib import Path

from aegisstore import scanner, usage_analyzer
from aegisstore.ml_training import generate_training_data
from aegisstore.future_usage_model import train_model, predict_record
from aegisstore.recommendation_engine import recommend


# --------------------------------------------------
# 1. Train the ML model
# --------------------------------------------------

X, y = generate_training_data(
    samples=3000,
    seed=42,
)

model = train_model(X, y)


# --------------------------------------------------
# 2. Scan the real sandbox
# --------------------------------------------------

target = (
    Path.home()
    / "AegisStore-Sandbox"
    / "test_usage"
)

records = scanner.scan_and_classify(target)

analyzed = usage_analyzer.analyze_records(records)


# --------------------------------------------------
# 3. ML prediction + recommendation
# --------------------------------------------------

print()
print("AegisStore Recommendation Engine")
print("=" * 80)

for record in analyzed:

    prediction = predict_record(
        model,
        record,
    )

    result = recommend(
        prediction
    )

    print()
    print(f"File                : {result['file_name']}")
    print(f"Usage Profile       : {result['usage_profile']}")
    print(
        f"Future Use          : "
        f"{result['future_usage_probability'] * 100:.1f}%"
    )
    print(
        f"Reproducibility    : "
        f"{result['reproducibility_score']}/100"
    )
    print(
        f"Storage Impact      : "
        f"{result['storage_impact_score']}/100"
    )
    print(
        f"Recommendation      : "
        f"{result['recommendation']}"
    )
    print(
        f"Why                 : "
        f"{result['recommendation_reason']}"
    )

print()
print("=" * 80)
print("No files were modified.")
