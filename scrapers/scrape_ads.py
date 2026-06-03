"""
Meta Ad Library web scraper — no API token required.
Uses Playwright (headless Chromium) + text parsing of the rendered page.
Searches by advertiser/page name so results are the competitor's own ads.
"""

import argparse
import json
import os
import re
import time
from datetime import date, datetime
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

COMPETITORS = [
    "Remento",
    "Enna",
    "Meminto",
    "StoryWorth",
    "Storykeeper",
    "Tellmel",
    "Keepsake",
    "HereAfter AI",
    "No Story Lost",
    "Heritage Whisper",
    # Adjacent / lateral competitors — companion & care space.
    "ElliQ",
    "Papa",
    "friend.com",
]

# Words that MUST appear in the page_name for an ad to be counted as that competitor's.
# Keeps broad searches (e.g. "Tellmel", "Keepsake") from pulling in unrelated pages.
COMPETITOR_PAGE_FILTER = {
    "Remento":       ["remento"],
    "Enna":          ["enna.care"],
    "Meminto":       ["meminto"],
    "StoryWorth":    ["storyworth", "story worth"],
    "Storykeeper":   ["storykeeper", "story keeper"],
    "Tellmel":      ["tell me", "tellme", "tellmel"],
    "Keepsake":      ["keepsake"],
    "HereAfter AI":  ["hereafter"],
    "No Story Lost": ["no story lost", "nostorylost"],
    "Heritage Whisper": ["heritage whisper", "heritagewhisper"],
    "ElliQ":         ["elliq", "intuition robotics"],
    # "Papa" and "friend" are common English words — keep filters strict so we
    # don't tag random pages (Papa Johns, friendship orgs, etc.).
    "Papa":          ["joinpapa", "papa, inc", "papa health", "papa.com"],
    "friend.com":    ["friend.com", "friend ai", "friend pendant"],
}

# Meta page IDs — bypass search ranking entirely by hitting view_all_page_id=<id>.
# Search results are inconsistent (geo-filtered, A/B tested, bot-detected, etc.)
# so we use the deterministic page-profile URL when an ID is known and only
# fall back to keyword search when it isn't. Refresh via:
#   python3 scripts/discover_page_ids.py
COMPETITOR_PAGE_IDS = {
    "Remento":          "105472718827818",
    "Enna":             "109074514802310",
    "Meminto":          "233623109834430",
    "StoryWorth":       "679258085265552",
    "Storykeeper":      "136291949559393",
    "Tellmel":          "676999072159591",
    "Keepsake":         "650888101449457",
    "HereAfter AI":     "108361132071329",
    "No Story Lost":    "627300267900557",
    # Heritage Whisper page_id discovery returned 122298767852952 but that's a
    # jewelry brand — the real HW page has few ads so noise outranks it in
    # Meta search results. Leave it on search-fallback until we get the real
    # page_id by visiting the HW profile in a logged-in browser.
    "Heritage Whisper": None,
    # Adjacent competitors:
    # ElliQ confirmed via Meta Ad Library; the other three don't run Meta ads
    # at the time of integration. Leave their IDs as None so the scraper skips
    # the deterministic page-profile URL and falls back to keyword search; if
    # the keyword search returns nothing (likely), they'll simply show 0 ads.
    "ElliQ":            "434160116949836",
    "Papa":             None,
    "friend.com":       None,
}

# Each entry is a list of (search_term, search_type) pairs tried in order.
# Used as fallback when COMPETITOR_PAGE_IDS doesn't have an ID for the competitor.
COMPETITOR_SEARCH_PLAN = {
    "Remento":       [("Remento",        "page")],
    "Enna":          [("Enna.care",      "page")],
    "Meminto":       [("Meminto",        "page")],
    "StoryWorth":    [("StoryWorth",     "page"),
                      ("StoryWorth",     "keyword_unordered")],
    "Storykeeper":   [("Storykeeper",    "page")],
    "Tellmel":       [("Tellmel",        "page"),
                      ("Tell me",        "page"),
                      ("TellMe Stories", "page"),
                      ("Tell Me",        "keyword_unordered")],
    "Keepsake":      [("Keepsake",       "page")],
    "HereAfter AI":  [("HereAfter AI",   "page"),
                      ("HereAfter",      "page"),
                      ("HereAfter AI",   "keyword_unordered")],
    "No Story Lost": [("No Story Lost",  "page"),
                      ("NoStoryLost",    "page"),
                      ("No Story Lost",  "keyword_unordered")],
    "Heritage Whisper": [("Heritage Whisper", "page"),
                         ("HeritageWhisper",  "page"),
                         ("Heritage Whisper", "keyword_unordered")],
    # Adjacent competitors — broad keyword fallbacks. ElliQ goes through
    # COMPETITOR_PAGE_IDS so this entry is rarely hit. Papa / friend.com
    # are common-word brand names; the page_filter above is the real safety
    # net — search results are best-effort only.
    "ElliQ":         [("ElliQ",            "page"),
                      ("Intuition Robotics","page")],
    "Papa":          [("Papa Inc",         "page"),
                      ("Join Papa",        "page")],
    "friend.com":    [("friend.com",       "page"),
                      ("Friend AI",        "keyword_unordered")],
}

AD_LIBRARY_BASE = "https://www.facebook.com/ads/library/"


def load_competitors_from_supabase():
    """
    Load active competitors from Supabase.

    Returns:
        (names, terms) — names is a list[str] of active competitor names;
        terms is a dict mapping name -> list[str] of Meta search terms.
        Returns (None, None) on any failure so callers can fall back to the
        hardcoded COMPETITORS list and COMPETITOR_SEARCH_PLAN.
    """
    try:
        import os as _os
        import sys
        _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from lib.supabase_client import get_client
        client = get_client()
        if client is None:
            return None, None
        resp = (
            client.table("competitors")
            .select("name,meta_search_terms")
            .eq("active", True)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None, None
        names = [r["name"] for r in rows]
        terms = {r["name"]: list(r.get("meta_search_terms") or []) for r in rows}
        return names, terms
    except Exception as e:
        print(f"[supabase] load_competitors_from_supabase failed: {e}")
        return None, None

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
        f"?active_status=active&ad_type=all&country=ALL"
        f"&is_targeted_country=false"
        f"&q={q}&search_type={search_type}&media_type=all"
    )


def build_page_url(page_id):
    """Deterministic per-page URL — same view as clicking the brand's profile
    in the Ad Library. Avoids the search-ranking inconsistency that drops ads
    from anonymous/headless sessions."""
    return (
        f"{AD_LIBRARY_BASE}"
        f"?active_status=active&ad_type=all&country=ALL"
        f"&is_targeted_country=false&media_type=all"
        f"&view_all_page_id={page_id}&search_type=page"
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


def scroll_and_load(page, rounds=12):
    """Scroll to bottom repeatedly to trigger Meta's lazy-load.

    We stop early once the page stops growing (Library ID count plateaus),
    so the upper bound only matters for pages with hundreds of ads.
    """
    last_count = 0
    stable_rounds = 0
    for _ in range(rounds):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2500)
        # Count Library ID occurrences as a proxy for ads loaded so far.
        try:
            count = page.evaluate(
                "(document.body.innerText.match(/Library ID|Bibliotheks-ID/g) || []).length"
            )
        except Exception:
            count = last_count
        if count == last_count:
            stable_rounds += 1
            if stable_rounds >= 2:
                break
        else:
            stable_rounds = 0
        last_count = count


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


_STATUS_LABELS = {"Active": "Active", "Aktiv": "Active", "Inactive": "Inactive", "Inaktiv": "Inactive"}


def build_status_map(body_text):
    """Pair each Library ID in the page text with the nearest preceding
    "Active"/"Inactive" (or German "Aktiv"/"Inaktiv") line. Meta renders the
    status badge on its own line above each ad card, so the closest preceding
    badge is the authoritative status for that ad.
    """
    status_positions = [
        (m.start(), _STATUS_LABELS[m.group(1)])
        for m in re.finditer(r"(?m)^(Active|Inactive|Aktiv|Inaktiv)\s*$", body_text)
    ]
    id_matches = re.finditer(r"(?:Library ID|Bibliotheks-ID):\s*(\d+)", body_text)
    result = {}
    for m in id_matches:
        ad_id = m.group(1)
        id_pos = m.start()
        # Nearest status line BEFORE this Library ID
        nearest = None
        for pos, label in status_positions:
            if pos < id_pos:
                nearest = label
            else:
                break
        if nearest:
            result[ad_id] = nearest
    return result


_EXTRACT_CREATIVES_JS = r"""
() => {
  // Walks the rendered Ad Library page and returns one record per ad card,
  // keyed by Library ID. Format detection is heuristic — Meta obfuscates
  // class names so we lean on structural hints (card width, media size)
  // instead of named selectors.
  //
  // Heuristics:
  //   * Card container = nearest ancestor with width >= 400px AND height
  //     >= 300px. Width alone isn't enough: the inline "Library ID: …"
  //     row often spans the full card width but has tiny height. Cards
  //     are tall because they pack media + copy + actions.
  //   * Logo/avatar filter: drop <img> with natural dimensions < 200px.
  //     Profile pics on Meta are 40-60px; ad creatives are >= 240px.
  //   * Video presence dominates classification (Meta videos always include
  //     a poster image, but a poster alone without <video> = static image).
  const MIN_MEDIA_PX = 200;
  const MAX_PARENT_WALK = 10;
  const MIN_CARD_WIDTH = 400;
  const MIN_CARD_HEIGHT = 300;

  function findCard(el) {
    let cur = el;
    let hops = 0;
    while (cur && cur !== document.body && hops < MAX_PARENT_WALK) {
      const rect = cur.getBoundingClientRect();
      if (rect.width >= MIN_CARD_WIDTH && rect.height >= MIN_CARD_HEIGHT) {
        return cur;
      }
      cur = cur.parentElement;
      hops += 1;
    }
    return null;
  }

  function isLargeImg(img) {
    const w = img.naturalWidth || img.width || 0;
    const h = img.naturalHeight || img.height || 0;
    return w >= MIN_MEDIA_PX && h >= MIN_MEDIA_PX;
  }

  function videoSrc(video) {
    if (video.src) return video.src;
    const source = video.querySelector('source[src]');
    return source ? source.src : null;
  }

  const out = {};
  // Locate every "Library ID:" / "Bibliotheks-ID:" text node, then walk up
  // to its enclosing card. document.evaluate is the only reliable way to
  // text-match across arbitrary inline spans Meta inserts mid-string.
  const xpath = "//*[contains(text(), 'Library ID:') or contains(text(), 'Bibliotheks-ID:')]";
  const snapshot = document.evaluate(
    xpath, document.body, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null
  );

  for (let i = 0; i < snapshot.snapshotLength; i++) {
    const node = snapshot.snapshotItem(i);
    const text = (node.textContent || "").trim();
    const m = text.match(/(?:Library ID|Bibliotheks-ID):\s*(\d+)/);
    if (!m) continue;
    const adId = m[1];
    if (out[adId]) continue; // first hit wins; duplicates happen in carousels

    const card = findCard(node);
    if (!card) continue;

    const videos = Array.from(card.querySelectorAll('video'));
    const allImgs = Array.from(card.querySelectorAll('img[src]'));
    const largeImgs = allImgs.filter(isLargeImg);

    let format = "text";
    const creativeUrls = [];
    let thumbnailUrl = null;

    if (videos.length > 0) {
      format = "video";
      for (const v of videos) {
        const src = videoSrc(v);
        if (src) creativeUrls.push(src);
        if (!thumbnailUrl && v.poster) thumbnailUrl = v.poster;
      }
      if (!thumbnailUrl && largeImgs.length > 0) thumbnailUrl = largeImgs[0].src;
    } else if (largeImgs.length > 1) {
      format = "carousel";
      for (const img of largeImgs) creativeUrls.push(img.src);
      thumbnailUrl = creativeUrls[0] || null;
    } else if (largeImgs.length === 1) {
      format = "image";
      creativeUrls.push(largeImgs[0].src);
      thumbnailUrl = largeImgs[0].src;
    }

    out[adId] = {
      format: format,
      creative_urls: creativeUrls,
      thumbnail_url: thumbnailUrl,
    };
  }

  return out;
}
"""


def extract_creatives_from_dom(page):
    """Walk the DOM for each loaded ad card and pull format + media URLs.

    Returns a dict ``{ad_id: {"format": str, "creative_urls": list[str],
    "thumbnail_url": str | None}}``. Empty dict on any failure — callers
    should fall back to ``None`` defaults so a flaky page doesn't drop
    ads from the output.
    """
    try:
        return page.evaluate(_EXTRACT_CREATIVES_JS) or {}
    except Exception as e:
        print(f"  [creative-extract] page.evaluate failed: {e}")
        return {}

_EXTRACT_SINGLE_AD_JS = r"""
() => {
  const MIN_MEDIA_PX = 200;
  const isHttp = (u) => typeof u === "string" && /^https?:/.test(u);
  const isProfile = (u) => /t51\.2885-19/.test(u);      // FB profile-pic token
  const isCreativeTok = (u) => /t39\.\d+-\d+/.test(u);  // FB ad-creative token
  const isLargeImg = (img) =>
    (img.naturalWidth || img.width || 0) >= MIN_MEDIA_PX &&
    (img.naturalHeight || img.height || 0) >= MIN_MEDIA_PX;
  // Headless CI often has not-yet-decoded imgs (naturalWidth=0). Accept by
  // creative-token URL too, so carousel cards are not lost to size checks.
  const qualifies = (img) =>
    isHttp(img.src) && !isProfile(img.src) &&
    (isLargeImg(img) || isCreativeTok(img.src));

  // Permalink renders exactly one ad. Scope to the card holding the single
  // "Library ID:" so we skip page chrome and any "suggested" ads.
  const xpath = "//*[contains(text(),'Library ID:') or contains(text(),'Bibliotheks-ID:')]";
  const node = document.evaluate(
    xpath, document.body, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null
  ).singleNodeValue;
  let root = document.body;
  if (node) {
    let cur = node, hops = 0;
    while (cur && cur !== document.body && hops < 14) {
      const r = cur.getBoundingClientRect();
      if (r.width >= 320 && r.height >= 300) { root = cur; break; }
      cur = cur.parentElement; hops++;
    }
  }

  const collect = (scope) => ({
    vids: Array.from(scope.querySelectorAll('video')),
    imgs: Array.from(scope.querySelectorAll('img[src]')).filter(qualifies),
  });

  let { vids, imgs } = collect(root);
  // Fallback: scoped root yielded nothing (lazy/virtualized carousel) -> scan
  // whole doc, still token/size filtered + profile-pic excluded. Permalink
  // shows a single ad, so doc-wide creative-token imgs belong to that ad.
  if (vids.length === 0 && imgs.length === 0) {
    ({ vids, imgs } = collect(document));
  }

  // Dedupe img srcs, preserve order.
  const seen = new Set();
  const uniqImgs = [];
  for (const img of imgs) {
    if (seen.has(img.src)) continue;
    seen.add(img.src); uniqImgs.push(img.src);
  }

  let format = "text";
  const creativeUrls = [];
  let thumbnailUrl = null;
  let videoUrl = null;

  if (vids.length > 0) {
    format = "video";
    for (const v of vids) {
      if (isHttp(v.src) && !videoUrl) videoUrl = v.src;
      if (isHttp(v.poster) && !isProfile(v.poster) && !thumbnailUrl) thumbnailUrl = v.poster;
    }
    if (!thumbnailUrl && uniqImgs.length) thumbnailUrl = uniqImgs[0];
    if (thumbnailUrl) creativeUrls.push(thumbnailUrl);
    for (const u of uniqImgs) if (!creativeUrls.includes(u)) creativeUrls.push(u);
  } else if (uniqImgs.length > 1) {
    format = "carousel";
    for (const u of uniqImgs) creativeUrls.push(u);
    thumbnailUrl = creativeUrls[0] || null;
  } else if (uniqImgs.length === 1) {
    format = "image";
    creativeUrls.push(uniqImgs[0]);
    thumbnailUrl = uniqImgs[0];
  }

  return { format, creative_urls: creativeUrls, thumbnail_url: thumbnailUrl, video_url: videoUrl };
}
"""


PER_AD_NAV_DELAY_MS = 1200   # politeness between permalink loads (avoid throttling)


def creative_for_single_ad(enrich_page, ad_id):
    """Load one ad's permalink (renders exactly that ad) and pull its creative.

    Returns a dict ``{format, creative_urls, thumbnail_url, video_url}`` or
    ``None``. Never raises so a flaky permalink can't abort the scrape.
    """
    url = f"https://www.facebook.com/ads/library/?id={ad_id}"
    try:
        enrich_page.goto(url, wait_until="domcontentloaded", timeout=30000)
        enrich_page.wait_for_timeout(3500)
        dismiss_overlays(enrich_page)
        enrich_page.wait_for_timeout(800)
        # Nudge lazy-loaded carousel/video media into the DOM (CI headless is
        # slower to populate off-screen cards than a local browser).
        try:
            enrich_page.mouse.wheel(0, 1400)
            enrich_page.wait_for_timeout(800)
            enrich_page.mouse.wheel(0, -700)
            enrich_page.wait_for_timeout(500)
        except Exception:
            pass
        data = enrich_page.evaluate(_EXTRACT_SINGLE_AD_JS)
        if data and (data.get("creative_urls") or data.get("thumbnail_url")):
            return data
        print(f"  [per-ad {ad_id}] no media (fmt={data.get('format') if data else '?'})")
    except Exception as e:
        print(f"  [per-ad {ad_id}] failed: {e}")
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
        # Populated by extract_creatives_from_dom() in scrape_competitor().
        # Kept here so the JSON shape is consistent even when DOM extraction
        # misses a card (e.g. heuristics fail on a layout variant).
        "format": None,
        "creative_urls": [],
        "thumbnail_url": None,
        "data_source": None,
    }

    # Note: status is NOT parsed here. Meta renders the "Active"/"Inactive"
    # badge above the Library ID, so after splitting at "Library ID:" the badge
    # for ad N lives at the END of block N-1. The authoritative status is
    # computed in scrape_competitor() via build_status_map() against the full
    # body_text and injected after parsing.

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


def scrape_competitor(page, competitor, debug_dir=None):
    """Work through the search plan for this competitor; return the first batch that yields matches.

    If ``debug_dir`` is set, dump the raw body_text, the status_by_id map, and a
    breakdown of parsed-vs-filtered counts for every search attempt — so we can
    see *why* a competitor returned 0 (no results vs filtered out vs status mis-detected).
    """
    safe_name = re.sub(r"[^a-z0-9]+", "_", competitor.lower()).strip("_")

    # Page-ID URL first (deterministic), then keyword-search fallbacks.
    attempts = []
    page_id = COMPETITOR_PAGE_IDS.get(competitor)
    if page_id:
        attempts.append((build_page_url(page_id), f"page_id={page_id}", "page_id"))
    for search_term, search_type in COMPETITOR_SEARCH_PLAN.get(competitor, [(competitor, "page")]):
        attempts.append((build_url(search_term, search_type), search_term, search_type))

    for attempt_idx, (url, search_term, search_type) in enumerate(attempts, start=1):
        print(f"  [{search_type}] q={search_term!r}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PWTimeout:
            print(f"  TIMEOUT — skipping")
            if debug_dir:
                _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_TIMEOUT.txt",
                             f"url={url}\nresult=timeout\n")
            continue

        page.wait_for_timeout(3000)
        dismiss_overlays(page)
        page.wait_for_timeout(1000)

        body_text = page.inner_text("body")

        if "No results found" in body_text or "Keine Ergebnisse" in body_text:
            print(f"  No results — trying next")
            if debug_dir:
                _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_NO_RESULTS.txt",
                             f"url={url}\nresult=no_results_banner\n\n{body_text}")
            continue

        if not re.search(r"(?:Library ID|Bibliotheks-ID):", body_text):
            print(f"  No ad cards — trying next")
            if debug_dir:
                _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_NO_CARDS.txt",
                             f"url={url}\nresult=no_library_ids_in_body\n\n{body_text}")
            continue

        scroll_and_load(page, rounds=5)
        body_text = page.inner_text("body")

        raw_blocks = re.split(r"(?=(?:Library ID|Bibliotheks-ID):)", body_text)
        raw_blocks = [b for b in raw_blocks if re.search(r"(?:Library ID|Bibliotheks-ID):", b)]

        # The "Active"/"Inactive" badge Meta renders above each card ends up in
        # the PREVIOUS block after the split. Build a side map of {ad_id: status}
        # by pairing each Library ID in body_text with the nearest preceding
        # status line, then inject it into each parsed ad below.
        status_by_id = build_status_map(body_text)

        ads = [parse_ad_block(block, competitor) for block in raw_blocks]
        for a in ads:
            if a.get("ad_id") and a["ad_id"] in status_by_id:
                a["status"] = status_by_id[a["ad_id"]]
                if a["status"] == "Active":
                    a["stop_date"] = None
                    if a.get("start_date"):
                        a["days_running"] = days_between(a["start_date"], None)

        # DOM-side enrichment: format + creative URLs come from img/video tags
        # inside each ad card, not the rendered text. Run once per page; any
        # ad whose card isn't found stays at default (format=None, dashboard
        # renders a dash).
        creatives_by_id = extract_creatives_from_dom(page)
        for a in ads:
            ad_id = a.get("ad_id")
            if not ad_id:
                continue
            a["data_source"] = "playwright"
            extra = creatives_by_id.get(ad_id)
            if extra:
                a["format"] = extra.get("format")
                a["creative_urls"] = extra.get("creative_urls") or []
                a["thumbnail_url"] = extra.get("thumbnail_url")

        parsed_count = len(ads)
        parsed_page_names = sorted({(a.get("page_name") or "").strip() for a in ads if a.get("page_name")})
        if search_type == "page_id":
            # Sanity check: the page_id URL is supposed to be the brand's own
            # profile, so SOME parsed ads should still show the brand name in
            # the page_name slot. If none match the filter, the page_id is
            # almost certainly wrong (picked up unrelated noise during
            # discovery) — drop the batch and fall through to search.
            matched = [a for a in ads if is_competitor_ad(a, competitor)]
            if not matched and ads:
                print(f"  page_id returned {len(ads)} ads but 0 matched "
                      f"page_name filter — likely wrong page_id, trying next")
                if debug_dir:
                    _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_BAD_PAGE_ID.txt",
                                 f"page_id={search_term} produced ads with page_names "
                                 f"that don't include any of "
                                 f"{COMPETITOR_PAGE_FILTER.get(competitor)}.\n"
                                 f"Sample page_names: {parsed_page_names[:10]}\n")
                continue
            # Trust the profile view — accept all ads, backfill page_name where missing.
            kept = ads
            for a in kept:
                if not a.get("page_name"):
                    a["page_name"] = competitor
        else:
            kept = [a for a in ads if is_competitor_ad(a, competitor)]
        active_kept = sum(1 for a in kept if a.get("status") == "Active")

        creative_hits = sum(1 for a in ads if a.get("format"))

        if debug_dir:
            _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_BODY.txt",
                         f"url={url}\nsearch_term={search_term!r} search_type={search_type}\n"
                         f"raw_blocks={len(raw_blocks)} parsed={parsed_count} "
                         f"status_map_size={len(status_by_id)} "
                         f"creative_hits={creative_hits} "
                         f"filtered_in={len(kept)} active_kept={active_kept}\n"
                         f"page_names_seen={parsed_page_names}\n"
                         f"filter_keywords={COMPETITOR_PAGE_FILTER.get(competitor)}\n"
                         f"\n===== BODY TEXT =====\n{body_text}")
            _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_STATUS_MAP.json",
                         json.dumps(status_by_id, indent=2))
            _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_CREATIVES.json",
                         json.dumps(creatives_by_id, indent=2))
            _debug_write(debug_dir, f"{safe_name}_{attempt_idx}_PARSED.json",
                         json.dumps(ads, indent=2, default=str))

        print(f"  raw_blocks={len(raw_blocks)} parsed={parsed_count} "
              f"status_badges={len(status_by_id)} creatives={creative_hits} "
              f"kept={len(kept)} active={active_kept}")
        # Per-ad creative enrichment: each ad's own permalink renders exactly
        # that ad, so its creative binds unambiguously (no shared-container
        # bleed from the results grid). Overrides the results-page guess above.
        if kept:
            enrich_page = page.context.new_page()
            try:
                for a in kept:
                    ad_id = a.get("ad_id")
                    if not ad_id:
                        continue
                    a["data_source"] = "playwright"
                    extra = creative_for_single_ad(enrich_page, ad_id)
                    if extra:
                        a["format"] = extra.get("format")
                        a["creative_urls"] = extra.get("creative_urls") or []
                        a["thumbnail_url"] = extra.get("thumbnail_url")
                        if extra.get("video_url"):
                            a["video_url"] = extra["video_url"]
                    enrich_page.wait_for_timeout(PER_AD_NAV_DELAY_MS)
            finally:
                enrich_page.close()


        if kept:
            return kept
        print(f"  0 matching ads after filter — trying next")

    print(f"  No matching ads found for {competitor} across all search strategies")
    return []


def _debug_write(debug_dir, filename, content):
    os.makedirs(debug_dir, exist_ok=True)
    with open(os.path.join(debug_dir, filename), "w", encoding="utf-8") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description="Meta Ad Library scraper")
    parser.add_argument("--debug", action="store_true",
                        help="Dump body_text, status maps, and parsed ads per competitor "
                             "to debug/<date>/ for inspection.")
    parser.add_argument("--only", nargs="+", metavar="COMPETITOR",
                        help="Only scrape these competitors (case-insensitive, "
                             "matched against the tracked list).")
    parser.add_argument("--headed", action="store_true",
                        help="Run Chromium with a visible window (helps when Meta "
                             "renders differently in headed vs headless).")
    args = parser.parse_args()

    today = date.today().isoformat()
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    dated_file = os.path.join(data_dir, f"ads_scraped_{today}.json")
    latest_file = os.path.join(data_dir, "ads_scraped_latest.json")
    debug_dir = os.path.join("debug", today) if args.debug else None
    if debug_dir:
        print(f"[debug] Writing per-competitor dumps to {debug_dir}/")

    # Load competitors from Supabase; fall back to hardcoded list if unavailable.
    sb_names, _sb_terms = load_competitors_from_supabase()
    if sb_names:
        active_competitors = sb_names
        print(f"[supabase] Loaded {len(active_competitors)} active competitors.")
    else:
        active_competitors = COMPETITORS
        print("[fallback] Using hardcoded competitor list.")

    if args.only:
        wanted = {n.lower() for n in args.only}
        active_competitors = [c for c in active_competitors if c.lower() in wanted]
        if not active_competitors:
            print(f"[error] --only {args.only} matched none of the tracked competitors")
            return
        print(f"[only] Scraping just: {active_competitors}")

    all_results = {}
    total_ads = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
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

        for competitor in active_competitors:
            print(f"\nFetching ads for: {competitor}")
            ads = scrape_competitor(page, competitor, debug_dir=debug_dir)
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

    payload = json.dumps(output, indent=2)
    with open(dated_file, "w") as f:
        f.write(payload)
    with open(latest_file, "w") as f:
        f.write(payload)

    # Summary
    print(f"\n{'='*55}")
    print(f"  Total ads collected: {total_ads}")
    print(f"  Saved to:            {dated_file}")
    print(f"  Saved to:            {latest_file}")
    print(f"{'='*55}")
    for comp, ads in all_results.items():
        print(f"  {comp:<20} {len(ads):>3} ads")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
