from pathlib import Path

from aegisstore import scanner, usage_analyzer
from aegisstore.ml_training import generate_training_data
from aegisstore.future_usage_model import train_model, predict_record


# --------------------------------------------------
# 1. Train the prototype model
# --------------------------------------------------

X, y = generate_training_data(
    samples=1000,
    seed=42,
)

model = train_model(X, y)


# --------------------------------------------------
# 2. Scan real AegisStore sandbox
# --------------------------------------------------

target = (
    Path.home()
    / "AegisStore-Sandbox"
    / "test_usage"
)

records = scanner.scan_and_classify(target)

analyzed = usage_analyzer.analyze_records(records)


# --------------------------------------------------
# 3. Predict future usage
# --------------------------------------------------

print("\nAegisStore Future Usage Predictions")
print("=" * 60)

for record in analyzed:

    result = predict_record(
        model,
        record,
    )

    print(
        f"{result['file_name']:<12} | "
        f"Profile: {result['usage_profile']:<8} | "
        f"7d: {result['access_count_7d']:<3} | "
        f"30d: {result['access_count_30d']:<3} | "
        f"90d: {result['access_count_90d']:<3} | "
        f"Future Use: "
        f"{result['future_usage_probability'] * 100:.1f}% | "
        f"{result['future_usage_class']}"
    )

    print(
        f"   Why: "
        f"{result['future_usage_explanation']}"
    )
