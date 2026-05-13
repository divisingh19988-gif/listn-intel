"""One-off helper: for each tracked competitor, search Meta Ad Library and
extract the page's Meta page_id from the rendered DOM. Print a Python dict
literal ready to paste into scrape_ads.py.

Usage: python3 scripts/discover_page_ids.py
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scrapers.scrape_ads import COMPETITORS, COMPETITOR_SEARCH_PLAN, dismiss_overlays  # noqa: E402

from playwright.sync_api import sync_playwright


def discover_one(page, competitor):
    """Try each search term in the plan, return the first page_id found."""
    plan = COMPETITOR_SEARCH_PLAN.get(competitor, [(competitor, "page")])
    for search_term, search_type in plan:
        q = search_term.replace(" ", "%20")
        url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status=all&ad_type=all&country=ALL"
            f"&is_targeted_country=false"
            f"&q={q}&search_type={search_type}&media_type=all"
        )
        print(f"  [{search_type}] q={search_term!r}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"    nav failed: {e}")
            continue
        page.wait_for_timeout(3000)
        dismiss_overlays(page)
        page.wait_for_timeout(1500)

        html = page.content()
        # Meta embeds the page in its React state as "page_id":"<digits>"
        matches = re.findall(r'"page_id":"(\d+)"', html)
        if matches:
            from collections import Counter
            # Heaviest reference count = the searched-for page; tail = other
            # pages cross-referenced (sponsored, related, etc.). Threshold of
            # 3 to skip incidental mentions.
            counts = Counter(matches).most_common(3)
            page_id, count = counts[0]
            if count >= 3:
                print(f"    found page_id={page_id} (referenced {count}x; "
                      f"runners-up: {counts[1:] if len(counts) > 1 else []})")
                return page_id
            print(f"    weak signal ({counts}) — trying next")
            continue
        print(f"    no page_id in DOM")
    return None


def main():
    results = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = ctx.new_page()
        page.goto("https://www.facebook.com/ads/library/",
                  wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        dismiss_overlays(page)

        for competitor in COMPETITORS:
            print(f"\n→ {competitor}")
            pid = discover_one(page, competitor)
            results[competitor] = pid
            time.sleep(1)

        browser.close()

    print("\n\n# === paste this into scrape_ads.py ===")
    print("COMPETITOR_PAGE_IDS = {")
    for comp, pid in results.items():
        print(f"    {comp!r:25s}: {pid!r},")
    print("}")


if __name__ == "__main__":
    main()
