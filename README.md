# AegisStore — Working Prototype (Must-Have Modules)

This covers the 5 "must have" items from the build plan: filesystem scanner,
context safety checks, the Risk-Adaptive Decision Engine (with live-override),
quarantine + undo with an audit log, and the Storage Story narrative.

Tested and working on Linux (this was built and verified in a Linux sandbox).

## 1. Setup (5 minutes)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`anthropic` is optional — if you don't set `ANTHROPIC_API_KEY`, the Storage
Story falls back to a clean template narrative, so the demo works with zero
internet dependency. To enable the live AI narrative:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## 2. Generate demo clutter

Don't risk pointing this at real files during rehearsal. Use the synthetic
demo disk instead:

```bash
python3 demo_setup.py ./demo_disk
```

This creates:
- an **active/hot** file (should be skipped — recently touched)
- a **duplicated + old** dataset pair (should be marked LOW risk / AUTOMATE)
- old build artifacts and logs (MEDIUM risk / SCHEDULE)
- a moderately recent file (should land as MEDIUM, lower confidence)

## 3. Run the scan

```bash
python3 -m aegisstore.cli scan ./demo_disk
```

You'll see, per file: size, age, classification, confidence, duplicate status,
context checks (active process / package owned / Git tracked), and the final
risk tier + action. Low-risk items are automatically quarantined; you'll see
`QUARANTINED -> ... integrity_verified=True`.

## 4. Show the live-override "wow moment"

This is the strongest demo beat — a scheduled/low-risk action deferring
because the *live* system is busy, even though the file itself is low risk.

Easiest way to force it live on stage: open a second terminal and run a CPU
burner right before your scan:

```bash
# terminal 2 — stress the CPU (Ctrl+C to stop)
yes > /dev/null & yes > /dev/null & yes > /dev/null &
```

Then run the scan in terminal 1 — you'll see `system load: BUSY` and any
previously LOW-risk candidate downgrade to `DEFER`. Kill the `yes` jobs
(`kill %1 %2 %3`) and re-run the scan to show it going back to `AUTOMATE`.

If you'd rather not depend on live CPU stress during the actual presentation,
there's also a deterministic version of this proof in `test_override.py` —
run it to print both scenarios side by side without touching real load.

## 5. Show audit + undo

```bash
python3 -m aegisstore.cli audit                       # see everything AegisStore has done
python3 -m aegisstore.cli undo <quarantine_file_path>  # restore a file — proves reversibility
```

## 6. Reset between rehearsals

```bash
rm -rf demo_disk quarantine aegisstore.db
python3 demo_setup.py ./demo_disk
```

## What's NOT built yet (by design, for tonight)

- Growth forecasting graph (nice-to-have — the doc's numeric example can be
  shown as a static slide if you run out of time)
- Streamlit dashboard (stretch — CLI output is judge-legible and safer to
  demo live than a UI you haven't stress-tested)
- Isolation Forest anomaly scoring, systemd packaging (stretch)

## Known limitation to be upfront about if asked

`is_active_process()` checks open file handles via `psutil`, which requires
the script to run with sufficient permission to see other processes' open
files. On most dev machines this works for user-owned processes; if a judge's
machine restricts this, mention it's a permissions boundary, not a logic gap.
