"""
Dashboard hygiene review — Claude reads the current dashboard state and
surfaces non-deterministic staleness issues that rule-based filters can't
catch: wrong dates baked into the data (Father's Day = June 15), placeholder
strings left in production (LISTN_AI_READINESS_MILESTONES with XX/YY/ZZ
keys), brand renames only half-applied, contradictions between cluster
content and tracked competitors, methodology markers from a previous era.

This is the natural complement to lib/completion_log.py: that one auto-
archives anything with a deadline date that has clearly passed; this one
catches problems the date math can't see.

Runs in two contexts:
  1. On-demand from the Admin page (button click).
  2. From cron: `python -m lib.dashboard_hygiene` — writes findings to
     data/hygiene_review.json so the dashboard surfaces them next render.

Cached findings live in data/hygiene_review.json (tracked) so the most
recent review is visible to anyone opening the dashboard, and the audit
trail of past reviews survives across machines.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
REVIEW_PATH = ROOT / "data" / "hygiene_review.json"
HYGIENE_MODEL = "claude-opus-4-7"

HYGIENE_SYSTEM_PROMPT = (
    "You are a brutal dashboard hygiene reviewer for Listn Intel — a "
    "competitive intelligence dashboard for Listn, a pre-launch voice-first "
    "AI memory app for older adults (65+). Public launch is June 10, 2026. "
    "The dashboard tracks Meta ads, SEO keywords, AI readiness, and a content "
    "roadmap across ~10 competitors.\n\n"
    "Your job: find data that is WRONG, STALE, or CONTRADICTORY. Be specific "
    "and actionable. Generic findings like 'review competitors' or 'monitor "
    "closely' are FORBIDDEN — each finding must point at a specific fixable "
    "thing.\n\n"
    "PATTERNS TO LOOK FOR\n"
    "- FACTUAL ERRORS: Verify any date against your knowledge. US Mother's "
    "Day is the 2nd Sunday of May; Father's Day is the 3rd Sunday of June; "
    "Memorial Day is the last Monday of May; Thanksgiving is the 4th "
    "Thursday of November. If a date in the data doesn't match the named "
    "holiday for that year, that's a HIGH severity factual error.\n"
    "- PLACEHOLDERS: Look for 'FIXME', 'TODO', 'XX', 'YY', 'ZZ', 'TBD', or "
    "obviously synthetic identifiers that should have been replaced.\n"
    "- STALE: Methodology markers older than 90 days that nobody mentions "
    "anymore. Clusters or posts with deadlines way in the past that didn't "
    "auto-archive (means the sweep logic has a bug or those items were "
    "skipped).\n"
    "- CONTRADICTIONS: A roadmap post's publish_by AFTER its event_date. "
    "A cluster's keywords referencing a brand not in any active context. "
    "Repeated brand spellings that disagree (e.g. 'Tell Mel' vs 'Tellmel').\n"
    "- TIME DRIFT: Items that were time-relevant when added but are now "
    "stale given today's date.\n\n"
    "SEVERITY\n"
    "- high: factually wrong data visible on the dashboard right now\n"
    "- medium: stale or contradictory data that misleads readers\n"
    "- low: cleanup hygiene with low impact\n\n"
    "If the dashboard looks clean, return an empty findings array. Do NOT "
    "manufacture problems to look thorough. Five real findings beat fifty "
    "manufactured ones.\n\n"
    "DESIGN INVARIANTS (do not flag these as bugs)\n"
    "- Evergreen content (event_date=null) is intentional: it stays on the "
    "dashboard indefinitely until manually retired. Do NOT flag evergreen "
    "items with publish_by < today as 'should auto-archive' — that only "
    "applies to items with an event_date. The overdue red border is the "
    "designed nag signal.\n"
    "- Past-deadline items in ACTIVE sections are a bug; past-deadline items "
    "in ARCHIVED sections are normal and expected."
)

HYGIENE_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "category": {
                        "type": "string",
                        "enum": ["factual", "placeholder", "stale", "contradiction", "time_drift", "other"],
                    },
                    "title": {"type": "string"},
                    "details": {"type": "string"},
                    "suggested_fix": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["severity", "category", "title", "details", "suggested_fix", "location"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["findings"],
    "additionalProperties": False,
}


def _serialize_state(today: date) -> dict:
    """Build the dashboard snapshot Claude reviews. Imports lazily to avoid
    pulling Streamlit into a CLI / cron path.

    Filters past-deadline items out of the active view so Claude doesn't
    flag them as "stale data still on the dashboard" — they were already
    auto-archived. The completion_history block carries those separately,
    clearly labelled as ARCHIVED."""
    from lib.synthesis import SEO_CLUSTERS, SEO_ROADMAP_POSTS

    clusters_view = []
    for c in SEO_CLUSTERS:
        deadline = c.get("deadline")
        if deadline is not None and deadline < today:
            continue  # already archived to completion_history below
        clusters_view.append({
            "name": c["name"],
            "window": c["window"],
            "deadline": deadline.isoformat() if deadline else None,
            "keyword_count": len(c.get("keywords", [])),
            "sample_keywords": [k[0] for k in c.get("keywords", [])[:3]],
        })

    posts_view = []
    for p in SEO_ROADMAP_POSTS:
        event_date = p.get("event_date")
        if event_date is not None and event_date < today:
            continue  # already archived
        posts_view.append({
            "num": p["num"],
            "title": p["title"],
            "publish_by": p["publish_by"].isoformat(),
            "event_date": event_date.isoformat() if event_date else None,
            "window": p["window"],
            "primary_keyword": p["primary"][0],
        })

    history: list[dict] = []
    try:
        from lib.completion_log import get_history
        history = get_history(limit=20)
    except Exception:
        pass

    methodology = {}
    try:
        from importlib import import_module
        trends_globals = {}
        trends_path = ROOT / "pages" / "8_Trends.py"
        if trends_path.exists():
            # Read constants without executing Streamlit calls.
            source = trends_path.read_text()
            # METHODOLOGY_CHANGE_DATE and LISTN_AI_READINESS_MILESTONES are
            # top-level constants — extract via simple parse so we don't have
            # to import the page (which triggers st.set_page_config).
            import re
            m = re.search(r'METHODOLOGY_CHANGE_DATE\s*=\s*"([^"]+)"', source)
            if m:
                methodology["meta_methodology_change_date"] = m.group(1)
            m2 = re.search(
                r'LISTN_AI_READINESS_MILESTONES[^=]*=\s*\{([^}]+)\}',
                source, re.DOTALL,
            )
            if m2:
                methodology["listn_ai_readiness_milestones_raw"] = m2.group(1).strip()
    except Exception:
        pass

    return {
        "today": today.isoformat(),
        "seo_clusters": clusters_view,
        "roadmap_posts": posts_view,
        "completion_history": history,
        "methodology_constants": methodology,
    }


def _build_user_prompt(state: dict) -> str:
    """Format the dashboard state as a structured prompt for Claude."""
    return (
        f"Today's date: {state['today']}\n\n"
        "Review the following dashboard state and return findings as JSON.\n\n"
        "NOTE: The dashboard auto-archives clusters and posts whose deadline "
        "is in the past — items appearing under ACTIVE below are the ones "
        "currently visible to users. Items under ARCHIVED have already been "
        "moved off the active view and are shown here only for audit. The "
        "'overdue' red border on posts with publish_by < today but event_date "
        "in the future is intentional pre-event signal — do NOT flag it as a "
        "bug. Flag it only if publish_by gives no realistic indexing lead "
        "time vs. event_date.\n\n"
        "=== ACTIVE: SEO KEYWORD CLUSTERS (visible to users) ===\n"
        + json.dumps(state["seo_clusters"], indent=2)
        + "\n\n=== ACTIVE: CONTENT ROADMAP POSTS (visible to users) ===\n"
        + json.dumps(state["roadmap_posts"], indent=2)
        + "\n\n=== ARCHIVED: COMPLETION HISTORY (already swept off the active view) ===\n"
        + json.dumps(state["completion_history"], indent=2)
        + "\n\n=== METHODOLOGY CONSTANTS (from Trends page source) ===\n"
        + json.dumps(state["methodology_constants"], indent=2)
    )


def run_hygiene_check(today: Optional[date] = None) -> dict:
    """Call Claude, return findings dict. Side effect: writes to disk."""
    today = today or date.today()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY not set — cannot run hygiene check")
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError("anthropic package not installed") from exc

    state = _serialize_state(today)
    user_prompt = _build_user_prompt(state)

    client = Anthropic()
    response = client.messages.create(
        model=HYGIENE_MODEL,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        system=[
            {
                "type": "text",
                "text": HYGIENE_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_prompt}],
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": HYGIENE_SCHEMA},
        },
    )

    text = next((b.text for b in response.content if b.type == "text"), "")
    if not text:
        raise RuntimeError("Empty response from Claude")
    parsed = json.loads(text)

    result = {
        "reviewed_at": datetime.now().isoformat(timespec="seconds"),
        "model": HYGIENE_MODEL,
        "today": state["today"],
        "findings": parsed.get("findings", []),
        "usage": {
            "input_tokens": getattr(response.usage, "input_tokens", None),
            "output_tokens": getattr(response.usage, "output_tokens", None),
            "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", None),
        },
    }
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REVIEW_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True))
    tmp.replace(REVIEW_PATH)
    return result


def get_last_review() -> Optional[dict]:
    """Read the most recent review from disk, or None if never run."""
    if not REVIEW_PATH.exists():
        return None
    try:
        return json.loads(REVIEW_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _cli() -> int:
    """CLI entry point for cron — `python -m lib.dashboard_hygiene`."""
    try:
        result = run_hygiene_check()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    findings = result["findings"]
    print(f"Reviewed at {result['reviewed_at']} — {len(findings)} findings")
    for f in findings:
        print(f"  [{f['severity'].upper()}] {f['title']}  ({f['location']})")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
