#!/usr/bin/env python3
"""
Remove Replika from every runtime data source the dashboard reads.

Two layers need scrubbing — code changes alone don't hit either:
  1. Supabase `competitors` row → soft-deleted (active=false, deleted_at=now).
  2. Cached JSON in data/ (ads_scraped_latest.json, seo_raw_latest.json) →
     Replika entries removed in place so the dashboard stops showing them
     immediately instead of waiting for the next weekly refresh.

Run:
    python3 scripts/remove_replika.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load .env so Supabase credentials are available when run from the terminal
# (Streamlit auto-loads it, standalone scripts don't).
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from lib.supabase_client import (  # noqa: E402
    COMPETITORS_TABLE,
    delete_competitors,
    get_client,
)

TARGET_NAME = "Replika"
DATA_DIR = REPO_ROOT / "data"
JSON_FILES = ["ads_scraped_latest.json", "seo_raw_latest.json"]


def scrub_supabase() -> str:
    client = get_client()
    if client is None:
        return "Supabase: SKIPPED (no SUPABASE_URL / SUPABASE_KEY configured)"

    # Wrap the network calls so a bad URL, expired key, or transient failure
    # doesn't kill the JSON-scrub step that follows. The deployed dashboard
    # uses Streamlit Cloud secrets (which we can't reach from CLI), so a
    # local-only run with a broken .env should still clean the cached JSONs.
    try:
        resp = (
            client.table(COMPETITORS_TABLE)
            .select("id,name")
            .eq("name", TARGET_NAME)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return f"Supabase: no row named '{TARGET_NAME}' found (already gone)"

        for row in rows:
            delete_competitors(client, row["id"])
        return f"Supabase: soft-deleted {len(rows)} row(s) named '{TARGET_NAME}'"
    except Exception as e:
        return f"Supabase: SKIPPED ({type(e).__name__}: {str(e)[:120]})"


def scrub_json(path: Path) -> str:
    if not path.exists():
        return f"{path.name}: not present (skipped)"

    raw = json.loads(path.read_text())
    removed = False

    # The two known shapes:
    #   ads_scraped_*.json  → {"competitors": {<name>: [ads...]}, "total_ads": N}
    #   seo_raw_*.json      → {"competitors": {<name>: {"keywords": [...]}}}
    competitors = raw.get("competitors")
    if isinstance(competitors, dict) and TARGET_NAME in competitors:
        del competitors[TARGET_NAME]
        removed = True

    # Recompute total_ads for ads files so the dashboard's headline number
    # stays consistent with the trimmed competitor list.
    if removed and isinstance(competitors, dict) and "total_ads" in raw:
        raw["total_ads"] = sum(
            len(v) if isinstance(v, list) else 0 for v in competitors.values()
        )

    if not removed:
        return f"{path.name}: no '{TARGET_NAME}' entry found"

    path.write_text(json.dumps(raw, indent=2))
    return f"{path.name}: removed '{TARGET_NAME}' entry"


def main() -> int:
    print(scrub_supabase())
    for name in JSON_FILES:
        print(scrub_json(DATA_DIR / name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
