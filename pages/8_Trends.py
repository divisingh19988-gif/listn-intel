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


def detect_inflections(
    df_view: pd.DataFrame,
    z_threshold: float = 1.5,
    min_abs_delta: int = 10,
) -> list[dict]:
    """Flag days where a competitor's day-over-day volume change is a z-score
    outlier within their own history AND the absolute change clears a magnitude
    floor (prevents noise from tiny advertisers bouncing between 0 and 3 ads).

    Threshold is 1.5σ rather than the conventional 2σ because the dataset is
    small (5-6 deltas per competitor); 2σ rarely fires until we have weeks of
    history. Min |delta| ≥ 10 ads filters out statistical noise from
    competitors that only run a few ads at a time.
    """
    if df_view.empty:
        return []
    daily = df_view.groupby(["date", "competitor"]).size().unstack(fill_value=0).sort_index()
    anomalies = []
    for competitor in daily.columns:
        series = daily[competitor]
        if len(series) < 4:
            continue
        deltas = series.diff().dropna()
        if len(deltas) < 3 or deltas.std() == 0:
            continue
        mean = deltas.mean()
        std = deltas.std()
        for date, delta in deltas.items():
            if abs(delta) < min_abs_delta:
                continue
            z = (delta - mean) / std
            if abs(z) >= z_threshold:
                idx = series.index.get_loc(date)
                anomalies.append({
                    "date": date,
                    "competitor": competitor,
                    "delta": int(delta),
                    "z": float(z),
                    "prev": int(series.iloc[idx - 1]),
                    "curr": int(series.iloc[idx]),
                })
    return sorted(anomalies, key=lambda a: -abs(a["z"]))


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


def _clean_layout(height: int) -> dict:
    """Strip chart chrome — no vertical grid, faint horizontal grid, legend below."""
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"], family="Inter, system-ui, sans-serif", size=12),
        height=height,
        margin=dict(l=0, r=10, t=30, b=0),
        xaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            color=COLORS["muted"],
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            gridcolor=_rgba(COLORS["border"], 0.4),
            showline=False,
            zeroline=False,
            color=COLORS["muted"],
            tickfont=dict(size=11),
            nticks=5,
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.12,
            x=0,
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font=dict(color=COLORS["muted"], size=11),
        ),
        hoverlabel=dict(
            bgcolor=COLORS["surface"],
            bordercolor=COLORS["border"],
            font=dict(color=COLORS["text"], size=12),
        ),
        modebar=dict(remove=["all"]),
    )


def _add_methodology_marker(fig: go.Figure, with_label: bool = True) -> None:
    marker = pd.Timestamp(METHODOLOGY_CHANGE_DATE)
    fig.add_vline(
        x=marker,
        line=dict(color=_rgba(COLORS["muted"], 0.35), width=1, dash="dot"),
    )
    if with_label:
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

anomalies = detect_inflections(df_view)
if anomalies:
    methodology_date = pd.Timestamp(METHODOLOGY_CHANGE_DATE)
    st.markdown("### Inflection points")
    st.caption(
        f"{len(anomalies)} detected — daily-delta z-score ≥ 1.5 with absolute change ≥ 10 ads."
    )
    for a in anomalies:
        direction = "↑" if a["delta"] > 0 else "↓"
        note = (
            " — coincides with scraper methodology change, treat with caution"
            if a["date"] == methodology_date else ""
        )
        st.markdown(
            f"- **{a['date'].date()}** — {a['competitor']} {direction} "
            f"**{abs(a['delta'])} ads** "
            f"({a['prev']} → {a['curr']}, z = {a['z']:+.1f}){note}"
        )

st.markdown("### Ad volume per competitor")

# Fill zeros for missing (date, competitor) pairs so every competitor renders
# as a full series — otherwise competitors with a single day of data (ElliQ,
# Heritage Whisper) don't draw at all under mode="lines".
vol_wide = df_view.groupby(["date", "competitor"]).size().unstack(fill_value=0).sort_index()
# Render lowest-volume competitors first so the busiest lines paint on top.
competitor_order = vol_wide.sum().sort_values(ascending=True).index.tolist()

fig_vol = go.Figure()
for competitor in competitor_order:
    series = vol_wide[competitor]
    fig_vol.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        mode="lines",
        name=competitor,
        line=dict(color=comp_color(competitor), width=1.5, shape="spline", smoothing=0.6),
        hovertemplate=f"<b>{competitor}</b><br>%{{x|%b %d}}: %{{y}} ads<extra></extra>",
    ))
fig_vol.update_layout(**_clean_layout(380), hovermode="closest")
_add_methodology_marker(fig_vol, with_label=True)
st.plotly_chart(fig_vol, use_container_width=True)

st.markdown("### Tone presence over time")
st.caption("Count of ads tagged with each tone (one ad can carry multiple tones).")

tone_rows = []
for _, row in df_view.iterrows():
    for tone in _all_tones(row["ad_copy"]):
        tone_rows.append({"date": row["date"], "tone": tone})
tone_df = pd.DataFrame(tone_rows)

if tone_df.empty:
    _empty_state("No tone data in the selected window.")
else:
    tone_counts = tone_df.groupby(["date", "tone"]).size().reset_index(name="count")

    fig_tone = go.Figure()
    for tone in TONE_KEYWORDS.keys():
        series = tone_counts[tone_counts["tone"] == tone].sort_values("date")
        if series.empty:
            continue
        tone_hex = TONE_COLORS.get(tone, COLORS["muted"])
        fig_tone.add_trace(go.Scatter(
            x=series["date"],
            y=series["count"],
            mode="lines",
            name=tone,
            line=dict(width=1.5, color=tone_hex, shape="spline", smoothing=0.6),
            hovertemplate=f"<b>{tone}</b><br>%{{x|%b %d}}: %{{y}} ads<extra></extra>",
        ))
    fig_tone.update_layout(**_clean_layout(320), hovermode="closest")
    _add_methodology_marker(fig_tone, with_label=False)
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
fig_total.update_layout(**_clean_layout(260), hovermode="closest", showlegend=False)
_add_methodology_marker(fig_total, with_label=False)
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
