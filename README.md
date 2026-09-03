
````markdown
# 🛡️ AegisStore

### Risk-Adaptive AI-Powered Intelligent Storage Optimizer for Linux

> **AegisStore doesn't just find files to clean — it understands usage, predicts future value, evaluates risk, considers live system load, explains its decisions, and keeps the user in control.**

AegisStore is an AI-powered storage intelligence and optimization system designed for Linux/Ubuntu. It analyzes filesystem behavior, identifies redundant and low-value files, predicts future file usage, forecasts storage growth, and generates explainable cleanup and archiving recommendations.

Unlike traditional storage cleaners that primarily rely on file size or age, AegisStore combines **usage intelligence, machine learning, dependency awareness, risk assessment, and live system telemetry** to make safer and more meaningful recommendations.

---

## 🚀 Live Demo

🌐 **Streamlit Dashboard**

https://aegisstore-9tssxb85wbgqe3j4z79c9q.streamlit.app/

💻 **GitHub Repository**

https://github.com/SHIVANI11233/aegisstore

---

# 🎯 Problem Statement

Modern Linux systems accumulate large amounts of data over time:

- Unused files
- Duplicate files
- Old project artifacts
- Temporary files
- Logs and caches
- Large files with little future value
- Files that may still be required by applications or system components

Traditional cleanup tools generally use simple rules such as:

```text
Large file + old file = delete
````

This can be unsafe because **age and size alone do not determine whether a file is valuable or safe to remove**.

AegisStore addresses this problem by asking:

> **"What is this file doing, how likely is it to be useful again, how much storage does it consume, and is it safe to optimize right now?"**

---

# 💡 Solution

AegisStore creates an intelligent storage decision pipeline:

```text
                    Linux / Ubuntu
                         │
                         ▼
                Filesystem Scanner
                         │
                         ▼
               Usage Intelligence
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
        Duplicates    File Usage    Metadata
             │           │           │
             └───────────┼───────────┘
                         ▼
                 ML Future Usage
                    Prediction
                         │
                         ▼
             Cleanup / Archive Engine
                         │
                         ▼
                Risk Assessment
                         │
                         ▼
               Live System Load
                 CPU / RAM / I/O
                         │
                         ▼
                Decision Engine
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       KEEP           REVIEW        OPTIMIZE
                                      │
                              ┌───────┴───────┐
                              ▼               ▼
                          CLEANUP          ARCHIVE
                         / DEFER
                              │
                              ▼
                     Explanation + Audit
                              │
                              ▼
                     Streamlit Dashboard
```

---

# ✨ Key Features

## 1. 🔍 Intelligent Filesystem Scanning

AegisStore scans a controlled filesystem location and collects information such as:

* File path
* File size
* Access time
* Modification time
* SHA-256 hash
* File classification
* Usage characteristics

The scanner also avoids unnecessary directories such as:

```text
.git
node_modules
__pycache__
.venv
```

---

# 2. 📊 Usage Intelligence

AegisStore analyzes how files are being used rather than relying only on their age.

Files can be classified into:

| Profile    | Meaning                     |
| ---------- | --------------------------- |
| 🔥 HOT     | Frequently or recently used |
| 🟡 WARM    | Moderately used             |
| ❄️ COLD    | Rarely used                 |
| ⚫ INACTIVE | Little or no observed usage |

Usage features include:

* Access frequency
* Recent access ratio
* Days since last access
* Modification age
* Historical usage

---

# 3. 🤖 Future Usage Prediction

AegisStore uses a machine-learning model to estimate whether a file is likely to be accessed again.

### Model

**Random Forest Classifier**

The model considers features including:

```text
access_count_7d
access_count_30d
access_count_90d
total_access_count
days_since_last_access
recent_access_ratio
size_bytes
days_since_modified
```

The model produces a:

```text
Future Usage Probability
```

which is used as an advisory signal for recommendations.

### Prototype Evaluation

The controlled synthetic evaluation achieved approximately:

| Metric    |  Score |
| --------- | -----: |
| Accuracy  | 93.33% |
| Precision | 96.53% |
| Recall    | 93.73% |
| F1 Score  | 95.11% |
| ROC-AUC   | 98.45% |

> ⚠️ These are **controlled synthetic/prototype results**, not production performance on a real Ubuntu population.

---

# 4. ♻️ Duplicate Detection

AegisStore calculates SHA-256 hashes to identify duplicate files.

Example:

```text
file_A.zip ─────┐
file_B.zip ─────┼──► Same SHA-256 → Duplicate
file_C.zip ─────┘
```

Duplicate files can significantly increase storage usage without providing additional value.

---

# 5. 🧠 Explainable Recommendations

AegisStore does not simply output:

```text
DELETE file
```

Instead, it provides recommendations such as:

```text
KEEP
CLEANUP
ARCHIVE
REVIEW
```

Each recommendation contains an explanation based on signals such as:

* Future usage probability
* File age
* File size
* Duplicate status
* Usage profile
* Reproducibility
* Safety context

---

# 6. 🛡️ Risk-Adaptive Decision Engine

AegisStore introduces a risk layer between recommendation and optimization.

Each candidate receives a:

```text
Risk Score: 0 – 100
```

and a corresponding risk tier:

```text
LOW
MEDIUM
HIGH
```

The decision engine can produce actions such as:

```text
AUTOMATE
SCHEDULE
APPROVAL_REQUIRED
DEFER
SKIP
```

This prevents the system from treating every cleanup candidate equally.

---

# 7. 🔒 Dependency-Aware Safety

Before optimization is considered, AegisStore checks whether a file may be important to the system.

Safety signals include:

* Active/open file
* Package-manager ownership
* Git tracking
* Symbolic link
* Symlink target
* systemd references
* cron references

For example:

```text
Package-owned file
       │
       ▼
    REVIEW
       │
       X
 No automatic optimization
```

This makes the system **recommendation-first rather than deletion-first**.

---

# 8. ⚡ Live System Load Awareness

AegisStore monitors the current system state using:

* CPU utilization
* RAM utilization
* I/O wait
* Disk read activity
* Disk write activity

System state is categorized as:

```text
NORMAL
BUSY
CRITICAL
```

If the system is busy, optimization can be deferred.

Example:

```text
CPU: 81%
I/O Wait: 14%

       ↓

System Busy

       ↓

DEFER optimization
```

This allows AegisStore to consider not only **what action to take**, but also **when it is safe to take it**.

---

# 9. 🕐 Energy / Performance-Aware Scheduling

AegisStore records scheduling decisions such as:

```text
DEFERRED
RETRIED
EXECUTED
```

The dashboard can display a timeline such as:

```text
14:02:11
DEFERRED
CPU 81% | RAM 74% | I/O Wait 14%

        ↓

02:00:04
EXECUTED
CPU 9% | System load within safe limits
```

This demonstrates that optimization can be aligned with system workload instead of blindly running at any time.

> AegisStore does not require a background daemon or uncontrolled autonomous scheduler.

---

# 10. 🔄 Counterfactual Explanations

AegisStore can answer:

> **"What would have changed the decision?"**

For example:

```text
Current Risk: 72
Action: REVIEW

If the file were 7 days newer:

Risk: 62
Action: SCHEDULE
```

This makes the decision engine more transparent and easier to understand.

Counterfactual explanations are generated by re-evaluating the existing decision engine with controlled input changes.

---

# 11. 📈 Storage Forecasting

AegisStore analyzes historical storage usage to estimate future storage requirements.

The forecasting module provides:

* Current storage utilization
* Growth rate
* Estimated time to storage thresholds
* Forecast horizon
* Sample count
* Forecast quality

Example:

```text
Current Usage       : 72%
Estimated Growth    : 1.8 GB/day

85% threshold       : ~7 days
90% threshold       : ~10 days
95% threshold       : ~13 days
```

---

# 12. 🧹 Cleanup Recommendations

AegisStore identifies files that may be suitable for cleanup based on multiple signals.

Example:

```text
Duplicate
+
Low future-use probability
+
Large storage impact
+
No safety flags

        ↓

CLEANUP
```

The system does **not blindly delete files**.

---

# 13. 📦 Archive Recommendations

Some files may have low near-term usage but still have long-term value.

Instead of deleting them, AegisStore can recommend:

```text
ARCHIVE
```

This is particularly useful for:

* Old project artifacts
* Historical datasets
* Large logs
* Rarely accessed files
* Backup-like data

---

# 14. 🗑️ Reversible Quarantine

AegisStore uses a controlled quarantine workflow for supported file operations.

Instead of immediately destroying data:

```text
Original File
     │
     ▼
Quarantine
     │
     ▼
Audit Log
```

The operation can be tracked through the application's audit system.

The design philosophy is:

> **Recommend first. Execute carefully. Keep the user in control.**

---

# 15. 🧾 Audit Logging

AegisStore maintains an audit trail of important actions and decisions.

Examples include:

```text
CLEANUP
ARCHIVE
DEFERRED
RETRIED
QUARANTINE
```

Each event can contain information such as:

* Timestamp
* File path
* Action
* Reason
* System load
* Quarantine location
* Reversibility

This improves transparency and accountability.

---

# 16. 🛡️ Threat Model & Safety Guarantees

AegisStore follows several safety principles:

### No uncontrolled deletion

The system does not automatically delete arbitrary files.

### Open files are protected

Files currently used by active processes are treated as unsafe optimization candidates.

### Dependency awareness

Package-owned, Git-tracked, symlink-related, systemd-referenced, and cron-referenced files can be flagged.

### Risk-based gating

Recommendations are evaluated using risk and safety signals.

### Load-aware deferral

Optimization can be postponed when system resources are under heavy load.

### Human-in-the-loop

The final decision remains with the user.

---

# 🧩 Technology Stack

## Programming

* Python 3.12+
* SQLite

## AI / Machine Learning

* Scikit-learn
* Random Forest
* NumPy

## System Monitoring

* psutil

## Dashboard

* Streamlit
* Pandas

## Storage Analysis

* SHA-256
* SQLite usage history

## Development

* Git
* GitHub
* Ubuntu / Linux
* WSL
* Python Virtual Environment

---

# 📁 Project Structure

```text
aegisstore/
│
├── aegisstore/
│   ├── __init__.py
│   ├── scanner.py
│   ├── context.py
│   ├── db.py
│   ├── usage_history.py
│   ├── usage_intelligence.py
│   ├── usage_analyzer.py
│   ├── future_usage_model.py
│   ├── ml_training.py
│   ├── predictor.py
│   ├── storage_intelligence.py
│   ├── recommendation_engine.py
│   ├── decision_engine.py
│   ├── safety_gate.py
│   ├── counterfactual.py
│   └── ...
│
├── tests/
│   ├── ...
│
├── dashboard.py
├── demo_setup.py
├── seed_history.py
├── test_scan.py
├── test_override.py
├── requirements.txt
├── README.md
├── DEPLOYMENT.md
├── LICENSE
└── .env.example
```

---

# ⚙️ Installation

## 1. Clone the repository

```bash
git clone https://github.com/SHIVANI11233/aegisstore.git
cd aegisstore
```

---

## 2. Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# ▶️ Running AegisStore

Launch the Streamlit dashboard:

```bash
streamlit run dashboard.py
```

The dashboard will be available locally through the Streamlit URL shown in the terminal.

---

# 🧪 Running Tests

Run the complete test suite:

```bash
pytest -q
```

Current project verification:

```text
32 passed
```

Compile-check the dashboard:

```bash
python -m py_compile dashboard.py
```

---

# 🖥️ Dashboard Workflow

The recommended workflow is:

```text
1. Open Dashboard
       ↓
2. Select controlled scan directory
       ↓
3. Run Scan
       ↓
4. Analyze file usage
       ↓
5. View duplicate files
       ↓
6. Review future-use predictions
       ↓
7. Review cleanup/archive recommendations
       ↓
8. Inspect risk score
       ↓
9. Review safety context
       ↓
10. Check scheduling timeline
       ↓
11. Review counterfactual explanation
       ↓
12. User decides whether to act
```

---

# 🔐 Safety Design

AegisStore is intentionally designed as a **recommendation-first system**.

It is **not** intended to function as an unrestricted filesystem deletion tool.

The architecture prioritizes:

```text
Analyze
   ↓
Predict
   ↓
Explain
   ↓
Assess Risk
   ↓
Check Safety
   ↓
Recommend
   ↓
User Decision
   ↓
Controlled Action
```

---

# 🎯 Design Philosophy

AegisStore follows five core principles:

### 1. Intelligence

Understand file behavior rather than relying only on age and size.

### 2. Safety

Never assume that an old file is safe to remove.

### 3. Explainability

Every important recommendation should have a reason.

### 4. Adaptability

System load and environmental conditions should influence optimization timing.

### 5. Human Control

The system recommends; the user decides.

---

# 📊 What Makes AegisStore Different?

Traditional storage tools often answer:

> **"Where is my storage being used?"**

AegisStore aims to answer:

> **"What is using my storage, how valuable is it likely to be in the future, what should I do about it, why, and is now a safe time to act?"**

### Comparison

| Capability                  | Traditional Cleaner | AegisStore |
| --------------------------- | ------------------- | ---------- |
| File scanning               | ✅                   | ✅          |
| Duplicate detection         | ✅                   | ✅          |
| Age-based analysis          | ✅                   | ✅          |
| Usage intelligence          | Limited             | ✅          |
| Future usage prediction     | ❌                   | ✅          |
| ML-assisted recommendations | ❌                   | ✅          |
| Risk scoring                | ❌                   | ✅          |
| Dependency awareness        | Limited             | ✅          |
| CPU/RAM/I/O awareness       | ❌                   | ✅          |
| Load-aware deferral         | ❌                   | ✅          |
| Counterfactual explanations | ❌                   | ✅          |
| Audit trail                 | Limited             | ✅          |
| Human-in-the-loop           | Varies              | ✅          |
| Controlled quarantine       | Varies              | ✅          |

---

# 🏆 Project Highlights

AegisStore combines several layers into a single storage intelligence pipeline:

```text
Filesystem Intelligence
        +
Usage Analytics
        +
Machine Learning
        +
Duplicate Detection
        +
Storage Forecasting
        +
Risk Assessment
        +
Dependency Awareness
        +
Live System Telemetry
        +
Scheduling
        +
Explainability
        +
Auditability
```

This combination transforms storage cleanup from a simple rule-based task into a **risk-aware decision-support system**.

---

# ⚠️ Limitations

AegisStore is a project/prototype and has intentionally defined boundaries.

### Usage history

File usage history is based on events recorded by AegisStore rather than automatically monitoring every filesystem access on the system.

### ML training

The current model evaluation uses controlled/synthetic data and should not be interpreted as production-grade performance.

### Scheduling

The project demonstrates energy/performance-aware scheduling logic but does not implement an unrestricted background daemon.

### Filesystem scope

Scanning should be performed on controlled directories rather than blindly targeting the entire operating system.

### Recommendations

AegisStore provides recommendations and safety analysis; it does not guarantee that every recommendation is correct.

---

# 🔮 Future Scope

Potential future improvements include:

* Real filesystem event monitoring using `inotify`
* Larger real-world usage datasets
* More advanced time-series forecasting
* Personalized storage behavior models
* Cloud/object-storage integration
* Intelligent compression recommendations
* Automatic archive tier selection
* Container-aware storage optimization
* Better dependency graph analysis
* More advanced anomaly detection
* Desktop notifications
* Optional background scheduling service

---

# 👩‍💻 Project Team

**Shivani Bhosale**

B.Tech — Artificial Intelligence & Data Science
Vishwakarma Institute of Technology, Pune

---

# 📜 License

This project is licensed under the terms specified in the repository's `LICENSE` file.

---

# ⭐ Final Project Statement

> **AegisStore is a risk-adaptive AI-powered storage intelligence system for Linux that understands file usage, predicts future value, identifies redundancy, forecasts storage growth, evaluates system and dependency risks, explains its decisions, and keeps the user in control of optimization.**

---

## 🔗 Links

* 🌐 **Live Dashboard:** [https://aegisstore-9tssxb85wbgqe3j4z79c9q.streamlit.app/](https://aegisstore-9tssxb85wbgqe3j4z79c9q.streamlit.app/)
* 💻 **GitHub:** [https://github.com/SHIVANI11233/aegisstore](https://github.com/SHIVANI11233/aegisstore)

---

### Built with Python, Machine Learning, Linux, and a safety-first mindset. 🛡️

````

### One important thing

Since your README is now a **final project README**, I recommend replacing the current GitHub README with this version and then committing it as:

```bash
git add README.md
git commit -m "Finalize project README"
git push origin main
````

That will make the repository look much more professional for **hackathon judges, professors, recruiters, and interviewers**.
