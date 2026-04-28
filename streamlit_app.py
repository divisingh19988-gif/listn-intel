import glob
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from io import BytesIO

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

<<<<<<< HEAD
from lib.theme import inject_global_css, COLORS, stat_card
from lib.data_freshness import show_freshness_banner
from lib.synthesis import (
    get_creative_move,
    get_content_move,
    count_new_ads_this_week,
    next_deadline,
    ai_readiness_leader,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Listn Intel · This Week's Moves",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()
show_freshness_banner()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="font-size:1.1rem;font-weight:800;color:{COLORS["accent"]};'
        'letter-spacing:0.02em;padding:0.25rem 0 0.75rem 0;'
        f'border-bottom:1px solid {COLORS["border"]};margin-bottom:0.75rem;">'
        '🎙 Listn Intel</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="muted" style="font-size:0.8rem;line-height:1.6;">'
        "Use the <strong>Pages</strong> menu above to navigate between "
        "Meta Intel, SEO Intel, AI Readiness, the Action Tracker, and "
        "Reports Archive."
        "</p>",
        unsafe_allow_html=True,
    )

# ── Header ────────────────────────────────────────────────────────────────────
today = date.today()
week_label = today.strftime("%B %-d, %Y") if hasattr(today, "strftime") else str(today)

st.markdown(
    f'<h1 style="margin-bottom:0.2rem;">This Week\'s Moves</h1>'
    f'<p class="muted" style="font-size:0.92rem;margin-top:0;">'
    f"Two actions for week of {week_label}. "
    "Pulled from live Meta + SEO data."
    "</p>",
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

# ── Two big cards: Creative Move + Content Move ───────────────────────────────
creative = get_creative_move()
content = get_content_move()


def _move_card(*, kicker: str, kicker_color: str, do: str, because: str,
               source_ref: str, link_label: str, link_target: str) -> str:
    return (
        '<div style="background:{surface};border:1px solid {border};'
        'border-left:4px solid {kicker_color};border-radius:14px;'
        'padding:1.4rem 1.6rem;height:100%;display:flex;flex-direction:column;'
        'animation:fadeInUp 0.45s ease both;">'
        '<div style="font-size:0.72rem;font-weight:700;letter-spacing:0.1em;'
        'text-transform:uppercase;color:{kicker_color};margin-bottom:0.6rem;">'
        '{kicker}'
        '</div>'
        '<div style="font-size:1.05rem;font-weight:700;color:{text};line-height:1.45;'
        'margin-bottom:0.85rem;">Do this: {do}</div>'
        '<div style="color:{muted};font-size:0.88rem;line-height:1.6;'
        'margin-bottom:0.85rem;"><strong style="color:{text};">Because:</strong> {because}</div>'
        '<div style="color:{muted};font-size:0.78rem;line-height:1.5;font-style:italic;'
        'margin-top:auto;padding-top:0.75rem;border-top:1px solid {border};">'
        '{source_ref}</div>'
        '<a href="{link_target}" class="insight-link">{link_label} →</a>'
        '</div>'
    ).format(
        surface=COLORS["surface"], border=COLORS["border"], text=COLORS["text"],
        muted=COLORS["muted"], kicker_color=kicker_color, kicker=kicker,
        do=do, because=because, source_ref=source_ref,
        link_label=link_label, link_target=link_target,
    )


col_left, col_right = st.columns(2)
with col_left:
    st.markdown(
        _move_card(
            kicker="🎯 Creative Move (Meta signal)",
            kicker_color=COLORS["accent"],
            do=creative["do"],
            because=creative["because"],
            source_ref=f"Source ad: {creative['source_ref']}" if creative.get("source_ref") else "",
            link_label="View supporting ads",
            link_target="Meta_Intel",
        ),
        unsafe_allow_html=True,
    )

with col_right:
    window_pill_color = {
        "URGENT":   COLORS["urgent"],
        "SOON":     COLORS["soon"],
        "EVERGREEN": COLORS["evergreen"],
        "COMMERCIAL INTENT": COLORS["accent"],
    }.get(content.get("window", ""), COLORS["accent"])
    st.markdown(
        _move_card(
            kicker=f"📝 Content Move (SEO signal · {content.get('cluster', '')})",
            kicker_color=window_pill_color,
            do=content["do"],
            because=content["because"],
            source_ref=(
                f"Cluster: {content['cluster']} · KW: {content['keyword']} · "
                f"Vol {content['volume']:,}/mo · KD {content['kd']}"
            ),
            link_label="View keyword cluster",
            link_target="SEO_Intel",
        ),
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── 3 small supporting stats ──────────────────────────────────────────────────
new_ads = count_new_ads_this_week()
deadline = next_deadline()
leader = ai_readiness_leader()

stats_html = '<div class="stat-grid">'
stats_html += stat_card(
    value=str(new_ads),
    label="New competitor ads this week",
    implication="Started in the last 7 days across all tracked competitors.",
    accent=COLORS["accent"],
)
stats_html += stat_card(
    value=deadline["label"] if deadline.get("days") is not None else deadline["label"],
    label="Next deadline",
    implication=f"Cluster: {deadline['cluster']}",
    accent=COLORS["urgent"] if (deadline.get("days") or 0) <= 14 else COLORS["soon"],
)
stats_html += stat_card(
    value=f"{leader['name']}",
    label="AI Readiness leader",
    implication=f"Score: {leader['score']}/100 — Listn must close the gap.",
    accent=COLORS["evergreen"],
)
stats_html += "</div>"
st.markdown(stats_html, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    "Listn Intel · live from Meta Ad Library + DataForSEO · "
    f"week of {week_label}</p>",
=======
# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Listn Intelligence",
    page_icon="🎙",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Base ── */
  html { scroll-behavior: smooth; }
  .stApp { background-color: #1E0A2E; font-family: system-ui, -apple-system, sans-serif; }
  .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1400px; }

  /* ── Headings ── */
  h1, h2, h3, h4 { color: #A78BFA !important; font-family: system-ui, -apple-system, sans-serif; font-weight: 700; }
  p, li, td, th, label { color: #E2D9F3 !important; font-family: system-ui, -apple-system, sans-serif; }

  /* ── Animated header gradient ── */
  @keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
  .header-wrap {
    background: linear-gradient(-45deg, #1E0A2E, #3B0764, #4C1D95, #6D28D9, #7C3AED, #A78BFA);
    background-size: 400% 400%;
    animation: gradientShift 10s ease infinite;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
  }
  .header-wrap::after {
    content: '';
    position: absolute;
    inset: 0;
    background: rgba(30, 10, 46, 0.35);
    border-radius: 16px;
  }
  .header-content { position: relative; z-index: 1; }
  .header-title {
    font-size: 2.2rem; font-weight: 800; color: #F3F0FF !important;
    letter-spacing: -0.02em; margin: 0; line-height: 1.2;
  }
  .header-sub { color: #DDD6FE !important; font-size: 0.9rem; margin-top: 0.4rem; }

  /* ── KPI cards ── */
  .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 0.5rem; }
  .kpi-card {
    background: linear-gradient(135deg, #2D1150 0%, #1a0838 100%);
    border: 1px solid rgba(167,139,250,0.45);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 0 24px rgba(167,139,250,0.15), inset 0 0 20px rgba(167,139,250,0.04);
    transition: box-shadow 0.3s ease, transform 0.2s ease;
  }
  .kpi-card:hover {
    box-shadow: 0 0 36px rgba(167,139,250,0.3), inset 0 0 20px rgba(167,139,250,0.08);
    transform: translateY(-2px);
  }
  .kpi-icon { font-size: 1.4rem; margin-bottom: 0.4rem; }
  .kpi-value { font-size: 2.4rem; font-weight: 800; color: #F3F0FF !important; line-height: 1; margin-bottom: 0.25rem; }
  .kpi-label { font-size: 0.78rem; color: #A78BFA !important; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }

  /* ── Dividers ── */
  hr { border: none; border-top: 1px solid rgba(167,139,250,0.2); margin: 1.5rem 0; }

  /* ── Sidebar ── */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #160822 0%, #1E0A2E 100%);
    border-right: 1px solid rgba(167,139,250,0.15);
  }
  .sidebar-logo {
    font-size: 1.4rem; font-weight: 800; color: #A78BFA !important;
    letter-spacing: -0.02em; padding: 0.5rem 0 1rem 0; border-bottom: 1px solid rgba(167,139,250,0.2);
    margin-bottom: 1rem;
  }
  .sidebar-logo span { color: #DDD6FE !important; }
  .sidebar-nav a {
    color: #C4B5FD !important; text-decoration: none; display: flex; align-items: center;
    gap: 0.5rem; padding: 0.45rem 0.6rem; border-radius: 8px;
    font-size: 0.83rem; transition: background 0.2s ease, color 0.2s ease;
  }
  .sidebar-nav a:hover { background: rgba(167,139,250,0.12); color: #F3F0FF !important; }
  .sidebar-meta { color: rgba(167,139,250,0.5) !important; font-size: 0.7rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid rgba(167,139,250,0.1); }

  /* ── Ad cards (top 10, new this week) ── */
  .ad-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(167,139,250,0.18);
    border-radius: 12px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.65rem;
    transition: background 0.2s ease, border-color 0.2s ease;
  }
  .ad-card:hover { background: rgba(167,139,250,0.06); border-color: rgba(167,139,250,0.35); }
  .ad-card-alt { background: rgba(167,139,250,0.04); }
  .ad-card .days-num { float: right; font-size: 1.6rem; font-weight: 800; color: #A78BFA !important; line-height: 1; }
  .ad-card .days-unit { float: right; font-size: 0.7rem; color: #7C3AED !important; margin-top: 0.6rem; margin-left: 0.2rem; }
  .ad-card .copy-text { color: #C4B5FD !important; font-size: 0.85rem; margin-top: 0.45rem; line-height: 1.55; }
  .ad-card .meta-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }

  /* ── Competitor badge pills ── */
  .badge {
    display: inline-block; border-radius: 20px; padding: 2px 10px;
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;
  }
  .badge-remento    { background: rgba(167,139,250,0.2); color: #A78BFA !important; border: 1px solid rgba(167,139,250,0.4); }
  .badge-meminto    { background: rgba(96,165,250,0.2);  color: #60A5FA !important; border: 1px solid rgba(96,165,250,0.4);  }
  .badge-storykeeper{ background: rgba(52,211,153,0.2);  color: #34D399 !important; border: 1px solid rgba(52,211,153,0.4);  }
  .badge-storyworth { background: rgba(252,211,77,0.2);  color: #FCD34D !important; border: 1px solid rgba(252,211,77,0.4);  }
  .badge-keepsake   { background: rgba(244,114,182,0.2); color: #F472B6 !important; border: 1px solid rgba(244,114,182,0.4); }
  .badge-other      { background: rgba(148,163,184,0.2); color: #94A3B8 !important; border: 1px solid rgba(148,163,184,0.4); }

  /* ── Status dot ── */
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
  .dot-green { background: #34D399; box-shadow: 0 0 6px #34D399; }
  .dot-red   { background: #F87171; box-shadow: 0 0 6px #F87171; }

  /* ── Tone tag ── */
  .tone-tag {
    display: inline-block; border-radius: 20px; padding: 1px 8px;
    font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
  }

  /* ── Glassmorphism playbook cards ── */
  .glass-high {
    background: rgba(167,139,250,0.06);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(167,139,250,0.3);
    border-left: 4px solid #A78BFA;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 1rem;
    box-shadow: 0 0 20px rgba(167,139,250,0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .glass-high:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(167,139,250,0.2); }
  .glass-medium {
    background: rgba(109,40,217,0.08);
    backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(109,40,217,0.3);
    border-left: 4px solid #6D28D9;
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 1rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .glass-medium:hover { transform: translateY(-3px); box-shadow: 0 8px 30px rgba(109,40,217,0.2); }
  .priority-pill-high {
    display: inline-block; background: #A78BFA; color: #1E0A2E !important;
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em;
    border-radius: 20px; padding: 2px 10px; margin-bottom: 0.5rem;
  }
  .priority-pill-medium {
    display: inline-block; background: #4C1D95; color: #DDD6FE !important;
    font-size: 0.65rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em;
    border-radius: 20px; padding: 2px 10px; margin-bottom: 0.5rem;
  }
  .card-title { color: #F3F0FF !important; font-size: 0.95rem; font-weight: 700; margin-bottom: 0.3rem; line-height: 1.4; }
  .card-action { color: #C4B5FD !important; font-size: 0.83rem; line-height: 1.55; margin-bottom: 0.35rem; }
  .card-why-label { color: #7C3AED !important; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; }
  .card-why { color: #9CA3AF !important; font-size: 0.82rem; line-height: 1.5; }

  /* ── Whitespace box ── */
  .ws-box {
    background: linear-gradient(135deg, rgba(167,139,250,0.08) 0%, rgba(109,40,217,0.06) 100%);
    border: 1px solid rgba(167,139,250,0.35);
    border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem;
  }
  .ws-label { color: #A78BFA !important; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
  .ws-row { color: #E2D9F3 !important; font-size: 0.9rem; line-height: 1.7; }
  .ws-hl { color: #C4B5FD !important; font-weight: 700; }

  /* ── New vs Stopped cards ── */
  .card-new     { background: rgba(52,211,153,0.05); border: 1px solid rgba(52,211,153,0.25); border-left: 3px solid #34D399; border-radius: 10px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem; }
  .card-stopped { background: rgba(248,113,113,0.05); border: 1px solid rgba(248,113,113,0.25); border-left: 3px solid #F87171; border-radius: 10px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem; }
  .card-new .copy-text, .card-stopped .copy-text { color: #C4B5FD !important; font-size: 0.83rem; margin-top: 0.3rem; line-height: 1.5; }

  /* ── Weekly delta box ── */
  .delta-box {
    background: rgba(167,139,250,0.07);
    border: 1px solid rgba(167,139,250,0.25);
    border-left: 4px solid #A78BFA;
    border-radius: 12px; padding: 1.2rem 1.5rem;
  }
  .delta-box p { color: #E2D9F3 !important; font-size: 0.92rem; line-height: 1.7; margin: 0; }

  /* ── Search input glow ── */
  .stTextInput input:focus { border-color: #A78BFA !important; box-shadow: 0 0 0 2px rgba(167,139,250,0.25) !important; }

  /* ── Dataframe ── */
  .stDataFrame { border-radius: 10px; }
  [data-testid="stDataFrame"] thead tr th { background: #2D1150 !important; color: #A78BFA !important; }

  /* ── Alert / info ── */
  .stAlert { background: rgba(167,139,250,0.07) !important; border-color: rgba(167,139,250,0.25) !important; border-radius: 10px; }

  /* ── Buttons ── */
  .stButton button { border-radius: 8px; font-weight: 600; }

  /* ── Status legend ── */
  .status-legend { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 0.75rem; }
  .status-dot { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; }
  .s-grey   { color: #6B7280 !important; }
  .s-yellow { color: #FCD34D !important; }
  .s-blue   { color: #60A5FA !important; }
  .s-green  { color: #34D399 !important; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE         = Path(__file__).parent
FETCHED_DATE = pd.Timestamp("2026-04-23")
PURPLE_SCALE = ["#4C1D95", "#5B21B6", "#6D28D9", "#7C3AED", "#8B5CF6", "#A78BFA", "#C4B5FD"]
TRANSPARENT  = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#E2D9F3",
    xaxis=dict(gridcolor="rgba(167,139,250,0.15)", color="#A78BFA", showline=False, zeroline=False),
    yaxis=dict(gridcolor="rgba(167,139,250,0.15)", color="#E2D9F3", showline=False, zeroline=False),
    margin=dict(l=0, r=40, t=20, b=10),
)
COMP_COLOR = {
    "Remento":     "#A78BFA",
    "Meminto":     "#60A5FA",
    "Storykeeper": "#34D399",
    "StoryWorth":  "#FCD34D",
    "Keepsake":    "#F472B6",
}
TONE_KEYWORDS = {
    "nostalgia":     ["memory", "remember", "story", "voice", "preserve", "legacy"],
    "urgency":       ["now", "today", "don't wait", "before", "last chance", "limited"],
    "gifting":       ["gift", "give", "present", "birthday", "christmas", "mother"],
    "fear of loss":  ["gone", "lost", "too late", "forget", "never", "disappear"],
    "pride":         ["hero", "proud", "amazing", "incredible", "legacy"],
    "transactional": ["save", "discount", "off", "price", "only $", "free"],
}
TONE_COLORS = {
    "nostalgia": "#7C3AED", "urgency": "#F87171", "gifting": "#34D399",
    "fear of loss": "#F59E0B", "pride": "#A78BFA", "transactional": "#60A5FA",
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def tag_tone(text):
    t = str(text or "").lower()
    for tone, words in TONE_KEYWORDS.items():
        if any(w in t for w in words):
            return tone
    return "nostalgia"

def all_tones(text):
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ["nostalgia"]
    t = str(text).lower()
    return [tone for tone, words in TONE_KEYWORDS.items() if any(w in t for w in words)] or ["nostalgia"]

def extract_cta(row):
    v = row.get("cta")
    if v and not (isinstance(v, float) and pd.isna(v)) and str(v).strip().lower() not in ("none", ""):
        return str(v).strip()
    copy = str(row.get("ad_copy") or "").lower()
    if "shop now"    in copy: return "Shop Now"
    if "learn more"  in copy: return "Learn More"
    if "install"     in copy: return "Install Now"
    if "get started" in copy: return "Get Started"
    return "None"

def comp_badge(name):
    key = name.lower().replace(" ", "")
    cls = f"badge-{key}" if key in ("remento", "meminto", "storykeeper", "storyworth", "keepsake") else "badge-other"
    return f'<span class="badge {cls}">{name}</span>'

def tone_tag(tone):
    c = TONE_COLORS.get(tone, "#9CA3AF")
    return f'<span class="tone-tag" style="background:rgba(0,0,0,0.3);color:{c}!important;border:1px solid {c}66;">{tone}</span>'

def kpi_html(icon, label, value):
    return f"""<div class="kpi-card">
      <div class="kpi-icon">{icon}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{label}</div>
    </div>"""

# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_ads():
    files = sorted(glob.glob(str(BASE / "ads_scraped_*.json")))
    if files:
        path = files[-1]
    else:
        path = BASE / "sample_data" / "ads_scraped_latest.json"
    with open(path) as f:
        raw = json.load(f)
    rows = []
    for ads in raw["competitors"].values():
        rows.extend(ads)
    df = pd.DataFrame(rows)
    df["start_date"]       = pd.to_datetime(df["start_date"], errors="coerce")
    df["stop_date"]        = pd.to_datetime(df["stop_date"],  errors="coerce")
    df["is_active"]        = df["stop_date"].isna()
    df["days_running"]     = pd.to_numeric(df["days_running"], errors="coerce").fillna(0).astype(int)
    df["snippet"]          = df["ad_copy"].fillna("").str[:130].str.strip() + "..."
    df["hover_snippet"]    = df["ad_copy"].fillna("").str[:90].str.strip() + "..."
    df["days_since_start"] = (FETCHED_DATE - df["start_date"]).dt.days.clip(lower=0)
    df["is_new14"]         = df["days_since_start"] <= 14
    df["is_new7"]          = df["days_since_start"] <= 7
    df["stopped_this_week"]= df["stop_date"].notna() & (df["stop_date"] >= FETCHED_DATE - pd.Timedelta(days=7))
    df["tone"]             = df["ad_copy"].fillna("").apply(tag_tone)
    df["cta_label"]        = df.apply(lambda r: extract_cta(r.to_dict()), axis=1)
    df["end_date"]         = df["stop_date"].fillna(FETCHED_DATE)
    n_competitors          = len(raw["competitors"])
    return df, raw["fetched_date"], raw["total_ads"], n_competitors

df, fetched_date, total_ads, n_competitors = load_ads()
active_df    = df[df["is_active"]]
new14_df     = df[df["is_new14"]]
new7_df      = df[df["is_new7"]]
stopped7_df  = df[df["stopped_this_week"]]
competitors  = sorted(df["competitor"].dropna().unique())

# ── Playbook ──────────────────────────────────────────────────────────────────
PLAYBOOK = [
    {
        "priority": "HIGH",
        "title": "Make the elder the hero of your adult-child-targeted ads",
        "action": "Keep targeting adult children (35-55) on Meta but reframe creatives — show the parent as a protagonist with a remarkable life, not a passive gift recipient.",
        "why": "Every competitor shows the elder as an object to be preserved. Listn's angle: your parent has a story that will blow your mind — and you haven't asked yet.",
    },
    {
        "priority": "HIGH",
        "title": "Make voice the product, not the book",
        "action": "Build brand identity around the irreplaceable nature of a human voice, not a printed artifact.",
        "why": "Remento quotes 'you will always have their voice' but does not build their brand around it — Listn can own this entirely.",
    },
    {
        "priority": "HIGH",
        "title": "Test grief-adjacent urgency with warmth",
        "action": "Lead with a specific wistful moment ('I forgot to ask him what he was most proud of') then redirect to possibility, not guilt.",
        "why": "The Storykeeper just started testing this tone — 5 days old at scrape time — Listn must move faster.",
    },
    {
        "priority": "MEDIUM",
        "title": "Own specificity over autobiography",
        "action": "Run ads zoomed into one moment — 'Ask her about the summer of 1968' — not 'capture their whole life story'.",
        "why": "Entire category frames memory preservation as homework — specificity removes the overwhelm entirely.",
    },
    {
        "priority": "MEDIUM",
        "title": "Target the caregiver segment",
        "action": "Create a dedicated campaign for adult children of parents with early cognitive decline.",
        "why": "Remento touched this once (18 days, then stopped) — high-urgency audience with nowhere to go in the market.",
    },
    {
        "priority": "MEDIUM",
        "title": "Test the multilingual / cultural legacy angle",
        "action": "'Some stories can only be told in the language they were lived in' — target immigrant families directly.",
        "why": "Zero competitors have run a single ad acknowledging multilingual families — enormous untapped scale.",
    },
    {
        "priority": "MEDIUM",
        "title": "Reach elders directly through non-Meta channels",
        "action": "Partner with senior Facebook Groups, senior living facility newsletters, and retirement community noticeboards.",
        "why": "Elders who self-motivate to preserve their own story are higher-retention users — acquisition channel is community, not paid social.",
    },
]

# ── Sidebar ───────────────────────────────────────────────────────────────────
NAV = [
    ("📊", "Total Ads Chart",       "total-ads-chart"),
    ("🎯", "Strategic Playbook",    "strategic-playbook"),
    ("🏆", "Top 10 Ads",            "top-10-ads"),
    ("✨", "New This Week",          "new-this-week"),
    ("🗂", "Ad Swipe File",          "ad-swipe-file"),
    ("📅", "Activity Timeline",     "activity-timeline"),
    ("🎭", "Emotional Tone",         "emotional-tone"),
    ("⚡", "New vs Stopped",        "new-vs-stopped"),
    ("✅", "Action Tracker",         "action-tracker"),
    ("📈", "Weekly Delta",           "weekly-delta"),
    ("📄", "Export & Email",        "export-email"),
]
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">🎙 <span>Listn</span> Intel</div>',
        unsafe_allow_html=True,
    )
    nav_html = '<div class="sidebar-nav">'
    for icon, label, anchor in NAV:
        nav_html += f'<a href="#{anchor}">{icon} {label}</a>'
    nav_html += "</div>"
    nav_html += f'<div class="sidebar-meta">Meta Ad Library · {fetched_date}<br>{total_ads} ads · {n_competitors} competitors</div>'
    st.markdown(nav_html, unsafe_allow_html=True)

# ── PDF / Email ───────────────────────────────────────────────────────────────
def generate_pdf():
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Listn Competitor Intelligence", styles["Title"]))
    story.append(Paragraph(f"Week of {fetched_date}", styles["Normal"]))
    story.append(Spacer(1, 0.2*inch))
    kpi = [["Metric", "Value"],
           ["Total Ads", str(total_ads)],
           ["Active Ads", str(len(active_df))],
           ["New This Week (14d)", str(len(new14_df))],
           ["Competitors Tracked", str(n_competitors)]]
    t = Table(kpi, colWidths=[3*inch, 2*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4C1D95")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,1), (-1,-1), colors.HexColor("#F3F0FF")),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Strategic Playbook", styles["Heading2"]))
    for item in PLAYBOOK:
        story.append(Paragraph(f"[{item['priority']}] {item['title']}", styles["Heading3"]))
        story.append(Paragraph(f"Action: {item['action']}", styles["Normal"]))
        story.append(Paragraph(f"Why: {item['why']}", styles["Normal"]))
        story.append(Spacer(1, 0.08*inch))
    doc.build(story)
    return buf.getvalue()

def send_email(pdf_bytes, date_str):
    sender   = os.getenv("EMAIL_SENDER", "")
    password = os.getenv("EMAIL_PASSWORD", "")
    if not sender or not password:
        return False, "EMAIL_SENDER or EMAIL_PASSWORD not set in .env"
    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = "digvijayudawat064@gmail.com"
    msg["Subject"] = f"Listn Competitor Intel — Week of {date_str}"
    msg.attach(MIMEText("Weekly report attached. Generated from Meta Ad Library data.", "plain"))
    part = MIMEBase("application", "octet-stream")
    part.set_payload(pdf_bytes)
    encoders.encode_base64(part)
    fname = f"listn_weekly_report_{date_str}.pdf"
    part.add_header("Content-Disposition", f'attachment; filename="{fname}"')
    msg.attach(part)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(sender, password)
            s.sendmail(sender, "digvijayudawat064@gmail.com", msg.as_string())
        return True, fname
    except Exception as e:
        return False, str(e)

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="export-email"></a>', unsafe_allow_html=True)
col_h, col_btn = st.columns([5, 1])
with col_h:
    st.markdown(
        '<div class="header-wrap"><div class="header-content">'
        '<div class="header-title">🎙 Listn Competitor Intelligence</div>'
        f'<div class="header-sub">Meta Ad Library · Fetched {fetched_date} · {total_ads} total ads scraped</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
with col_btn:
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("📄 Export & Email", use_container_width=True):
        with st.spinner("Generating PDF..."):
            try:
                pdf_bytes = generate_pdf()
                date_str  = FETCHED_DATE.strftime("%Y-%m-%d")
                (BASE / f"listn_weekly_report_{date_str}.pdf").write_bytes(pdf_bytes)
                ok, msg = send_email(pdf_bytes, date_str)
                st.success(f"Sent: {msg}") if ok else st.warning(f"PDF saved. Email failed: {msg}")
            except Exception as e:
                st.error(f"Export failed: {e}")

# ── KPI Strip ─────────────────────────────────────────────────────────────────
cards_html = '<div class="kpi-grid">'
cards_html += kpi_html("📊", "Total Ads Scraped",    total_ads)
cards_html += kpi_html("🟢", "Active Ads",            len(active_df))
cards_html += kpi_html("✨", "New This Week (14d)",   len(new14_df))
cards_html += kpi_html("🏢", "Competitors Tracked",   n_competitors)
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)
st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION A — Total Ads per Competitor
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="total-ads-chart"></a>', unsafe_allow_html=True)
st.markdown("## 📊 Total Ads Scraped per Competitor")

total_counts = (
    df.groupby("competitor").size()
    .reset_index(name="total")
    .sort_values("total", ascending=True)
)
bar_colors = [COMP_COLOR.get(c, "#94A3B8") for c in total_counts["competitor"]]

fig_bar = go.Figure(go.Bar(
    x=total_counts["total"],
    y=total_counts["competitor"],
    orientation="h",
    marker=dict(
        color=bar_colors,
        opacity=0.85,
        line=dict(color="rgba(255,255,255,0.1)", width=1),
    ),
    text=total_counts["total"],
    textposition="outside",
    textfont=dict(color="#E2D9F3", size=13, family="system-ui"),
    hovertemplate="<b>%{y}</b><br>Total Ads: %{x}<extra></extra>",
))
fig_bar.update_layout(**TRANSPARENT, height=280, showlegend=False)
fig_bar.update_xaxes(showgrid=True)
fig_bar.update_yaxes(showgrid=False, tickfont=dict(size=13))
st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION B — Listn Strategic Playbook
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="strategic-playbook"></a>', unsafe_allow_html=True)
st.markdown("## 🎯 Listn Strategic Playbook")

remento_total = int(df[df["competitor"] == "Remento"].shape[0])
st.markdown(
    f'<div class="ws-box"><div class="ws-label">📊 Competitive Whitespace Summary</div>'
    f'<div class="ws-row"><span class="ws-hl">Remento:</span> {remento_total} total ads — '
    f'100% targeting the adult child gifter, zero speaking to elders directly</div>'
    f'<div class="ws-row"><span class="ws-hl">Listn opportunity:</span> elder-as-hero reframe '
    f'+ voice-as-product + caregiver segment = <span class="ws-hl">3 uncontested lanes</span></div>'
    f'</div>',
    unsafe_allow_html=True,
)

col_l, col_r = st.columns(2)
for i, item in enumerate(PLAYBOOK):
    cls = "glass-high" if item["priority"] == "HIGH" else "glass-medium"
    pill_cls = "priority-pill-high" if item["priority"] == "HIGH" else "priority-pill-medium"
    icon = "⚡" if item["priority"] == "HIGH" else "◆"
    html = (
        f'<div class="{cls}">'
        f'<div class="{pill_cls}">{icon} {item["priority"]} PRIORITY</div>'
        f'<div class="card-title">{item["title"]}</div>'
        f'<div class="card-action">{item["action"]}</div>'
        f'<div><span class="card-why-label">Why: </span>'
        f'<span class="card-why">{item["why"]}</span></div>'
        f'</div>'
    )
    (col_l if i % 2 == 0 else col_r).markdown(html, unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION C — Top 10 Longest-Running Ads
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="top-10-ads"></a>', unsafe_allow_html=True)
st.markdown("## 🏆 Top 10 Longest-Running Ads")

top10 = df.nlargest(10, "days_running").reset_index(drop=True)
for i, row in top10.iterrows():
    alt = "ad-card-alt" if i % 2 else ""
    dot_cls = "dot-green" if row["is_active"] else "dot-red"
    status_txt = "Active" if row["is_active"] else "Stopped"
    badge = comp_badge(row["competitor"])
    st.markdown(
        f'<div class="ad-card {alt}">'
        f'<div class="meta-row">'
        f'{badge}'
        f'<span class="dot {dot_cls}"></span>'
        f'<span style="color:#9CA3AF;font-size:0.75rem;">{status_txt}</span>'
        f'<span class="days-num">{row["days_running"]}</span>'
        f'<span class="days-unit">days</span>'
        f'</div>'
        f'<div class="copy-text">{row["snippet"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION D — New This Week (14d)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="new-this-week"></a>', unsafe_allow_html=True)
st.markdown("## ✨ New This Week  *(ads started within 14 days)*")

if new14_df.empty:
    st.info("No ads started in the last 14 days.")
else:
    for competitor, group in new14_df.sort_values("days_since_start").groupby("competitor", sort=False):
        st.markdown(f"### {competitor}")
        for _, row in group.iterrows():
            age  = f"{row['days_since_start']}d old"
            stat = "🟢 Active" if row["is_active"] else "🔴 Stopped"
            st.markdown(
                f'<div class="ad-card">'
                f'<div class="meta-row">'
                f'{comp_badge(competitor)}'
                f'<span style="background:rgba(167,139,250,0.15);color:#A78BFA;border-radius:20px;padding:1px 8px;font-size:0.68rem;font-weight:700;">NEW · {age}</span>'
                f'<span style="color:#9CA3AF;font-size:0.75rem;">{stat}</span>'
                f'</div>'
                f'<div class="copy-text">{row["snippet"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Ad Copy Swipe File
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="ad-swipe-file"></a>', unsafe_allow_html=True)
st.markdown("## 🗂 Ad Copy Swipe File")

swipe = df[["competitor", "ad_copy", "tone", "cta_label", "days_running", "is_active"]].copy()
swipe["Ad Copy"]     = df["ad_copy"].fillna("").str[:140] + "..."
swipe["Status"]      = swipe["is_active"].map({True: "🟢 Active", False: "🔴 Stopped"})
swipe = swipe.rename(columns={"competitor": "Competitor", "tone": "Tone", "cta_label": "CTA", "days_running": "Days"})

sf1, sf2, sf3 = st.columns([2, 1, 1])
with sf1:
    search = st.text_input("🔍  Search ad copy", placeholder="Type any keyword...")
with sf2:
    comp_filter = st.selectbox("Competitor", ["All"] + sorted(swipe["Competitor"].unique()))
with sf3:
    tone_filter = st.selectbox("Tone", ["All"] + list(TONE_KEYWORDS.keys()))

mask = pd.Series([True] * len(swipe), index=swipe.index)
if search:
    mask &= df["ad_copy"].fillna("").str.lower().str.contains(search.lower())
if comp_filter != "All":
    mask &= swipe["Competitor"] == comp_filter
if tone_filter != "All":
    mask &= swipe["Tone"] == tone_filter

st.dataframe(
    swipe.loc[mask, ["Competitor", "Ad Copy", "Tone", "CTA", "Days", "Status"]].reset_index(drop=True),
    use_container_width=True,
    height=380,
    column_config={
        "Competitor": st.column_config.TextColumn(width="small"),
        "Ad Copy":    st.column_config.TextColumn(width="large"),
        "Tone":       st.column_config.TextColumn(width="small"),
        "CTA":        st.column_config.TextColumn(width="small"),
        "Days":       st.column_config.NumberColumn(width="small", format="%d"),
        "Status":     st.column_config.TextColumn(width="small"),
    },
)
st.caption(f"Showing {int(mask.sum())} of {len(swipe)} ads")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Activity Timeline
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="activity-timeline"></a>', unsafe_allow_html=True)
st.markdown("## 📅 Competitor Activity Timeline")
st.caption("Every individual ad as a horizontal bar. Hover for ad copy snippet and days running.")

gantt = df[df["start_date"].notna()].copy()
gantt["end_date"]  = gantt["stop_date"].fillna(FETCHED_DATE)
gantt["bar_color"] = gantt["competitor"].map(COMP_COLOR).fillna("#94A3B8")

fig_gantt = px.timeline(
    gantt,
    x_start="start_date",
    x_end="end_date",
    y="competitor",
    color="competitor",
    color_discrete_map={c: COMP_COLOR.get(c, "#94A3B8") for c in gantt["competitor"].unique()},
    hover_data={"hover_snippet": True, "days_running": True, "is_active": True},
    labels={"hover_snippet": "Ad Copy", "days_running": "Days", "is_active": "Active"},
)
fig_gantt.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#E2D9F3",
    margin=dict(l=0, r=20, t=20, b=10),
    height=max(380, len(gantt) * 5),
    showlegend=True,
    legend=dict(bgcolor="rgba(45,17,80,0.7)", bordercolor="rgba(167,139,250,0.3)",
                font=dict(color="#E2D9F3"), title=dict(text="Competitor")),
)
fig_gantt.update_xaxes(gridcolor="rgba(167,139,250,0.12)", color="#A78BFA", showline=False)
fig_gantt.update_yaxes(gridcolor="rgba(167,139,250,0.12)", color="#E2D9F3", showline=False, autorange="reversed")
st.plotly_chart(fig_gantt, use_container_width=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Emotional Tone Breakdown
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="emotional-tone"></a>', unsafe_allow_html=True)
st.markdown("## 🎭 Emotional Tone Breakdown")

tone_rows = []
for comp, copy_text in zip(df["competitor"], df["ad_copy"].fillna("")):
    for t in all_tones(copy_text):
        tone_rows.append({"competitor": comp, "tone": t})
tone_df     = pd.DataFrame(tone_rows)
tone_counts = tone_df.groupby(["competitor", "tone"]).size().reset_index(name="count")
tone_totals = tone_counts.groupby("competitor")["count"].transform("sum")
tone_counts["pct"]   = (tone_counts["count"] / tone_totals * 100).round(1)
tone_counts["label"] = tone_counts["pct"].astype(str) + "%"

fig_tone = px.bar(
    tone_counts,
    x="competitor",
    y="pct",
    color="tone",
    barmode="group",
    text="label",
    color_discrete_map=TONE_COLORS,
    labels={"pct": "% share", "competitor": "", "tone": "Tone"},
    category_orders={"tone": list(TONE_KEYWORDS.keys())},
)
fig_tone.update_traces(textposition="outside", textfont=dict(size=10, color="#E2D9F3"))
fig_tone.update_layout(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font_color="#E2D9F3",
    margin=dict(l=0, r=20, t=20, b=10),
    height=420,
    legend=dict(bgcolor="rgba(45,17,80,0.7)", bordercolor="rgba(167,139,250,0.3)",
                font=dict(color="#E2D9F3"), title=dict(text="Tone")),
)
fig_tone.update_xaxes(gridcolor="rgba(167,139,250,0.12)", color="#A78BFA", showline=False, zeroline=False)
fig_tone.update_yaxes(gridcolor="rgba(167,139,250,0.12)", color="#E2D9F3", showline=False, zeroline=False)
st.plotly_chart(fig_tone, use_container_width=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — New vs Stopped This Week (7d)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="new-vs-stopped"></a>', unsafe_allow_html=True)
st.markdown("## ⚡ New vs Stopped This Week  *(last 7 days)*")

col_new, col_stopped = st.columns(2)
with col_new:
    st.markdown("### 🟢 Started This Week")
    if new7_df.empty:
        st.info("No ads started in the last 7 days.")
    else:
        for _, row in new7_df.sort_values("days_since_start").iterrows():
            st.markdown(
                f'<div class="card-new">'
                f'<div class="meta-row">{comp_badge(row["competitor"])}'
                f'<span style="color:#34D399;font-size:0.75rem;">{row["days_since_start"]}d old</span></div>'
                f'<div class="copy-text">{row["snippet"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

with col_stopped:
    st.markdown("### 🔴 Stopped This Week")
    if stopped7_df.empty:
        st.info("No ads stopped in the last 7 days.")
    else:
        for _, row in stopped7_df.sort_values("stop_date", ascending=False).iterrows():
            st.markdown(
                f'<div class="card-stopped">'
                f'<div class="meta-row">{comp_badge(row["competitor"])}'
                f'<span style="color:#F87171;font-size:0.75rem;">ran {row["days_running"]}d</span></div>'
                f'<div class="copy-text">{row["snippet"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Action Tracker
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="action-tracker"></a>', unsafe_allow_html=True)
st.markdown("## ✅ Listn Action Tracker")

st.markdown(
    '<div class="status-legend">'
    '<span class="status-dot s-grey">⬤ Not Started</span>'
    '<span class="status-dot s-yellow">⬤ In Progress</span>'
    '<span class="status-dot s-blue">⬤ Testing</span>'
    '<span class="status-dot s-green">⬤ Done</span>'
    '</div>',
    unsafe_allow_html=True,
)

tracker_path = BASE / "action_tracker.json"
default_tracker = [
    {"Recommendation": item["title"], "Priority": item["priority"],
     "Status": "Not Started", "Notes": "", "Result": ""}
    for item in PLAYBOOK
]
if tracker_path.exists():
    try:
        saved = json.loads(tracker_path.read_text())
        tracker_rows = saved if isinstance(saved, list) else default_tracker
    except Exception:
        tracker_rows = default_tracker
else:
    tracker_rows = default_tracker

edited = st.data_editor(
    pd.DataFrame(tracker_rows),
    column_config={
        "Recommendation": st.column_config.TextColumn(width="large", disabled=True),
        "Priority":       st.column_config.TextColumn(width="small", disabled=True),
        "Status":         st.column_config.SelectboxColumn(
            options=["Not Started", "In Progress", "Done", "Testing"], width="medium",
        ),
        "Notes":  st.column_config.TextColumn(width="large"),
        "Result": st.column_config.TextColumn(width="large"),
    },
    use_container_width=True,
    hide_index=True,
    num_rows="fixed",
)
if st.button("💾 Save Tracker", type="primary"):
    tracker_path.write_text(json.dumps(edited.to_dict("records"), indent=2))
    st.success(f"Saved to {tracker_path.name}")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Weekly Delta Report
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="weekly-delta"></a>', unsafe_allow_html=True)
st.markdown("## 📈 Weekly Delta Report")

prev_path = BASE / "ads_scraped_previous_week.json"
if not prev_path.exists():
    st.markdown(
        '<div class="delta-box"><p>📊 <strong>First run</strong> — delta report will appear after the second weekly scrape. '
        "Place last week's file as <strong>ads_scraped_previous_week.json</strong> in this folder to enable comparison.</p></div>",
        unsafe_allow_html=True,
    )
else:
    with open(prev_path) as f:
        prev_raw = json.load(f)
    prev_rows = [a for ads in prev_raw["competitors"].values() for a in ads]
    prev_df   = pd.DataFrame(prev_rows)
    prev_ids  = set(prev_df["ad_id"].astype(str))
    curr_ids  = set(df["ad_id"].astype(str))
    new_ads   = curr_ids - prev_ids
    prev_active = set(prev_df[prev_df.get("stop_date", pd.Series()).isna()]["ad_id"].astype(str)) if "stop_date" in prev_df else set()
    now_stopped = prev_active & set(df[~df["is_active"]]["ad_id"].astype(str))
    biggest = (df.groupby("competitor").size() - prev_df.groupby("competitor").size()).dropna().sort_values(key=abs, ascending=False)
    top_mover = biggest.index[0] if len(biggest) else "N/A"
    top_delta  = int(biggest.iloc[0]) if len(biggest) else 0
    direction  = "added" if top_delta > 0 else "removed"
    summary = (
        f"Since last week, **{len(new_ads)} new ads** appeared across all competitors "
        f"and **{len(now_stopped)} ads stopped running**. "
        f"**{top_mover}** saw the biggest change, {direction} {abs(top_delta)} ads."
    )
    st.markdown(f'<div class="delta-box"><p>📊 {summary}</p></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:rgba(167,139,250,0.3);font-size:0.75rem;'>"
    "Listn Competitor Intelligence · Meta Ad Library · Generated from scraped data</p>",
>>>>>>> b64a844 (Rename main file to streamlit_app.py)
    unsafe_allow_html=True,
)
