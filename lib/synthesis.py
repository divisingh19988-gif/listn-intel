"""
This Week's Moves — synthesis logic for streamlit_app.py.

Reads the same JSON files the page modules read and returns:
  • get_creative_move(ads_data)  -> dict for Card 1 (Meta signal)
  • get_content_move(seo_data)   -> dict for Card 2 (SEO signal)
  • get_supporting_stats(...)    -> 3 small stat cards

All functions return plain dicts so the page can render them directly.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
ADS_FILE = DATA_DIR / "ads_scraped_latest.json"
SEO_FILE = DATA_DIR / "seo_raw_latest.json"
AI_FILE = DATA_DIR / "ai_readiness_latest.json"


# ── Tone tagging (kept consistent with Meta Intel page) ───────────────────────
TONE_KEYWORDS = {
    "nostalgia":     ["memory", "remember", "story", "voice", "preserve", "legacy"],
    "urgency":       ["now", "today", "don't wait", "before", "last chance", "limited"],
    "gifting":       ["gift", "give", "present", "birthday", "christmas", "mother"],
    "fear of loss":  ["gone", "lost", "too late", "forget", "never", "disappear"],
    "pride":         ["hero", "proud", "amazing", "incredible", "legacy"],
    "transactional": ["save", "discount", "off", "price", "only $", "free"],
}


def _all_tones(text: Optional[str]) -> list[str]:
    if not text:
        return []
    t = text.lower()
    return [tone for tone, words in TONE_KEYWORDS.items() if any(w in t for w in words)]


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s[:10]).date()
    except (ValueError, TypeError):
        return None


def _load_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


# ── Meta signal: creative move ────────────────────────────────────────────────
def get_creative_move(ads_data: Optional[dict] = None, today: Optional[date] = None) -> dict:
    """
    Pick the strongest creative signal.

    Priority:
      1. An ad started in the last 14 days that has the highest days_running
         AND uses an under-played tone (< 10% average).
      2. Otherwise the under-played tone alone (gap message).
      3. Fallback: the longest-running active ad.

    Returns dict: {do, because, source_ref, signal_type}
    """
    today = today or date.today()
    ads_data = ads_data or _load_json(ADS_FILE) or {}
    competitors = ads_data.get("competitors", {})

    # Flatten all ads
    all_ads: list[dict] = []
    for ads in competitors.values():
        all_ads.extend(ads)

    if not all_ads:
        return {
            "do": "Run the Meta scraper.",
            "because": "No ad data has been collected yet — there's nothing to analyze.",
            "source_ref": "Meta Intel",
            "signal_type": "no-data",
        }

    # Compute tone share across all competitor ads
    tone_counts: dict[str, int] = {}
    total_tagged = 0
    for ad in all_ads:
        for tone in _all_tones(ad.get("ad_copy")):
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
            total_tagged += 1

    underplayed_tones = [
        t for t in TONE_KEYWORDS
        if (tone_counts.get(t, 0) / total_tagged * 100 if total_tagged else 0) < 10
    ]

    # Recent ads (started <= 14 days ago) sorted by longevity
    recent = []
    for ad in all_ads:
        start = _parse_date(ad.get("start_date"))
        if not start:
            continue
        days_since_start = (today - start).days
        if 0 <= days_since_start <= 14:
            recent.append((ad, days_since_start, int(ad.get("days_running") or 0)))
    recent.sort(key=lambda x: x[2], reverse=True)

    # Case 1 — recent ad in an under-played tone (strongest signal)
    for ad, days_old, days_running in recent:
        ad_tones = _all_tones(ad.get("ad_copy"))
        gap = next((t for t in ad_tones if t in underplayed_tones), None)
        if gap:
            comp = ad.get("competitor", "A competitor")
            snippet = (ad.get("ad_copy") or "")[:120].strip()
            return {
                "do": (
                    f"Test a creative in the '{gap}' register this week — "
                    "before competitors catch on."
                ),
                "because": (
                    f"{comp} just launched an ad in this register {days_old} day(s) ago "
                    f"({days_running}d total run). Tone share for '{gap}' is under 10% "
                    "across the market — this is unowned territory."
                ),
                "source_ref": f'"{snippet}…"',
                "signal_type": "recent-and-underplayed",
            }

    # Case 2 — under-played tone alone
    if underplayed_tones:
        gap = underplayed_tones[0]
        share = round(tone_counts.get(gap, 0) / total_tagged * 100 if total_tagged else 0, 1)
        return {
            "do": f"Run a creative test in the '{gap}' register.",
            "because": (
                f"Only {share}% of competitor ad copy uses this tone — "
                "Listn can claim it without category resistance."
            ),
            "source_ref": "Emotional Tone Breakdown",
            "signal_type": "underplayed-tone",
        }

    # Case 3 — fallback: longest-running active ad
    active = [a for a in all_ads if not a.get("stop_date")]
    active.sort(key=lambda a: int(a.get("days_running") or 0), reverse=True)
    if active:
        ad = active[0]
        comp = ad.get("competitor", "Competitor")
        days = int(ad.get("days_running") or 0)
        snippet = (ad.get("ad_copy") or "")[:120].strip()
        return {
            "do": f"Audit {comp}'s longest-running ad — what makes it stick?",
            "because": (
                f"{comp} has run this creative for {days} days. "
                "Evergreen ads in this market reveal what the buyer actually wants."
            ),
            "source_ref": f'"{snippet}…"',
            "signal_type": "longest-running",
        }

    return {
        "do": "Review the Meta Intel page.",
        "because": "Data was loaded but no clear creative signal surfaced.",
        "source_ref": "Meta Intel",
        "signal_type": "neutral",
    }


# ── SEO signal: content move ──────────────────────────────────────────────────
# Hardcoded clusters mirror the SEO Intel page — this is the source of truth
# for "what cluster has the nearest deadline".
SEO_CLUSTERS = [
    {
        "name": "Mother's Day",
        "window": "URGENT",
        "deadline": date(2026, 5, 10),
        "keywords": [
            ("meaningful mothers day gift", 8100, 12),
            ("unique mothers day gift", 22200, 14),
            ("mothers day gift for mom who has everything", 12100, 11),
            ("gift for mom from daughter", 12100, 8),
            ("sentimental mothers day gift", 4400, 9),
            ("mothers day gift ideas for older moms", 2900, 7),
            ("preserve mothers voice", 880, 4),
            ("record moms stories mothers day", 720, 3),
        ],
    },
    {
        "name": "Father's Day",
        "window": "SOON",
        "deadline": date(2026, 6, 15),
        "keywords": [
            ("fathers day gift ideas", 74000, 0),
            ("meaningful fathers day gift", 9900, 8),
            ("unique fathers day gift", 18100, 11),
            ("gift for dad from daughter", 12100, 7),
            ("fathers day gift for dad who has everything", 8100, 9),
            ("preserve dads voice", 590, 3),
            ("record dads stories fathers day", 480, 2),
            ("questions to ask dad before its too late", 1900, 6),
        ],
    },
    {
        "name": "Grandparent + Record Stories",
        "window": "EVERGREEN",
        "deadline": None,
        "keywords": [
            ("grandparent gift ideas", 14800, 0),
            ("grandparents gift idea", 14800, 0),
            ("presents grandparents", 14800, 0),
            ("gift for grandma", 22200, 6),
            ("gift for grandpa", 18100, 7),
            ("meaningful gift for grandparents", 4400, 8),
            ("how to record parents life stories", 2900, 8),
            ("record grandparents stories before too late", 1600, 6),
            ("questions to record with grandparents", 1300, 5),
            ("recording memories before dementia", 1300, 6),
            ("voice journaling for seniors", 720, 4),
            ("preserve grandparents memories", 1300, 5),
        ],
    },
    {
        "name": "Competitor Alternatives",
        "window": "COMMERCIAL INTENT",
        "deadline": None,
        "keywords": [
            ("remento alternative", 1900, 8),
            ("remento vs storyworth", 1300, 12),
            ("storyworth alternative", 2400, 10),
            ("storyworth vs remento", 880, 11),
            ("meminto alternative", 320, 4),
            ("hereafter ai alternative", 590, 6),
            ("heritage whisper alternative", 210, 3),
            ("best app to record family stories", 2400, 14),
            ("remento review", 1600, 9),
            ("storyworth review", 4400, 13),
        ],
    },
]


def get_content_move(seo_data: Optional[dict] = None, today: Optional[date] = None) -> dict:
    """
    Pick the highest-volume keyword (KD <= 10) in the cluster nearest its deadline.
    Mother's Day → Father's Day → Evergreen → Commercial Intent (in that order).

    Returns dict: {do, because, source_ref, cluster, keyword, volume, kd, days_to_deadline}
    """
    today = today or date.today()

    # Pick the nearest *future* dated cluster, falling back to evergreen order
    dated = [
        c for c in SEO_CLUSTERS
        if c["deadline"] and c["deadline"] >= today
    ]
    dated.sort(key=lambda c: c["deadline"])
    chosen = dated[0] if dated else next(
        (c for c in SEO_CLUSTERS if c["window"] == "EVERGREEN"),
        SEO_CLUSTERS[0],
    )

    # Highest-volume keyword with KD <= 10 (relax to KD <= 14 if nothing fits)
    candidates = [k for k in chosen["keywords"] if k[2] <= 10]
    if not candidates:
        candidates = list(chosen["keywords"])
    candidates.sort(key=lambda k: k[1], reverse=True)
    keyword, volume, kd = candidates[0]

    days_to_deadline = (chosen["deadline"] - today).days if chosen["deadline"] else None

    if chosen["deadline"]:
        deadline_phrase = (
            f"{chosen['name']} is in {days_to_deadline} day(s)"
            if days_to_deadline > 0
            else f"{chosen['name']} is today"
        )
    else:
        deadline_phrase = f"{chosen['name']} is the evergreen lane"

    return {
        "do": f'Publish a post targeting "{keyword}" this week.',
        "because": (
            f"{deadline_phrase}. Volume {volume:,}/mo, KD {kd}. "
            "Highest combined opportunity in the cluster."
        ),
        "source_ref": chosen["name"],
        "cluster": chosen["name"],
        "window": chosen["window"],
        "keyword": keyword,
        "volume": volume,
        "kd": kd,
        "days_to_deadline": days_to_deadline,
    }


# ── 3 small supporting stats ──────────────────────────────────────────────────
def count_new_ads_this_week(ads_data: Optional[dict] = None, today: Optional[date] = None) -> int:
    """Count ads with start_date in the last 7 days."""
    today = today or date.today()
    ads_data = ads_data or _load_json(ADS_FILE) or {}
    competitors = ads_data.get("competitors", {})
    threshold = today - timedelta(days=7)
    count = 0
    for ads in competitors.values():
        for ad in ads:
            start = _parse_date(ad.get("start_date"))
            if start and start >= threshold:
                count += 1
    return count


def next_deadline(today: Optional[date] = None) -> dict:
    """
    Return the nearest cluster deadline.
    Dict: {label, days, cluster}.
    """
    today = today or date.today()
    upcoming = [c for c in SEO_CLUSTERS if c["deadline"] and c["deadline"] >= today]
    upcoming.sort(key=lambda c: c["deadline"])
    if not upcoming:
        return {"label": "No seasonal deadline", "days": None, "cluster": "Evergreen"}
    c = upcoming[0]
    days = (c["deadline"] - today).days
    return {
        "label": f"{c['name']} in {days} days",
        "days": days,
        "cluster": c["name"],
    }


def ai_readiness_leader() -> dict:
    """
    Return the leader of the AI readiness ranking.
    Tries data/ai_readiness_latest.json, falls back to baseline.
    """
    fallback = {"name": "Heritage Whisper", "score": 95}
    data = _load_json(AI_FILE)
    if not data:
        return fallback
    sites = data.get("sites") or data.get("results") or []
    if not sites:
        return fallback
    # Pick highest scoring site (skip Listn — we want to highlight the leader)
    scored = [
        (s.get("name") or s.get("site"), s.get("score"))
        for s in sites
        if isinstance(s.get("score"), (int, float))
        and (s.get("name") or s.get("site")) != "Listn"
    ]
    if not scored:
        return fallback
    name, score = max(scored, key=lambda x: x[1])
    return {"name": name, "score": int(score)}
