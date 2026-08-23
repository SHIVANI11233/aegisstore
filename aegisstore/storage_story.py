"""
storage_story.py — Explainability layer.
Turns the structured scan + decision output into a plain-English narrative.
Uses the Anthropic API if ANTHROPIC_API_KEY is set; otherwise falls back to a
template so the demo still works with zero network dependency.

IMPORTANT: this module only ever reads data and returns text. It never touches
the filesystem — it has no delete/move capability, by design.
"""
import json
import os

SYSTEM_PROMPT = (
    "You are the explanation layer of AegisStore, a Linux storage optimizer. "
    "Given structured JSON about a scan, write a short, confident, plain-English "
    "'Storage Story' (3-5 sentences) a non-expert user would trust. Mention the "
    "total reclaimable size, the top reason data can be reclaimed, the confidence "
    "level, and note if any action was deferred due to system load. Do not invent "
    "numbers not present in the JSON."
)


def _template_story(summary: dict) -> str:
    parts = [
        f"Your scan found {summary['total_candidates']} optimization candidates totaling "
        f"{summary['total_reclaimable_gb']:.2f} GB of potentially reclaimable storage.",
    ]
    if summary.get("top_reason"):
        parts.append(f"Most of this is {summary['top_reason']}.")
    if summary.get("deferred_count", 0) > 0:
        parts.append(
            f"{summary['deferred_count']} action(s) were deferred because the system was under "
            f"heavy load at the time — AegisStore will re-check them automatically."
        )
    if summary.get("automated_count", 0) > 0:
        parts.append(f"{summary['automated_count']} low-risk item(s) were safely quarantined.")
    parts.append(f"Overall confidence: {summary.get('avg_confidence', 0):.0%}.")
    return " ".join(parts)


def generate_story(summary: dict) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return _template_story(summary)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(summary)}],
        )
        return "".join(block.text for block in resp.content if block.type == "text").strip()
    except Exception as e:  # network issues, missing package, etc. — never let this break the demo
        return _template_story(summary) + f"\n\n[Note: live AI narrative unavailable, showing template — {e}]"
