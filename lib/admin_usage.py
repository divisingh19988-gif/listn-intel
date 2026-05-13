"""
Per-competitor usage stats for the admin page.

Today the only data source we can trust is the local ads JSON
(`data/ads_scraped_latest.json`). When a real Supabase `meta_ads` table
or SEO ranking table lands, extend the helpers below.

All readers degrade gracefully: missing files / missing keys return zeros.
"""

from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ADS_FILE_LATEST = DATA_DIR / "ads_scraped_latest.json"


def _load_ads() -> dict[str, Any]:
    """Returns the ads JSON or an empty shell. Never raises."""
    if not ADS_FILE_LATEST.exists():
        return {"fetched_date": None, "competitors": {}}
    try:
        with ADS_FILE_LATEST.open() as f:
            return json.load(f)
    except Exception:
        return {"fetched_date": None, "competitors": {}}


def _parse_date(s: Any) -> date | None:
    if not s:
        return None
    if isinstance(s, date):
        return s
    try:
        return datetime.fromisoformat(str(s)[:10]).date()
    except Exception:
        return None


def competitor_usage_stats(today: date | None = None) -> dict[str, dict[str, Any]]:
    """
    Returns: { competitor_name: { 'total_ads', 'ads_7d', 'last_scrape', 'last_ad_start' } }

    Names are returned as they appear in the JSON (the scraper writes the same
    name the competitors table uses). Match in the admin page with a
    case-insensitive lookup.
    """
    data = _load_ads()
    today = today or date.today()
    cutoff = today - timedelta(days=7)
    fetched = _parse_date(data.get("fetched_date"))
    out: dict[str, dict[str, Any]] = {}

    competitors = data.get("competitors") or {}
    for name, ads in competitors.items():
        if not isinstance(ads, list):
            continue
        total = len(ads)
        ads_7d = 0
        latest_start: date | None = None
        for a in ads:
            if not isinstance(a, dict):
                continue
            ad_date = _parse_date(a.get("start_date"))
            if ad_date:
                if latest_start is None or ad_date > latest_start:
                    latest_start = ad_date
                if ad_date >= cutoff:
                    ads_7d += 1
        out[name] = {
            "total_ads": total,
            "ads_7d": ads_7d,
            "last_scrape": fetched.isoformat() if fetched else None,
            "last_ad_start": latest_start.isoformat() if latest_start else None,
        }
    return out


def lookup_usage(stats: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    """Case-insensitive lookup with a zeroed fallback."""
    if not name:
        return _zero()
    nm = name.strip().casefold()
    for k, v in stats.items():
        if k.strip().casefold() == nm:
            return v
    return _zero()


def _zero() -> dict[str, Any]:
    return {"total_ads": 0, "ads_7d": 0, "last_scrape": None, "last_ad_start": None}


def coverage_gaps(
    *,
    competitors: list[dict],
    clusters: list[dict],
    tones: list[dict],
    today: date | None = None,
) -> dict[str, list[str]]:
    """
    Returns a dict of gap-name -> list of row labels.
    Used to power the 'Coverage gaps' panel.
    """
    today = today or date.today()
    gaps: dict[str, list[str]] = {
        "competitors_missing_appstore": [],
        "competitors_missing_domain": [],
        "competitors_missing_terms": [],
        "clusters_empty_keywords": [],
        "clusters_past_deadline_active": [],
        "tones_thin_keywords": [],
    }

    for c in competitors:
        if not c.get("active"):
            continue
        label = c.get("name") or "?"
        if not (c.get("appstore_id") or "").strip() if isinstance(c.get("appstore_id"), str) else not c.get("appstore_id"):
            gaps["competitors_missing_appstore"].append(label)
        if not (c.get("seo_domain") or "").strip() if isinstance(c.get("seo_domain"), str) else not c.get("seo_domain"):
            gaps["competitors_missing_domain"].append(label)
        terms = c.get("meta_search_terms") or []
        if not isinstance(terms, list) or not terms:
            gaps["competitors_missing_terms"].append(label)

    for cl in clusters:
        if not cl.get("active"):
            continue
        label = cl.get("name") or "?"
        kws = cl.get("keywords") or []
        if not isinstance(kws, list) or not kws:
            gaps["clusters_empty_keywords"].append(label)
        dl = _parse_date(cl.get("deadline"))
        if dl and dl < today:
            gaps["clusters_past_deadline_active"].append(f"{label} ({dl.isoformat()})")

    for t in tones:
        label = t.get("tone") or "?"
        kw = t.get("keyword_list") or []
        if not isinstance(kw, list) or len(kw) < 3:
            gaps["tones_thin_keywords"].append(f"{label} ({len(kw) if isinstance(kw, list) else 0})")

    return gaps
