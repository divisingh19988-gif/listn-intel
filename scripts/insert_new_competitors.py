#!/usr/bin/env python3
"""
One-shot script to add the three adjacent/lateral competitors (ElliQ, Papa,
friend.com) to the Supabase `competitors` table.

The hardcoded fallback lists in `scrapers/scrape_ads.py`, `scrapers/fetch_ads.py`,
`scrapers/ai_readiness_check.py`, and `scrapers/seo_monitor.py` have already been
updated. This script just keeps Supabase in sync so the dashboards (which read
from Supabase first) show them.

Idempotent: if a competitor with the same name already exists, it's updated
in place instead of inserted again.

Run:
    python3 scripts/insert_new_competitors.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from lib.supabase_client import (  # noqa: E402
    COMPETITORS_TABLE,
    add_competitors,
    get_client,
    update_competitors,
)


# Best-guess values. App Store IDs left None on purpose — use the Admin page's
# "Discover with Claude" flow to populate them after the rows exist, so the
# values are verified rather than fabricated.
NEW_COMPETITORS = [
    {
        "name": "ElliQ",
        "meta_search_terms": ["ElliQ", "Intuition Robotics"],
        "seo_domain": "elliq.com",
        "appstore_id": None,
        "active": True,
        "notes": "Adjacent: robot companion for seniors. Meta page_id 434160116949836. Runs Meta ads.",
    },
    {
        "name": "Papa",
        "meta_search_terms": ["Papa Inc", "Join Papa"],
        "seo_domain": "papa.com",
        "appstore_id": None,
        "active": True,
        "notes": "Adjacent: human caregiving / companionship marketplace. No Meta ads at integration time.",
    },
    {
        "name": "friend.com",
        "meta_search_terms": ["friend.com", "Friend AI"],
        "seo_domain": "friend.com",
        "appstore_id": None,
        "active": True,
        "notes": "Adjacent: AI friend pendant (hardware). No Meta ads at integration time.",
    },
]


def main() -> int:
    client = get_client()
    if client is None:
        print(
            "ERROR: Could not connect to Supabase. Check SUPABASE_URL and "
            "SUPABASE_KEY in .env or st.secrets.",
            file=sys.stderr,
        )
        return 1

    # Pull existing rows once so we can choose insert vs update by name.
    resp = client.table(COMPETITORS_TABLE).select("id,name").execute()
    existing = {row["name"]: row["id"] for row in (resp.data or [])}

    inserted, updated = [], []
    for comp in NEW_COMPETITORS:
        name = comp["name"]
        if name in existing:
            update_competitors(client, existing[name], comp)
            updated.append(name)
            print(f"  ↺  updated existing row: {name}")
        else:
            add_competitors(client, **comp)
            inserted.append(name)
            print(f"  +  inserted: {name}")

    print()
    print(f"Done. Inserted {len(inserted)}, updated {len(updated)}.")
    if inserted:
        print(f"  Inserted: {', '.join(inserted)}")
    if updated:
        print(f"  Updated:  {', '.join(updated)}")
    print()
    print(
        "Next: open the Admin page → run 'Discover with Claude' on each new row "
        "to fill App Store IDs and confirm Meta search terms."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
