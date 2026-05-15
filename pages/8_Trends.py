"""
Trends — historical view of competitive ad activity over time.

Reads every dated snapshot we have (data/archive/ + data/ads_scraped_*.json
+ data/ads_scraped_latest.json) and builds three time series:
  1. Ad volume per competitor
  2. Tone share across all ads
  3. Total ads in market

The 2026-05-13 marker on each chart flags the day the scraper switched to
active_status=active + page_id URLs + adaptive scroll. Pre-/post-data isn't
apples-to-apples — Enna in particular was undercounted before that change.
"""

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib.theme import COLORS, PLOTLY_LAYOUT, comp_color, inject_global_css, inject_sidebar
from lib.data_freshness import show_freshness_banner
from lib.synthesis import TONE_KEYWORDS

inject_global_css()
inject_sidebar()
show_freshness_banner()

ROOT = Path(__file__).parent.parent
ARCHIVE_DIR = ROOT / "data" / "archive"
DATA_DIR = ROOT / "data"
LATEST_FILE = DATA_DIR / "ads_scraped_latest.json"
METHODOLOGY_CHANGE_DATE = "2026-05-13"

TONE_COLORS = {
    "nostalgia":     "#FFB4A2",
    "urgency":       COLORS["urgent"],
    "gifting":       COLORS["evergreen"],
    "fear of loss":  COLORS["soon"],
    "pride":         COLORS["accent"],
    "transactional": "#22D3EE",
}

DATE_RE = re.compile(r"ads_scraped_(\d{4}-\d{2}-\d{2})\.json$")


def _all_tones(text: str) -> list[str]:
    t = (text or "").lower()
    hits = [tone for tone, words in TONE_KEYWORDS.items() if any(w in t for w in words)]
    return hits or ["nostalgia"]


@st.cache_data(show_spinner=False)
def load_snapshots() -> pd.DataFrame:
    """Return a long-format dataframe: one row per ad per snapshot date."""
    snapshots: dict[str, dict] = {}

    candidates = list(ARCHIVE_DIR.glob("ads_scraped_*.json")) + list(DATA_DIR.glob("ads_scraped_*.json"))
    if LATEST_FILE.exists():
        candidates.append(LATEST_FILE)

    for path in candidates:
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        snapshot_date = data.get("fetched_date")
        if not snapshot_date:
            m = DATE_RE.search(path.name)
            if not m:
                continue
            snapshot_date = m.group(1)
        snapshots[snapshot_date] = data

    rows = []
    for snapshot_date, data in snapshots.items():
        for competitor, ads in (data.get("competitors") or {}).items():
            for ad in (ads or []):
                rows.append({
                    "date": snapshot_date,
                    "competitor": competitor,
                    "ad_copy": ad.get("ad_copy") or "",
                })
    if not rows:
        return pd.DataFrame(columns=["date", "competitor", "ad_copy"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date")


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _add_methodology_marker(fig: go.Figure) -> None:
    marker = pd.Timestamp(METHODOLOGY_CHANGE_DATE)
    fig.add_vline(
        x=marker,
        line=dict(color=_rgba(COLORS["muted"], 0.35), width=1, dash="dot"),
    )
    fig.add_annotation(
        x=marker,
        y=1.0,
        yref="paper",
        text="Scraper methodology change — pre/post not comparable",
        showarrow=False,
        font=dict(color=COLORS["muted"], size=10),
        xanchor="left",
        xshift=6,
        yshift=4,
    )


def _empty_state(message: str) -> None:
    st.markdown(
        f"<div style='padding:48px;text-align:center;color:{COLORS['muted']};"
        f"border:1px dashed {COLORS['border']};border-radius:12px;'>{message}</div>",
        unsafe_allow_html=True,
    )


st.title("Trends")
st.caption("Historical view of competitive ad activity. Most recent snapshot defines the window.")

df = load_snapshots()

if df.empty:
    _empty_state("No snapshot data found in data/ or data/archive/.")
    st.stop()

# Window anchored on the latest snapshot, not today — handles weekend gaps.
max_date = df["date"].max()
window_choice = st.radio(
    "Window",
    options=["Last 7 days", "Last 30 days", "All time"],
    horizontal=True,
    index=2,
)
if window_choice == "Last 7 days":
    cutoff = max_date - pd.Timedelta(days=6)
    df_view = df[df["date"] >= cutoff]
elif window_choice == "Last 30 days":
    cutoff = max_date - pd.Timedelta(days=29)
    df_view = df[df["date"] >= cutoff]
else:
    df_view = df

snapshot_dates = sorted(df_view["date"].unique())
st.caption(
    f"{len(snapshot_dates)} snapshot{'s' if len(snapshot_dates) != 1 else ''} • "
    f"{snapshot_dates[0].date()} → {snapshot_dates[-1].date()}"
)

st.markdown("### Ad volume per competitor")

vol = df_view.groupby(["date", "competitor"]).size().reset_index(name="ads")
fig_vol = go.Figure()
for competitor in sorted(vol["competitor"].unique()):
    series = vol[vol["competitor"] == competitor].sort_values("date")
    fig_vol.add_trace(go.Scatter(
        x=series["date"],
        y=series["ads"],
        mode="lines",
        name=competitor,
        line=dict(color=comp_color(competitor), width=1.5, shape="spline", smoothing=0.6),
        opacity=0.85,
        hovertemplate=f"<b>{competitor}</b><br>%{{x|%b %d}}: %{{y}} ads<extra></extra>",
    ))
fig_vol.update_layout(**PLOTLY_LAYOUT, height=380, hovermode="x unified")
_add_methodology_marker(fig_vol)
st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("### Tone share over time")

tone_rows = []
for _, row in df_view.iterrows():
    for tone in _all_tones(row["ad_copy"]):
        tone_rows.append({"date": row["date"], "tone": tone})
tone_df = pd.DataFrame(tone_rows)

if tone_df.empty:
    _empty_state("No tone data in the selected window.")
else:
    tone_counts = tone_df.groupby(["date", "tone"]).size().reset_index(name="count")
    daily_totals = tone_counts.groupby("date")["count"].transform("sum")
    tone_counts["share"] = tone_counts["count"] / daily_totals * 100

    fig_tone = go.Figure()
    for tone in TONE_KEYWORDS.keys():
        series = tone_counts[tone_counts["tone"] == tone].sort_values("date")
        if series.empty:
            continue
        tone_hex = TONE_COLORS.get(tone, COLORS["muted"])
        fig_tone.add_trace(go.Scatter(
            x=series["date"],
            y=series["share"],
            mode="lines",
            stackgroup="tone",
            name=tone,
            line=dict(width=0, color=tone_hex),
            fillcolor=_rgba(tone_hex, 0.45),
            hovertemplate=f"<b>{tone}</b><br>%{{x|%b %d}}: %{{y:.1f}}%<extra></extra>",
        ))
    fig_tone.update_layout(**PLOTLY_LAYOUT, height=320, hovermode="x unified")
    fig_tone.update_yaxes(ticksuffix="%", range=[0, 100])
    _add_methodology_marker(fig_tone)
    st.plotly_chart(fig_tone, use_container_width=True)

st.markdown("### Total ads in market")

totals = df_view.groupby("date").size().reset_index(name="total")
fig_total = go.Figure()
fig_total.add_trace(go.Scatter(
    x=totals["date"],
    y=totals["total"],
    mode="lines",
    line=dict(color=COLORS["accent"], width=1.5, shape="spline", smoothing=0.6),
    fill="tozeroy",
    fillcolor=_rgba(COLORS["accent"], 0.06),
    hovertemplate="<b>%{x|%b %d}</b><br>%{y} ads total<extra></extra>",
    showlegend=False,
))
fig_total.update_layout(**PLOTLY_LAYOUT, height=260, hovermode="x unified")
_add_methodology_marker(fig_total)
st.plotly_chart(fig_total, use_container_width=True)

st.markdown("---")
st.markdown("### SEO trends")
_empty_state(
    "Awaiting historical data — first dated SEO file will appear after the next scrape. "
    "The SEO scraper now writes data/seo_raw_YYYY-MM-DD.json alongside _latest, so this "
    "chart will populate on the next Monday weekly refresh."
)

st.markdown("### AI Readiness trends")
_empty_state(
    "Awaiting historical data — first dated AI Readiness file will appear after the next scrape. "
    "The audit now writes data/ai_readiness_YYYY-MM-DD.json alongside _latest."
)
