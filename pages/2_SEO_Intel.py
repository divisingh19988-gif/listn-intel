"""
SEO Intel — keyword opportunity map, content clusters, and content roadmap.

REMOVED:
  • Bubble chart (Volume vs Position, bubble size = KD) — was noise
  • "Keywords to Avoid" section — was noise

ADDED:
  • 4 hand-curated clusters with window badges (Mother's Day, Father's Day,
    Evergreen, Competitor Alternatives)
  • "Remento Cannibalization Gap" insight card
  • 6-post Content Roadmap with live countdown + overdue/within-7d border colors
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from lib.theme import inject_global_css, COLORS, comp_color, window_badge
from lib.data_freshness import show_freshness_banner
from lib.synthesis import SEO_CLUSTERS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="SEO Intel · Listn", page_icon="🔍", layout="wide")
inject_global_css()
show_freshness_banner()

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "seo_raw_latest.json"


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_seo() -> tuple[dict, pd.DataFrame, str]:
    if not DATA_FILE.exists():
        return {}, pd.DataFrame(), ""
    with open(DATA_FILE) as f:
        data = json.load(f)
    rows = []
    for comp, info in data.get("competitors", {}).items():
        for kw in info.get("keywords", []):
            rows.append({
                "competitor": comp,
                "keyword":    kw.get("keyword", ""),
                "volume":     int(kw.get("search_volume") or 0),
                "position":   int(kw.get("position") or 0),
                "kd":         int(kw.get("keyword_difficulty") or 0),
                "url":        kw.get("url", ""),
            })
    return data, pd.DataFrame(rows), data.get("fetched_date", "")


data, kw_df, fetched_date = load_seo()
if kw_df.empty:
    st.error(
        "No SEO data found in `data/seo_raw_latest.json`. "
        "Run `python scrapers/seo_monitor.py` first."
    )
    st.stop()


# ── Header + 4 stat cards ─────────────────────────────────────────────────────
total_kw_tracked = len(kw_df)
avg_kd = round(kw_df["kd"].mean(), 1) if total_kw_tracked else 0
all_cluster_kws = [k for c in SEO_CLUSTERS for k in c["keywords"]]
total_cluster_volume = sum(k[1] for k in all_cluster_kws)
n_clusters = len(SEO_CLUSTERS)
n_posts = 6

st.markdown(
    f'<h1 style="margin-bottom:0.2rem;">🔍 SEO Intel</h1>'
    f'<p class="muted" style="margin-top:0;">'
    f"DataForSEO · fetched {fetched_date} · {total_kw_tracked} competitor keywords tracked"
    "</p>",
    unsafe_allow_html=True,
)


def _stat(value, label, *, color=None, big=True):
    color = color or COLORS["accent"]
    size = "2.1rem" if big else "1.4rem"
    return (
        '<div class="stat-card">'
        f'<div class="stat-value" style="color:{color};font-size:{size};">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        '</div>'
    )


cards_html = '<div class="stat-grid">'
cards_html += _stat(total_kw_tracked, "Competitor keywords tracked")
cards_html += _stat(avg_kd, "Avg competitor KD")
cards_html += _stat(f"{total_cluster_volume:,}", "Total cluster volume / mo", color=COLORS["evergreen"], big=False)
cards_html += _stat(n_posts, "Content posts planned", color=COLORS["soon"])
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Keyword Clusters
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🎯 Keyword clusters")
st.markdown(
    f'<p class="muted" style="margin-top:-0.5rem;font-size:0.88rem;">'
    "4 hand-curated clusters · sorted by deadline / commercial intent"
    "</p>",
    unsafe_allow_html=True,
)


def kd_pill(kd: int) -> str:
    if kd <= 10:
        bg, fg = "#10B98122", "#10B981"
    elif kd <= 20:
        bg, fg = f"{COLORS['soon']}22", COLORS["soon"]
    else:
        bg, fg = "#F9731622", "#F97316"
    return (
        f'<span style="display:inline-block;border-radius:999px;padding:2px 9px;'
        f'font-size:0.75rem;font-weight:700;background:{bg};color:{fg};'
        f'border:1px solid {fg}55;min-width:32px;text-align:center;">{kd}</span>'
    )


def render_cluster(cluster: dict) -> None:
    today = date.today()
    deadline = cluster.get("deadline")
    if deadline:
        days = (deadline - today).days
        deadline_text = f"Deadline: <strong>{deadline.strftime('%b %d, %Y')}</strong> · {days} days away"
    else:
        deadline_text = "<strong>Evergreen</strong> — no fixed deadline"

    badge = window_badge(cluster["window"])
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:0.75rem;'
        'flex-wrap:wrap;margin:0.85rem 0 0.5rem;">'
        f'<h3 style="margin:0;">{cluster["name"]}</h3>'
        f'{badge}'
        f'<span class="muted" style="font-size:0.82rem;">{deadline_text}</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    rows_html = (
        f'<div style="border:1px solid {COLORS["border"]};border-radius:12px;overflow:hidden;'
        'animation:fadeInUp 0.4s ease both;">'
        '<div style="display:grid;grid-template-columns: 3fr 1fr 0.6fr;'
        f'background:{COLORS["surface"]};padding:0.55rem 1rem;'
        f'font-size:0.72rem;font-weight:700;color:{COLORS["muted"]};'
        'text-transform:uppercase;letter-spacing:0.08em;gap:0.5rem;">'
        '<span>Keyword</span><span>Volume / mo</span><span>KD</span>'
        '</div>'
    )
    for i, (kw, vol, kd) in enumerate(cluster["keywords"]):
        bg = "rgba(79,142,247,0.04)" if i % 2 else "transparent"
        rows_html += (
            '<div style="display:grid;grid-template-columns: 3fr 1fr 0.6fr;'
            f'padding:0.55rem 1rem;gap:0.5rem;background:{bg};'
            f'border-top:1px solid {COLORS["border"]};font-size:0.86rem;'
            'align-items:center;">'
            f'<span style="font-family:\'SF Mono\',monospace;font-size:0.85rem;'
            f'color:{COLORS["text"]};">{kw}</span>'
            f'<span style="color:{COLORS["accent"]};font-weight:700;">{vol:,}</span>'
            f'<span>{kd_pill(kd)}</span>'
            '</div>'
        )
    rows_html += "</div>"
    st.markdown(rows_html, unsafe_allow_html=True)


for cluster in SEO_CLUSTERS:
    render_cluster(cluster)

# ═══════════════════════════════════════════════════════════════════════════════
# Remento Cannibalization Gap insight
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    '<div class="insight-card blue">'
    '<div class="insight-title">💡 Remento Cannibalization Gap</div>'
    '<div class="insight-body">'
    'Remento has <strong>4 competing "StoryWorth review" pages</strong> '
    "splitting authority across identical queries. A single focused Listn "
    '"remento alternative" post can outrank all 4.'
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Content Roadmap — 6 posts
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📝 Content roadmap")
st.markdown(
    f'<p class="muted" style="margin-top:-0.5rem;font-size:0.88rem;">'
    "6 posts · ordered by publish-by date · live countdown"
    "</p>",
    unsafe_allow_html=True,
)

POSTS = [
    {
        "num": "01",
        "publish_by": date(2026, 4, 30),
        "window": "SOON",
        "title": "What to Ask Your Dad Before Father's Day: 50 Questions Worth Recording in His Own Voice",
        "primary": ("fathers day gift ideas", 74000, 0),
        "secondary": ["meaningful fathers day gift", "gift for dad from daughter"],
        "why": "6.5 weeks to rank. KD 0. No memory app has written this post.",
    },
    {
        "num": "02",
        "publish_by": date(2026, 5, 1),
        "window": "URGENT",
        "title": "The Mother's Day Gift That Actually Lasts: Why Her Voice Is Worth More Than Flowers",
        "primary": ("meaningful mothers day gift", 8100, 12),
        "secondary": ["gift for mom from daughter", "mothers day gift for mom who has everything"],
        "why": "9 days to index before May 10.",
    },
    {
        "num": "03",
        "publish_by": date(2026, 5, 10),
        "window": "COMMERCIAL INTENT",
        "title": "Looking for a Remento Alternative? Here's What Actually Matters in a Memory App",
        "primary": ("remento alternative", 1900, 8),
        "secondary": ["storyworth alternative", "heritage whisper alternative"],
        "why": "Remento's 4 cannibalized pages create a clear opening.",
    },
    {
        "num": "04",
        "publish_by": date(2026, 5, 15),
        "window": "EVERGREEN",
        "title": "The Gift That Won't Get Donated: Why Voice Memories Beat Any Physical Present for Grandparents",
        "primary": ("grandparent gift ideas", 14800, 0),
        "secondary": ["gift for grandma", "gift for grandpa"],
        "why": "KD 0 · 14.8K volume · Meminto's #99 ranking is beatable.",
    },
    {
        "num": "05",
        "publish_by": date(2026, 6, 1),
        "window": "EVERGREEN",
        "title": "How to Record Your Parent's Life Stories Before It's Too Late",
        "primary": ("how to record parents life stories", 2900, 8),
        "secondary": ["record grandparents stories", "recording memories before dementia"],
        "why": "Targets caregiver segment at peak emotional urgency.",
    },
    {
        "num": "06",
        "publish_by": date(2026, 6, 15),
        "window": "SOON",
        "title": "50 Questions to Ask Your Parents Before It's Too Late",
        "primary": ("questions to record with grandparents", 1300, 5),
        "secondary": ["questions to ask dad before its too late"],
        "why": "Father's Day pairing for Post 01 — same emotional hook, deeper questions.",
    },
]


def post_card(post: dict) -> str:
    today = date.today()
    days_to = (post["publish_by"] - today).days
    if days_to < 0:
        border_color = COLORS["urgent"]
        countdown = f"OVERDUE by {abs(days_to)}d"
        countdown_color = COLORS["urgent"]
    elif days_to <= 7:
        border_color = COLORS["soon"]
        countdown = f"in {days_to}d"
        countdown_color = COLORS["soon"]
    else:
        border_color = COLORS["accent"]
        countdown = f"in {days_to}d"
        countdown_color = COLORS["muted"]

    primary_kw, vol, kd = post["primary"]
    chips = "".join(
        f'<span style="display:inline-block;background:{COLORS["accent"]}1A;'
        f'color:{COLORS["accent"]};border:1px solid {COLORS["accent"]}33;'
        f'border-radius:999px;padding:2px 9px;font-size:0.72rem;'
        f'margin:2px 4px 2px 0;font-family:monospace;">{kw}</span>'
        for kw in post["secondary"]
    )
    return (
        '<div style="background:{surface};border:1px solid {border};'
        'border-left:4px solid {border_color};border-radius:14px;'
        'padding:1.15rem 1.3rem;margin-bottom:0.85rem;height:100%;'
        'animation:fadeInUp 0.4s ease both;position:relative;">'
        '<div style="display:flex;justify-content:space-between;align-items:center;'
        'margin-bottom:0.5rem;">'
        '<div style="font-size:0.68rem;font-weight:700;letter-spacing:0.1em;'
        'color:{accent};text-transform:uppercase;">Post {num} · {window_badge_html}</div>'
        '<div style="font-size:0.78rem;font-weight:700;color:{countdown_color};">'
        '{countdown} ({publish_by})</div></div>'
        '<div style="font-size:1rem;font-weight:700;color:{text};line-height:1.4;'
        'margin-bottom:0.6rem;">{title}</div>'
        '<div style="margin-bottom:0.5rem;">'
        '<span style="font-family:monospace;background:{accent}26;color:{accent};'
        'border-radius:999px;padding:2px 9px;font-size:0.78rem;font-weight:700;">'
        '{primary_kw} · {vol:,}/mo · KD {kd}</span>'
        '</div>'
        '<div style="margin-bottom:0.6rem;">{chips}</div>'
        '<div style="color:{muted};font-size:0.84rem;line-height:1.55;font-style:italic;">'
        '<strong style="color:{text};font-style:normal;">Why:</strong> {why}</div>'
        '</div>'
    ).format(
        surface=COLORS["surface"], border=COLORS["border"], border_color=border_color,
        accent=COLORS["accent"], text=COLORS["text"], muted=COLORS["muted"],
        countdown_color=countdown_color, num=post["num"],
        window_badge_html=post["window"],
        countdown=countdown, publish_by=post["publish_by"].strftime("%b %d"),
        title=post["title"], primary_kw=primary_kw, vol=vol, kd=kd,
        chips=chips, why=post["why"],
    )


col_a, col_b = st.columns(2)
for i, post in enumerate(POSTS):
    (col_a if i % 2 == 0 else col_b).markdown(post_card(post), unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Competitor Keyword Map (kept — useful)
# ═══════════════════════════════════════════════════════════════════════════════
import plotly.express as px
from lib.theme import PLOTLY_LAYOUT

st.markdown("## 🗺 Competitor keyword map")
st.markdown(
    f'<p class="muted" style="margin-top:-0.5rem;font-size:0.88rem;">'
    "Top 10 keywords per competitor — search volume view"
    "</p>",
    unsafe_allow_html=True,
)
ctrl_col, chart_col = st.columns([1, 3])
with ctrl_col:
    selected = st.selectbox("Competitor", sorted(kw_df["competitor"].unique()))
with chart_col:
    top10 = (
        kw_df[kw_df["competitor"] == selected]
        .sort_values("volume", ascending=False)
        .head(10)
        .copy()
    )
    top10["label"] = top10["keyword"].str[:42]
    plot_df = top10.sort_values("volume")
    fig = px.bar(
        plot_df,
        x="volume",
        y="label",
        orientation="h",
        color="kd",
        color_continuous_scale=[
            [0,   COLORS["evergreen"]],
            [0.5, COLORS["soon"]],
            [1,   COLORS["urgent"]],
        ],
        text=plot_df["volume"].apply(lambda v: f"{v:,.0f}"),
        labels={"volume": "Monthly searches", "label": "", "kd": "KD"},
        title=f"{selected} · Top 10 by search volume",
    )
    fig.update_traces(textposition="outside", textfont_color=COLORS["text"])
    fig.update_layout(
        **PLOTLY_LAYOUT,
        height=420,
        title_font_color=COLORS["text"],
        title_font_size=13,
        transition_duration=400,
    )
    fig.update_coloraxes(
        colorbar_title="KD",
        colorbar_tickfont_color=COLORS["muted"],
        colorbar_title_font_color=COLORS["text"],
    )
    st.plotly_chart(fig, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    "SEO Intel · Listn · DataForSEO + curated cluster strategy</p>",
    unsafe_allow_html=True,
)
