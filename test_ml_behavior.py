from pathlib import Path

from aegisstore import db, scanner, usage_analyzer
from aegisstore.ml_training import generate_training_data
from aegisstore.future_usage_model import train_model, predict_record


# --------------------------------------------------
# 1. Train model
# --------------------------------------------------

X, y = generate_training_data(
    samples=3000,
    seed=42,
)

model = train_model(X, y)


# --------------------------------------------------
# 2. Create controlled files
# --------------------------------------------------

target = (
    Path.home()
    / "AegisStore-Sandbox"
    / "ml_behavior"
)

target.mkdir(
    parents=True,
    exist_ok=True,
)

files = {
    "file_A.txt": "A" * 1000,
    "file_B.txt": "B" * 1000,
    "file_C.txt": "C" * 1000,
}

for name, content in files.items():
    (target / name).write_text(content)


# --------------------------------------------------
# 3. Clear previous experiment events
# --------------------------------------------------

db.clear_file_usage_events()


# --------------------------------------------------
# 4. Simulate different usage behaviours
# --------------------------------------------------

# A = almost inactive
for _ in range(1):
    db.log_file_usage(
        target / "file_A.txt",
        event_type="access",
        timestamp=__import__("time").time() - 20 * 86400,
        source="experiment",
    )


# B = moderate usage
for days_ago in [20, 15, 10, 5, 2]:
    db.log_file_usage(
        target / "file_B.txt",
        event_type="access",
        timestamp=__import__("time").time() - days_ago * 86400,
        source="experiment",
    )


# C = high recent usage
for days_ago in [6, 5, 4, 3, 2, 1, 0.5]:
    db.log_file_usage(
        target / "file_C.txt",
        event_type="access",
        timestamp=__import__("time").time() - days_ago * 86400,
        source="experiment",
    )


# --------------------------------------------------
# 5. Scan files
# --------------------------------------------------

records = scanner.scan_and_classify(target)

analyzed = usage_analyzer.analyze_records(records)


# --------------------------------------------------
# 6. Predict
# --------------------------------------------------

print()
print("AegisStore ML Behaviour Experiment")
print("=" * 75)
print(
    "Same file type + same size + different usage history"
)
print("=" * 75)

for record in sorted(
    analyzed,
    key=lambda x: x["file_name"],
):

    result = predict_record(
        model,
        record,
    )

    print()
    print(f"File: {result['file_name']}")
    print(
        f"7-day accesses : "
        f"{result['access_count_7d']}"
    )
    print(
        f"30-day accesses: "
        f"{result['access_count_30d']}"
    )
    print(
        f"Last access    : "
        f"{result['days_since_last_access']:.1f} days ago"
    )
    print(
        f"Future use     : "
        f"{result['future_usage_probability'] * 100:.1f}%"
    )
    print(
        f"Classification  : "
        f"{result['future_usage_class']}"
    )
