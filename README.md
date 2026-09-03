
````markdown
# AegisStore — Risk-Adaptive AI Storage Intelligence

AegisStore is a Linux/Ubuntu storage intelligence prototype that goes beyond simply finding large or old files. It combines filesystem analysis, usage behavior, ML-based future-use prediction, duplicate detection, storage forecasting, explainable recommendations, and a risk-adaptive safety layer.

> **Core idea:** Existing tools tell you where your storage went. AegisStore tells you what the data is doing, what you should do about it, why, and whether it is safe to act.

---

## AegisStore — Working Prototype (Must-Have Modules)

The prototype covers the core build-plan modules:

1. **Filesystem Scanner** — scans a controlled directory and collects file metadata, size, timestamps and hashes.
2. **Context Safety Checks** — checks active processes, package ownership and Git-tracked status before risky actions.
3. **Risk-Adaptive Decision Engine** — assigns risk tiers and actions, with a live system-load override that can defer an otherwise safe action when the machine is busy.
4. **Quarantine + Undo + Audit Log** — supports reversible quarantine and records actions for auditability.
5. **Storage Story** — produces an explainable narrative around storage findings.
6. **Usage Intelligence** — classifies files as **HOT / WARM / COLD / INACTIVE** using access and modification behavior.
7. **Future Usage Prediction** — ML predicts `FutureUsageProbability`, estimating whether a file is likely to be accessed again within the next 30 days.
8. **Recommendation Engine** — combines future-use probability, duplication, storage impact and reproducibility to recommend **CLEANUP / ARCHIVE / KEEP / REVIEW**.
9. **Storage Forecasting** — estimates future storage pressure from historical usage data.

Tested and working on Linux in a sandboxed environment.

---

## 1. Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

`anthropic` is optional. If `ANTHROPIC_API_KEY` is not configured, the Storage Story falls back to a clean template narrative, so the core demo does not depend on a live AI API.

To enable the optional live narrative:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

---

## 2. Generate Demo Clutter

Do not point the prototype at important real files during a rehearsal. Use the synthetic sandbox instead:

```bash
python3 demo_setup.py ./demo_disk
```

The demo creates representative storage conditions including:

* an **active/hot** file that should be protected from cleanup
* a **duplicated + old** dataset pair
* old build artifacts and logs
* a moderately recent file with lower confidence

---

## 3. Run the Risk-Adaptive Scan

```bash
python3 -m aegisstore.cli scan ./demo_disk
```

The CLI reports, per candidate:

* file size and age
* classification
* confidence
* duplicate status
* active-process status
* package ownership
* Git-tracked status
* risk tier
* recommended action

Low-risk candidates can be quarantined by the existing prototype workflow, with integrity verification and an audit record.

---

## 4. Demonstrate the Live-Override

This is the strongest safety demonstration: an action that would normally be allowed can be deferred when the **live system is busy**.

In a second terminal:

```bash
yes > /dev/null & yes > /dev/null & yes > /dev/null &
```

Run the scan in the first terminal. The system should detect a busy system and downgrade eligible actions to `DEFER`.

Stop the CPU workload:

```bash
kill %1 %2 %3
```

Then run the scan again to demonstrate the normal decision path.

For a deterministic demonstration without depending on actual CPU load:

```bash
python3 test_override.py
```

---

## 5. Demonstrate Usage Intelligence + ML

AegisStore now learns from file-access history rather than relying only on file age.

The usage pipeline tracks access events over **7 / 30 / 90 day windows** and derives behavioral features such as recent activity and time since last access.

The ML model predicts:

```text
FutureUsageProbability = P(file will be accessed again within 30 days)
```

Run the prototype prediction demo:

```bash
python3 test_future_usage.py
```

Example interpretation:

```text
HOT      → high recent activity → high future-use probability
WARM     → moderate activity    → moderate future-use probability
COLD     → low activity         → lower future-use probability
INACTIVE → little/no activity   → candidate for review/cleanup/archive
```

The ML prediction is **advisory**. It does not independently authorize deletion.

### Controlled ML Validation

The current prototype includes a controlled synthetic training/evaluation pipeline in:

```text
aegisstore/ml_training.py
```

Prototype metrics from the controlled synthetic dataset:

* Accuracy: **93.33%**
* Precision: **96.53%**
* Recall: **93.73%**
* F1: **95.11%**
* ROC-AUC: **98.45%**

> These are **synthetic/controlled prototype metrics**, not production Ubuntu performance claims.

---

## 6. Demonstrate Explainable Recommendations

The recommendation engine combines multiple signals and produces one of four actions:

| Recommendation | Meaning                                                           |
| -------------- | ----------------------------------------------------------------- |
| **CLEANUP**    | Low expected future use and suitable for reclaiming space         |
| **ARCHIVE**    | Low/moderate future use but potentially worth retaining elsewhere |
| **KEEP**       | Strong evidence that the file is still useful                     |
| **REVIEW**     | Signals are mixed; human decision is preferred                    |

Run:

```bash
python3 test_recommendations.py
```

Every recommendation includes an explanation of why the decision was made.

---

## 7. Show Audit + Undo

The existing reversible workflow can be demonstrated with:

```bash
python3 -m aegisstore.cli audit
```

To restore a quarantined file:

```bash
python3 -m aegisstore.cli undo <quarantine_file_path>
```

This demonstrates that the prototype is recommendation/safety-oriented rather than silently deleting user data.

---

## 8. Storage Forecasting

AegisStore also maintains historical storage measurements and can estimate future storage pressure.

The forecast is intended to answer questions such as:

* How quickly is storage usage growing?
* When could the system approach a storage threshold?
* What is the likely impact of reclaiming candidate files?

Forecast outputs should be treated as estimates and should include the available history/sample quality when presented.

---

## 9. End-to-End Architecture

```text
Ubuntu / Linux
      ↓
Sandboxed Filesystem Scan
      ↓
File Metadata + Hashes
      ↓
Usage History + Context Checks
      ↓
Usage Intelligence
HOT / WARM / COLD / INACTIVE
      ↓
ML Future Usage Probability
      ↓
Duplicate + Storage Impact Analysis
      ↓
Recommendation Engine
CLEANUP / ARCHIVE / KEEP / REVIEW
      ↓
Storage Forecast
      ↓
Risk-Adaptive Safety Layer
      ↓
Final Explainable Recommendation
      ↓
Optional Quarantine + Undo + Audit
```

---

## 10. Reset Between Rehearsals

```bash
rm -rf demo_disk quarantine aegisstore.db
python3 demo_setup.py ./demo_disk
```

If you are testing usage-history behavior, regenerate the synthetic usage history for the demo files before running the ML demonstrations.

---

## Current Scope

### Built

* Filesystem scanning
* SHA-256 duplicate detection
* Context safety checks
* Risk-adaptive decision engine
* Live system-load override
* Quarantine / undo / audit workflow
* Usage event history
* HOT / WARM / COLD / INACTIVE classification
* Future-use ML prediction
* Explainable cleanup/archive/keep/review recommendations
* Storage history and forecasting components
* Automated test coverage for the core intelligence modules

### Not Yet the Core Demo

* Final Streamlit AI dashboard integration
* Isolation Forest anomaly scoring
* systemd packaging
* Fully autonomous deletion

The system is intentionally **recommendation-first**: intelligence recommends an action, while safety controls and the user remain the final authority.

---

## Known Limitation

`is_active_process()` checks open file handles through `psutil`. Depending on Linux permissions, a process may not be able to inspect every other user's open files.

This is a permissions boundary rather than a flaw in the decision logic.

---

## Project Tests

Run the complete test suite with:

```bash
pytest -q
```

The current development state has the core test suite passing.

---

## Project Structure

```text
aegisstore/
├── scanner.py                 # filesystem scan + duplicate detection
├── context.py                 # process/package/Git safety checks
├── decision_engine.py         # risk-adaptive decisions
├── quarantine.py              # reversible quarantine workflow
├── audit.py                   # audit trail
├── predictor.py               # storage forecasting
├── storage_intelligence.py    # forecast intelligence helpers
├── usage_history.py           # access-event history + behavioral features
├── usage_intelligence.py      # HOT/WARM/COLD/INACTIVE analysis
├── usage_analyzer.py          # scanner + usage-history integration
├── future_usage_model.py      # future-use ML model
├── ml_training.py             # controlled ML training/evaluation
└── recommendation_engine.py   # CLEANUP/ARCHIVE/KEEP/REVIEW
```

---

## Safety Philosophy

AegisStore separates **intelligence from authority**.

The AI/ML layer identifies patterns and recommends actions, but safety context, system state, confidence, and human approval remain part of the final decision path.

That makes the prototype more than a storage cleaner: it is a **risk-aware storage intelligence system for Linux**.

```

**One important change:** I deliberately updated the README to show the **new AI/ML modules as built**, while keeping quarantine, undo, audit, and the Risk-Adaptive Engine because those are already part of your working prototype. 
```
