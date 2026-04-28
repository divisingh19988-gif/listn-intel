"""
Data freshness helpers — read mtime of canonical data files,
compute next scheduled refresh, and render a banner at the top of every page.

Refresh schedule: every Monday 12:00 UTC (matches GitHub Actions cron '0 12 * * 1').
Stale threshold: 8 days (one full cycle + 1 day grace).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
ADS_FILE = DATA_DIR / "ads_scraped_latest.json"
SEO_FILE = DATA_DIR / "seo_raw_latest.json"

STALE_AFTER_DAYS = 8


def _file_mtime_utc(path: Path) -> Optional[datetime]:
    """Return UTC datetime of file's last-modified, or None if missing."""
    if not path.exists():
        return None
    return datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)


def get_last_refreshed() -> Optional[datetime]:
    """
    Last refresh = the most recent mtime among the canonical data files.
    Returns None if no data files exist yet.
    """
    candidates = [m for m in (_file_mtime_utc(ADS_FILE), _file_mtime_utc(SEO_FILE)) if m]
    return max(candidates) if candidates else None


def get_next_refresh(now: Optional[datetime] = None) -> datetime:
    """
    Next Monday at 12:00 UTC. If today is Monday and clock is before noon,
    today is the answer. Otherwise the next Monday.
    """
    now = now or datetime.now(tz=timezone.utc)
    target = now.replace(hour=12, minute=0, second=0, microsecond=0)
    # weekday(): Mon=0 ... Sun=6
    days_ahead = (0 - now.weekday()) % 7
    if days_ahead == 0 and now >= target:
        days_ahead = 7
    return (target + timedelta(days=days_ahead)).replace(
        hour=12, minute=0, second=0, microsecond=0
    )


def is_stale(last_refreshed: Optional[datetime], now: Optional[datetime] = None) -> bool:
    """True if last refresh is older than STALE_AFTER_DAYS or missing."""
    if last_refreshed is None:
        return True
    now = now or datetime.now(tz=timezone.utc)
    return (now - last_refreshed) > timedelta(days=STALE_AFTER_DAYS)


def _format_dt(dt: datetime) -> str:
    """Format like 'Apr 27, 2026 12:00 UTC' (no leading zero on day)."""
    return dt.strftime("%b %-d, %Y %H:%M UTC") if os.name != "nt" else dt.strftime(
        "%b %#d, %Y %H:%M UTC"
    )


def _format_short(dt: datetime) -> str:
    """Format like 'Mon May 4, 12:00 UTC'."""
    return dt.strftime("%a %b %-d, %H:%M UTC") if os.name != "nt" else dt.strftime(
        "%a %b %#d, %H:%M UTC"
    )


def show_freshness_banner() -> None:
    """
    Render the full-width data freshness banner. Must be the FIRST visible
    element on every page (call right after inject_global_css).
    """
    last = get_last_refreshed()
    next_ = get_next_refresh()
    stale = is_stale(last)

    if stale and last is None:
        body = (
            '<strong>⚠️ No data yet</strong> &nbsp;·&nbsp; '
            'Run the scrapers in <code>scrapers/</code> or trigger the '
            '<code>Weekly Intelligence Refresh</code> workflow.'
        )
        css_class = "freshness-banner stale"
    elif stale:
        body = (
            '⚠️ <strong>Data stale</strong> &nbsp;·&nbsp; '
            f'Last refresh: <strong>{_format_dt(last)}</strong> &nbsp;·&nbsp; '
            'Last automated refresh failed — check GitHub Actions.'
        )
        css_class = "freshness-banner stale"
    else:
        body = (
            f'📡 Last refreshed: <strong>{_format_dt(last)}</strong> '
            '&nbsp;·&nbsp; '
            f'Next refresh: <strong>{_format_short(next_)}</strong>'
        )
        css_class = "freshness-banner"

    st.markdown(f'<div class="{css_class}">{body}</div>', unsafe_allow_html=True)
