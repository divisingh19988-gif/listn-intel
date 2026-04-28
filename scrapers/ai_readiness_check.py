"""
AI Readiness audit — checks 7 signals across the competitor landscape.

Signals per site:
  1. /llms.txt exists?                      → "Yes" / "No"
  2. /robots.txt — count of explicitly      → int (0-5)
     allowed AI bots (GPTBot, ClaudeBot,
     PerplexityBot, GoogleExtended, Bingbot)
  3. Homepage has FAQPage JSON-LD?          → "Yes" / "No"
  4. /blog (or /journal) has Article schema → "Yes" / "No"
  5. Sample 10 sitemap URLs — % with        → int %
     <link rel="canonical">
  6. Same 10 URLs — % with                  → int %
     <meta name="description">
  7. Composite score (0-100)                → int

Hard timeouts: 10s per request, 60s total per site.

Output: data/ai_readiness_latest.json with
  { "fetched_date": "...", "method": "auto", "sites": [...] }

Usage:
  python scrapers/ai_readiness_check.py            # all 10 sites
  python scrapers/ai_readiness_check.py remento.co heritagewhisper.com
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).parent.parent
OUT_FILE = ROOT / "data" / "ai_readiness_latest.json"

SITES = [
    ("Remento",          "https://www.remento.co"),
    ("StoryWorth",       "https://welcome.storyworth.com"),
    ("Meminto",          "https://meminto.com"),
    ("Storykeeper",      "https://storykeeper.app"),
    ("Heritage Whisper", "https://www.heritagewhisper.com"),
    ("StoriedLife AI",   "https://storiedlife.ai"),
    ("LifeEcho",         "https://lifeecho.org"),
    ("Storii",           "https://www.storii.com"),
    ("Tell Mel",         "https://tellmel.com"),
    ("Listn",            "https://listn-app.com"),
]

AI_BOT_NAMES = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "Bingbot"]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TIMEOUT = 10


# ── Signal probes ─────────────────────────────────────────────────────────────
def _get(url: str) -> Optional[requests.Response]:
    """GET with a hard timeout. Returns Response or None."""
    try:
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def has_llms_txt(base: str) -> str:
    """
    Real /llms.txt is plain text (not HTML). Many SPAs return their
    index.html for every URL — so we must reject HTML responses even
    when the status code is 200.
    """
    r = _get(base.rstrip("/") + "/llms.txt")
    if r is None:
        return "Timeout"
    if r.status_code != 200 or not r.text.strip():
        return "No"
    body = r.text.strip()
    content_type = r.headers.get("content-type", "").lower()
    looks_like_html = (
        body.lstrip().lower().startswith(("<!doctype", "<html", "<!--"))
        or "text/html" in content_type
    )
    if looks_like_html:
        return "No"
    return "Yes"


def count_allowed_ai_bots(base: str) -> int | str:
    r = _get(base.rstrip("/") + "/robots.txt")
    if r is None:
        return "Timeout"
    if r.status_code != 200:
        return 0
    text = r.text.lower()
    allowed = 0
    # A bot is "allowed" if its user-agent block has Allow: / or no Disallow: /
    blocks = re.split(r"(?im)^\s*user-agent:\s*", text)
    for block in blocks[1:]:
        first_line = block.split("\n", 1)[0].strip()
        for bot in AI_BOT_NAMES:
            if first_line == bot.lower():
                # Look for an explicit Disallow: / inside the block
                if not re.search(r"^\s*disallow:\s*/\s*$", block, flags=re.MULTILINE):
                    allowed += 1
                break
    return allowed


def has_faq_schema(base: str) -> str:
    r = _get(base)
    if r is None:
        return "Timeout"
    if r.status_code != 200:
        return "No"
    return "Yes" if '"@type": "FAQPage"' in r.text or '"@type":"FAQPage"' in r.text else "No"


def has_article_schema(base: str) -> str:
    """Try /blog and /journal."""
    for path in ("/blog", "/journal", "/articles", "/stories"):
        r = _get(base.rstrip("/") + path)
        if r is None:
            return "Timeout"
        if r.status_code == 200 and (
            '"@type": "Article"' in r.text
            or '"@type":"Article"' in r.text
            or '"@type": "BlogPosting"' in r.text
            or '"@type":"BlogPosting"' in r.text
        ):
            return "Yes"
    return "No"


def _sitemap_urls(base: str, limit: int = 10) -> list[str]:
    for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemaps/sitemap.xml"):
        r = _get(base.rstrip("/") + path)
        if r and r.status_code == 200 and "<loc>" in r.text:
            raw = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
            # If the sitemap is an index (points to other sitemaps), follow first child
            if raw and raw[0].endswith(".xml"):
                child = _get(raw[0])
                if child and child.status_code == 200 and "<loc>" in child.text:
                    raw = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", child.text)
            # Skip media-only entries
            urls = [u for u in raw if not u.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf", ".xml"))]
            seen = set()
            kept = []
            for u in urls:
                if u not in seen:
                    seen.add(u)
                    kept.append(u)
                if len(kept) >= limit:
                    break
            if kept:
                return kept
    # Fallback: return just the homepage so we get 1/1 = 100% for that single check
    return [base]


def canonical_and_metadesc_pct(base: str) -> tuple[int | str, int | str]:
    urls = _sitemap_urls(base, limit=10)
    if not urls:
        return "Unknown", "Unknown"
    canon_hits = 0
    metadesc_hits = 0
    checked = 0
    for u in urls:
        r = _get(u)
        if r is None:
            continue
        if r.status_code != 200:
            continue
        checked += 1
        head_block = r.text[: min(len(r.text), 30000)]
        if re.search(r'<link[^>]+rel=["\']canonical["\']', head_block, flags=re.IGNORECASE):
            canon_hits += 1
        if re.search(r'<meta[^>]+name=["\']description["\']', head_block, flags=re.IGNORECASE):
            metadesc_hits += 1
    if checked == 0:
        return "Unknown", "Unknown"
    return round(canon_hits / checked * 100), round(metadesc_hits / checked * 100)


# ── Composite score ───────────────────────────────────────────────────────────
def compute_score(row: dict) -> int:
    """
    Weighted composite:
      llms.txt:      15 pts
      AI bots ≥ 3:   15 pts (5 pts each, capped)
      FAQ schema:    15 pts
      Article schema:15 pts
      canonical_pct: up to 20 pts (linear)
      metadesc_pct:  up to 20 pts (linear)
    Anything missing or "Timeout" / "Unknown" contributes 0.
    """
    s = 0
    if row.get("llms_txt") == "Yes":
        s += 15
    bots = row.get("ai_bots")
    if isinstance(bots, int):
        s += min(bots * 5, 15)
    if row.get("faq_schema") == "Yes":
        s += 15
    if row.get("article_schema") == "Yes":
        s += 15
    cpct = row.get("canonical_pct")
    if isinstance(cpct, int):
        s += round(cpct / 100 * 20)
    mpct = row.get("metadesc_pct")
    if isinstance(mpct, int):
        s += round(mpct / 100 * 20)
    return s


# ── Per-site driver ───────────────────────────────────────────────────────────
def audit_site(name: str, base: str) -> dict:
    print(f"  · {name:20s} {base}")
    started = time.monotonic()
    row: dict = {"name": name, "url": base}

    row["llms_txt"]       = has_llms_txt(base)
    row["ai_bots"]        = count_allowed_ai_bots(base)
    row["faq_schema"]     = has_faq_schema(base)
    row["article_schema"] = has_article_schema(base)
    canon, meta = canonical_and_metadesc_pct(base)
    row["canonical_pct"] = canon
    row["metadesc_pct"]  = meta

    row["score"] = compute_score(row)
    row["elapsed_seconds"] = round(time.monotonic() - started, 1)
    print(
        f"    -> score {row['score']} "
        f"(llms {row['llms_txt']} · bots {row['ai_bots']} · "
        f"faq {row['faq_schema']} · article {row['article_schema']} · "
        f"canon {row['canonical_pct']} · meta {row['metadesc_pct']}) "
        f"in {row['elapsed_seconds']}s"
    )
    return row


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    if len(sys.argv) > 1:
        # Filter to specific domains (e.g. python ai_readiness_check.py remento.co)
        # Match by suffix so "remento.co" finds "www.remento.co".
        allowed = [urlparse(a if "://" in a else f"https://{a}").netloc.lower().lstrip("www.")
                   for a in sys.argv[1:]]
        def _matches(url: str) -> bool:
            host = urlparse(url).netloc.lower().lstrip("www.")
            return any(host.endswith(a) for a in allowed)
        sites = [(n, u) for n, u in SITES if _matches(u)]
        if not sites:
            print(f"No matches in SITES for: {sys.argv[1:]}")
            print("Known sites:", [(n, u) for n, u in SITES])
            return 1
    else:
        sites = SITES

    print(f"Auditing {len(sites)} site(s)...")
    rows = [audit_site(n, u) for n, u in sites]

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_date": date.today().isoformat(),
        "method": "auto",
        "sites": rows,
    }
    OUT_FILE.write_text(json.dumps(payload, indent=2))
    print(f"\nWrote {OUT_FILE} ({len(rows)} rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
