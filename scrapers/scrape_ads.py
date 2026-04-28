"""
Meta Ad Library web scraper — no API token required.
Uses Playwright (headless Chromium) + text parsing of the rendered page.
Searches by advertiser/page name so results are the competitor's own ads.
"""

import json
import re
import time
from datetime import date, datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

COMPETITORS = [
    "Remento",
    "Meminto",
    "StoryWorth",
    "Storykeeper",
    "Tell me",
    "Keepsake",
    "HereAfter AI",
    "No Story Lost",
]

# Words that MUST appear in the page_name for an ad to be counted as that competitor's.
# Keeps broad searches (e.g. "Tell me", "Keepsake") from pulling in unrelated pages.
COMPETITOR_PAGE_FILTER = {
    "Remento":       ["remento"],
    "Meminto":       ["meminto"],
    "StoryWorth":    ["storyworth", "story worth"],
    "Storykeeper":   ["storykeeper", "story keeper"],
    "Tell me":       ["tell me", "tellme"],
    "Keepsake":      ["keepsake"],
    "HereAfter AI":  ["hereafter"],
    "No Story Lost": ["no story lost", "nostorylost"],
}

# Each entry is a list of (search_term, search_type) pairs tried in order.
# The first one to return matching ads wins.
COMPETITOR_SEARCH_PLAN = {
    "Remento":       [("Remento",        "page")],
    "Meminto":       [("Meminto",        "page")],
    "StoryWorth":    [("StoryWorth",     "page"),
                      ("StoryWorth",     "keyword_unordered")],
    "Storykeeper":   [("Storykeeper",    "page")],
    "Tell me":       [("Tell me",        "page"),
                      ("TellMe Stories", "page"),
                      ("Tell Me",        "keyword_unordered")],
    "Keepsake":      [("Keepsake",       "page")],
    "HereAfter AI":  [("HereAfter AI",   "page"),
                      ("HereAfter",      "page"),
                      ("HereAfter AI",   "keyword_unordered")],
    "No Story Lost": [("No Story Lost",  "page"),
                      ("NoStoryLost",    "page"),
                      ("No Story Lost",  "keyword_unordered")],
}

AD_LIBRARY_BASE = "https://www.facebook.com/ads/library/"

PLATFORM_NAMES = ["Facebook", "Instagram", "Messenger", "Audience Network", "WhatsApp"]


def is_competitor_ad(ad, competitor):
    """Return True only if the page_name matches the competitor's known page."""
    page = (ad.get("page_name") or "").lower()
    if not page:
        return False
    keywords = COMPETITOR_PAGE_FILTER.get(competitor, [competitor.lower()])
    return any(kw in page for kw in keywords)


def build_url(search_term, search_type="page"):
    q = search_term.replace(" ", "%20")
    return (
        f"{AD_LIBRARY_BASE}"
        f"?active_status=all&ad_type=all&country=US"
        f"&q={q}&search_type={search_type}&media_type=all"
    )


def dismiss_overlays(page):
    for sel in [
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept All")',
        'button:has-text("Accept Cookies")',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
    ]:
        try:
            page.click(sel, timeout=2000)
            return
        except Exception:
            pass


def scroll_and_load(page, rounds=5):
    for _ in range(rounds):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)


def parse_date(s):
    """Parse 'Month D, YYYY' or 'Mon D, YYYY' into ISO date string."""
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date().isoformat()
        except ValueError:
            pass
    return s.strip()


def days_between(start_iso, stop_iso):
    try:
        d1 = date.fromisoformat(start_iso)
        d2 = date.fromisoformat(stop_iso) if stop_iso else date.today()
        return (d2 - d1).days
    except Exception:
        return None


def parse_ad_block(block_text, competitor):
    """
    Parse one ad card's text block into structured fields.

    The visible text layout from the Ad Library is:
        Active | Inactive
        Library ID: <id>
        <start_date> - <stop_date>  (or just <start_date>)
        Platforms
        [N ads use this creative and text]
        See ad details | See summary details
        <Page Name>
        Sponsored
        <ad copy>
        [headline / link title]
        [cta]
    """
    lines = [l.strip() for l in block_text.split("\n") if l.strip()]

    ad = {
        "competitor": competitor,
        "ad_id": None,
        "status": None,
        "page_name": None,
        "ad_copy": None,
        "headline": None,
        "cta": None,
        "platforms": [],
        "impression_lower": None,
        "impression_upper": None,
        "start_date": None,
        "stop_date": None,
        "days_running": None,
    }

    # Status (English + German)
    if lines and lines[0] in ("Active", "Inactive", "Aktiv", "Inaktiv"):
        ad["status"] = "Active" if lines[0] in ("Active", "Aktiv") else "Inactive"

    # Library ID (English: "Library ID:" / German: "Bibliotheks-ID:")
    id_match = re.search(r"(?:Library ID|Bibliotheks-ID):\s*(\d+)", block_text)
    if id_match:
        ad["ad_id"] = id_match.group(1)

    # Date range — handles both EN "Jan 1, 2024" and DE "01.01.2024" formats
    date_range_match = re.search(
        r"(\w+ \d{1,2},\s*\d{4})\s*[-–]\s*(\w+ \d{1,2},\s*\d{4})",
        block_text,
    )
    if date_range_match:
        ad["start_date"] = parse_date(date_range_match.group(1))
        ad["stop_date"] = parse_date(date_range_match.group(2))
    else:
        # German numeric date: DD.MM.YYYY bis DD.MM.YYYY
        de_range = re.search(
            r"(\d{2}\.\d{2}\.\d{4})\s*(?:bis|-|–)\s*(\d{2}\.\d{2}\.\d{4})",
            block_text,
        )
        if de_range:
            def parse_de(s):
                try:
                    return datetime.strptime(s.strip(), "%d.%m.%Y").date().isoformat()
                except ValueError:
                    return s.strip()
            ad["start_date"] = parse_de(de_range.group(1))
            ad["stop_date"] = parse_de(de_range.group(2))
        else:
            single_date = re.search(r"(\w+ \d{1,2},\s*\d{4})", block_text)
            if single_date:
                ad["start_date"] = parse_date(single_date.group(1))
            else:
                de_single = re.search(r"(\d{2}\.\d{2}\.\d{4})", block_text)
                if de_single:
                    try:
                        ad["start_date"] = datetime.strptime(
                            de_single.group(1), "%d.%m.%Y"
                        ).date().isoformat()
                    except ValueError:
                        pass

    if ad["start_date"]:
        ad["days_running"] = days_between(ad["start_date"], ad["stop_date"])

    # Impression range — "1K-5K impressions" or "10,000-50,000"
    imp_match = re.search(
        r"([\d,]+[KkMm]?\s*[-–]\s*[\d,]+[KkMm]?)\s*impressions",
        block_text,
        re.IGNORECASE,
    )
    if imp_match:
        parts = re.split(r"[-–]", imp_match.group(1))
        ad["impression_lower"] = parts[0].strip()
        ad["impression_upper"] = parts[1].strip() if len(parts) > 1 else None

    # Platforms — scan all lines for known platform names
    for line in lines:
        for pname in PLATFORM_NAMES:
            if pname.lower() in line.lower() and pname not in ad["platforms"]:
                ad["platforms"].append(pname)

    # Page name + ad copy: the page name is immediately before "Sponsored" or "Anzeige" (DE)
    sponsored_idx = next(
        (i for i, l in enumerate(lines) if l.lower() in ("sponsored", "anzeige")), None
    )
    if sponsored_idx is not None and sponsored_idx > 0:
        ad["page_name"] = lines[sponsored_idx - 1]
        # Ad copy is the next non-boilerplate line after "Sponsored"
        copy_lines = []
        for l in lines[sponsored_idx + 1 :]:
            if l.lower() in ("learn more", "shop now", "sign up", "get started",
                             "download", "install now", "book now", "contact us",
                             "watch more", "send message", "subscribe"):
                ad["cta"] = l
                break
            if len(l) > 15:
                copy_lines.append(l)
            if len(copy_lines) >= 4:
                break
        if copy_lines:
            ad["ad_copy"] = " ".join(copy_lines[:3])
            if len(copy_lines) > 1:
                ad["headline"] = copy_lines[-1] if len(copy_lines[-1]) < 100 else None

    return ad


def scrape_competitor(page, competitor):
    """Work through the search plan for this competitor; return the first batch that yields matches."""
    search_plan = COMPETITOR_SEARCH_PLAN.get(competitor, [(competitor, "page")])

    for search_term, search_type in search_plan:
        url = build_url(search_term, search_type)
        print(f"  [{search_type}] q={search_term!r}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PWTimeout:
            print(f"  TIMEOUT — skipping")
            continue

        page.wait_for_timeout(3000)
        dismiss_overlays(page)
        page.wait_for_timeout(1000)

        body_text = page.inner_text("body")

        if "No results found" in body_text or "Keine Ergebnisse" in body_text:
            print(f"  No results — trying next")
            continue

        if not re.search(r"(?:Library ID|Bibliotheks-ID):", body_text):
            print(f"  No ad cards — trying next")
            continue

        scroll_and_load(page, rounds=5)
        body_text = page.inner_text("body")

        raw_blocks = re.split(r"(?=(?:Library ID|Bibliotheks-ID):)", body_text)
        raw_blocks = [b for b in raw_blocks if re.search(r"(?:Library ID|Bibliotheks-ID):", b)]

        ads = [parse_ad_block(block, competitor) for block in raw_blocks]
        ads = [a for a in ads if is_competitor_ad(a, competitor)]

        if ads:
            return ads
        print(f"  0 matching ads after filter — trying next")

    print(f"  No matching ads found for {competitor} across all search strategies")
    return []


def main():
    today = date.today().isoformat()
    output_file = f"ads_scraped_{today}.json"

    all_results = {}
    total_ads = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = ctx.new_page()

        # Prime cookies on the landing page
        print("Loading Ad Library landing page...")
        page.goto(AD_LIBRARY_BASE, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)
        dismiss_overlays(page)
        page.wait_for_timeout(1000)

        for competitor in COMPETITORS:
            print(f"\nFetching ads for: {competitor}")
            ads = scrape_competitor(page, competitor)
            all_results[competitor] = ads
            total_ads += len(ads)
            print(f"  => {len(ads)} ads parsed")
            time.sleep(2)

        browser.close()

    output = {
        "fetched_date": today,
        "method": "web_scrape",
        "total_ads": total_ads,
        "competitors": all_results,
    }

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    # Summary
    print(f"\n{'='*55}")
    print(f"  Total ads collected: {total_ads}")
    print(f"  Saved to:            {output_file}")
    print(f"{'='*55}")
    for comp, ads in all_results.items():
        print(f"  {comp:<20} {len(ads):>3} ads")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
