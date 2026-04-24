"""
Listn SEO Intelligence Dashboard — Premium Edition
Run: streamlit run SEO_Intel/seo_dashboard.py --server.port 8502
"""

import glob
import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Listn SEO Intelligence",
    page_icon="🔍",
    layout="wide",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
html { scroll-behavior: smooth; }

* { font-family: system-ui, -apple-system, sans-serif; box-sizing: border-box; }

.stApp { background-color: #0D0B1E; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }

/* Hide default Streamlit header elements */
[data-testid="stHeader"] { background: transparent; }

/* Global text */
h2, h3, h4, h5, h6 { color: #A78BFA !important; }
p, li, td, th, label, .stMarkdown { color: #C4B5FD !important; }
hr { border-color: rgba(167,139,250,0.2); margin: 2rem 0; }
.stCaption p { color: #6B7280 !important; font-size: 0.82rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A0818 0%, #0D0B1E 100%);
    border-right: 1px solid rgba(167,139,250,0.12);
}
.sidebar-logo {
    font-size: 1.15rem; font-weight: 800; color: #A78BFA;
    letter-spacing: 0.04em; padding: 0.25rem 0 1rem;
    border-bottom: 1px solid rgba(167,139,250,0.15);
    margin-bottom: 1rem;
}
.sidebar-section {
    font-size: 0.68rem; font-weight: 700; color: #4C1D95;
    text-transform: uppercase; letter-spacing: 0.1em;
    margin: 1rem 0 0.4rem; padding-top: 0.75rem;
    border-top: 1px solid rgba(167,139,250,0.08);
}
.sidebar-nav a {
    color: #9CA3AF !important; text-decoration: none;
    display: block; padding: 5px 8px; border-radius: 6px;
    font-size: 0.84rem; transition: all 0.15s ease; margin-bottom: 1px;
}
.sidebar-nav a:hover {
    color: #A78BFA !important; background: rgba(167,139,250,0.08);
    padding-left: 12px;
}
.sidebar-meta {
    color: #4C1D95 !important; font-size: 0.72rem;
    border-top: 1px solid rgba(167,139,250,0.1);
    padding-top: 0.75rem; margin-top: 1rem;
}

/* ── Header ── */
.dash-title {
    font-size: 2.5rem; font-weight: 900; letter-spacing: -0.02em;
    background: linear-gradient(135deg, #A78BFA 0%, #E2D9F3 60%, #FFFFFF 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
    text-shadow: none;
    filter: drop-shadow(0 0 30px rgba(167,139,250,0.35));
    line-height: 1.1; margin-bottom: 0.4rem;
}
.dash-sub {
    color: #7C6FA0 !important; font-size: 0.9rem; margin-bottom: 0;
}

/* ── KPI Cards ── */
.kpi-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 1rem; margin: 1.5rem 0 2rem;
}
.kpi-card {
    background: rgba(167,139,250,0.07);
    border: 1px solid rgba(167,139,250,0.18);
    border-radius: 16px;
    padding: 1.5rem 1.25rem;
    display: flex; flex-direction: column;
    justify-content: center; align-items: center;
    min-height: 130px; text-align: center;
    transition: all 0.2s ease;
    position: relative; overflow: hidden;
}
.kpi-card::before {
    content: ''; position: absolute; inset: 0;
    background: radial-gradient(ellipse at top, rgba(167,139,250,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.kpi-card:hover {
    border-color: rgba(167,139,250,0.35);
    box-shadow: 0 0 24px rgba(167,139,250,0.15), 0 4px 16px rgba(0,0,0,0.3);
    transform: translateY(-2px);
}
.kpi-value {
    color: #A78BFA; font-size: 2rem; font-weight: 800;
    line-height: 1.1; margin-bottom: 0.45rem;
}
.kpi-label {
    color: #6B7280; font-size: 0.77rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.08em;
}

/* ── Section headings ── */
.section-heading {
    font-size: 1.4rem; font-weight: 700; color: #A78BFA !important;
    margin: 0 0 0.25rem; letter-spacing: -0.01em;
}
.section-sub {
    color: #6B7280 !important; font-size: 0.83rem; margin-bottom: 1.25rem;
}

/* ── Quick Wins Table ── */
.qw-wrap {
    border: 1px solid rgba(167,139,250,0.18);
    border-radius: 14px; overflow: hidden; margin-top: 0.75rem;
}
.qw-header {
    display: grid; grid-template-columns: 2.2fr 1fr 0.55fr 1.3fr 2fr;
    background: rgba(124,58,237,0.35);
    padding: 0.6rem 1rem;
    font-size: 0.72rem; font-weight: 700; color: #DDD6FE;
    text-transform: uppercase; letter-spacing: 0.08em; gap: 0.5rem;
}
.qw-row {
    display: grid; grid-template-columns: 2.2fr 1fr 0.55fr 1.3fr 2fr;
    padding: 0.65rem 1rem; gap: 0.5rem;
    align-items: center; font-size: 0.86rem;
    border-top: 1px solid rgba(167,139,250,0.08);
    transition: background 0.15s ease;
}
.qw-row:nth-child(odd)  { background: rgba(167,139,250,0.04); }
.qw-row:nth-child(even) { background: transparent; }
.qw-row:hover           { background: rgba(167,139,250,0.1); }
.kw-mono {
    font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.82rem;
    color: #E2D9F3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.vol-bold { color: #A78BFA; font-weight: 700; }
.kd-pill {
    display: inline-block; border-radius: 20px; padding: 2px 9px;
    font-size: 0.75rem; font-weight: 700; min-width: 32px; text-align: center;
}
.kd-green  { background: rgba(16,185,129,0.2);  color: #10B981; border: 1px solid rgba(16,185,129,0.3);  }
.kd-yellow { background: rgba(245,158,11,0.2);  color: #F59E0B; border: 1px solid rgba(245,158,11,0.3);  }
.kd-orange { background: rgba(249,115,22,0.2);  color: #F97316; border: 1px solid rgba(249,115,22,0.3);  }
.comp-lbl { color: #9CA3AF; font-size: 0.81rem; }
.edge-lbl { color: #7C6FA0; font-size: 0.81rem; line-height: 1.4; }

/* ── Blog cards ── */
.blog-card {
    background: rgba(167,139,250,0.06);
    border: 1px solid rgba(167,139,250,0.18);
    border-left: 4px solid #A78BFA;
    border-radius: 14px; padding: 1.25rem 1.4rem 1.1rem;
    margin-bottom: 1rem; position: relative; overflow: hidden;
    transition: all 0.2s ease;
}
.blog-card:hover {
    transform: translateY(-3px);
    border-color: rgba(167,139,250,0.45);
    box-shadow: 0 8px 24px rgba(124,58,237,0.2);
}
.blog-watermark {
    position: absolute; right: 0.8rem; top: -0.2rem;
    font-size: 5rem; font-weight: 900; line-height: 1;
    color: rgba(167,139,250,0.06); pointer-events: none; user-select: none;
    font-variant-numeric: tabular-nums;
}
.blog-num {
    font-size: 0.68rem; font-weight: 700; color: #7C3AED;
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.35rem;
}
.blog-title {
    color: #F3F0FF; font-size: 0.97rem; font-weight: 700;
    line-height: 1.4; margin-bottom: 0.6rem;
}
.kw-chip {
    display: inline-block; background: rgba(124,58,237,0.25);
    color: #C4B5FD; border: 1px solid rgba(167,139,250,0.25);
    border-radius: 20px; padding: 2px 9px;
    font-size: 0.73rem; margin: 2px 3px 2px 0; font-family: monospace;
}
.blog-why {
    color: #6B7280; font-size: 0.83rem; line-height: 1.55;
    font-style: italic; margin-top: 0.5rem;
}
.blog-why strong { color: #9CA3AF; font-style: normal; }

/* ── Gap cards ── */
.gap-card {
    background: rgba(167,139,250,0.06);
    border: 1px solid rgba(167,139,250,0.15);
    border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: 0.75rem;
    transition: all 0.2s ease;
}
.gap-card:hover {
    border-color: rgba(167,139,250,0.3);
    background: rgba(167,139,250,0.1);
}
.gap-icon  { font-size: 1.4rem; margin-bottom: 0.35rem; display: block; }
.gap-title { color: #A78BFA; font-weight: 700; font-size: 0.92rem; margin-bottom: 0.3rem; }
.gap-body  { color: #7C6FA0; font-size: 0.83rem; line-height: 1.55; }

/* ── Note box ── */
.note-box {
    background: rgba(245,158,11,0.07);
    border: 1px solid rgba(245,158,11,0.25);
    border-left: 4px solid #F59E0B;
    border-radius: 12px; padding: 0.85rem 1.25rem; margin-bottom: 1.25rem;
}
.note-label { color: #FCD34D; font-weight: 700; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em; }
.note-text  { color: #D1C4A0; font-size: 0.87rem; margin-left: 0.5rem; }

/* ── Avoid cards ── */
.avoid-card {
    background: rgba(239,68,68,0.06);
    border: 1px solid rgba(239,68,68,0.18);
    border-radius: 12px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem;
    transition: border-color 0.15s ease;
}
.avoid-card:hover { border-color: rgba(239,68,68,0.35); }
.avoid-cluster  { color: #F87171; font-weight: 700; font-size: 0.9rem; margin-bottom: 0.3rem; }
.avoid-keywords { color: #6B7280; font-size: 0.8rem; font-family: monospace; margin: 0.2rem 0; }
.avoid-traffic  { color: #FCD34D; font-size: 0.8rem; margin-bottom: 0.3rem; }
.avoid-why      { color: #9CA3AF; font-size: 0.82rem; line-height: 1.5; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
PURPLE_SCALE = ["#3B0764", "#5B21B6", "#7C3AED", "#8B5CF6", "#A78BFA", "#C4B5FD", "#EDE9FE"]
COMP_COLORS = {
    "Remento":    "#A78BFA",
    "Meminto":    "#34D399",
    "StoryWorth": "#F87171",
    "Storykeeper": "#FCD34D",
}
CHART_BG = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#C4B5FD", family="system-ui, -apple-system, sans-serif"),
    margin=dict(l=10, r=40, t=40, b=10),
)

# ── Keyword relevance filter (blocklist + allowlist) ──────────────────────────
_BLOCKLIST_PHRASES = [
    "boyfriend", "girlfriend", "mother's day date", "mothers day date",
    "when is", "scan iphone", "scan on iphone", "romantic", "dating",
    "mom day", "mother day", "mothers day", "mother's day",
]
_ALLOWLIST_WORDS = [
    "memory", "memories", "story", "stories", "grandparent", "grandparents",
    "parent", "parents", "family", "memoir", "voice", "record", "preserve",
    "legacy", "gift", "gifts", "dad", "father", "mom", "mother", "elder",
    "aging", "remember", "heirloom", "keepsake", "capture", "biography",
    "life", "oral", "history", "ancestor", "generation",
]
_ALLOW_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _ALLOWLIST_WORDS) + r")\b",
    re.IGNORECASE,
)

def is_relevant(keyword: str) -> bool:
    kw_lower = keyword.lower()
    if any(phrase in kw_lower for phrase in _BLOCKLIST_PHRASES):
        return False
    return bool(_ALLOW_RE.search(kw_lower))

# ── Hardcoded insights ─────────────────────────────────────────────────────────
BLOG_POSTS = [
    {
        "num": "01",
        "title": "The Gift That Won't Get Donated: Why Voice Memories Beat Any Physical Present for Grandparents",
        "keywords": [
            ("grandparent gift ideas", "14,800/mo", 0),
            ("grandparents gift idea", "14,800/mo", 0),
            ("christmas gifts for grandparents", "6,600/mo", 0),
        ],
        "why": "Meminto ranks 50s–90s for this cluster with a generic list. KD is zero. "
               "One well-optimized post → page one. Add a 'give Listn as a gift' CTA → direct acquisition page.",
    },
    {
        "num": "02",
        "title": "How to Record Your Parent's Life Stories Before It's Too Late (A Guide for Adult Children)",
        "keywords": [
            ("parent memory book", "880/mo", 8),
            ("memory keeper", "880/mo", 2),
            ("memories books", "8,100/mo", 0),
        ],
        "why": "Targets Listn's highest-urgency persona: adult children who feel the weight of time. "
               "No competitor has written this piece. Lead with loss aversion, then frame Listn as frictionless for older adults.",
    },
    {
        "num": "03",
        "title": "The Best Christmas Present for Dad That Isn't Another Gadget He'll Never Use",
        "keywords": [
            ("christmas present for dad", "33,100/mo", 6),
            ("christmas present for father", "33,100/mo", 2),
            ("father birthday gifts", "33,100/mo", 9),
        ],
        "why": "StoryWorth ranks #88–102 for these despite being the most obvious brand to own them. "
               "KD 2–9, converts at peak holiday season. Publish by late October.",
    },
    {
        "num": "04",
        "title": "Voice vs. Text: Why Older Adults Remember More When They Speak Their Stories",
        "keywords": [
            ("autobiographical", "60,500/mo", 21),
            ("memory book", "8,100/mo", 12),
        ],
        "why": "Neither StoryWorth nor Remento covers the neuroscience of spoken vs. written memory — "
               "Listn's core product thesis. Cite oral history research. Earns backlinks from aging and caregiving publications.",
    },
    {
        "num": "05",
        "title": "What to Ask Your Parents Before It's Too Late: 50 Voice-Ready Questions for Recording Family Stories",
        "keywords": [
            ("get to know you questions", "33,100/mo", 9),
            ("memories books", "8,100/mo", 0),
        ],
        "why": "Remento's question content targets romantic relationships — a mismatch with their product. "
               "Listn owns the intergenerational family storytelling questions space. High shareability in caregiving groups.",
    },
]

CONTENT_GAPS = [
    ("🎙", "Voice journaling for older adults",
     "Zero competitor content exists. 'Voice journaling' is emerging search territory — no text-first brand will credibly own it."),
    ("💬", "How to talk to aging parents about preserving memories",
     "SEO-viable and highly shareable. No competitor addresses the conversation — only the product."),
    ("🧠", "Dementia, memory loss, and the urgency of story capture",
     "High-demand, zero competitive content. 'Recording memories before dementia' has real search volume. Listn's most defensible niche."),
    ("💫", "What happens to family stories when someone dies",
     "Grief + legacy intersection. High emotional search intent. Earns organic links from elder care and hospice publications."),
    ("♿", "Voice accessibility for seniors: why audio-first apps work better",
     "Ranks for long-tail accessibility queries. Every competitor assumes text/typing fluency — Listn doesn't."),
    ("📼", "How to digitize oral family history",
     "Adjacent to Remento's iPhone scanning post (2,184 est. traffic), but for audio, not photos. Completely uncontested."),
    ("🌱", "Intergenerational storytelling as a mental health practice",
     "Research-backed angle tying story-sharing to reduced cognitive decline. No competitor covers this from a clinical/wellness angle."),
]

KEYWORDS_TO_AVOID = [
    {
        "cluster": "Romantic relationship questions",
        "keywords": "questions to ask your boyfriend / girlfriend, love questions to ask your gf",
        "traffic": "~10,400/mo combined",
        "why": "Remento's top 3 pages — heavy editorial investment. Completely irrelevant to Listn's audience. Fighting here wastes resources.",
    },
    {
        "cluster": "iPhone photo scanning",
        "keywords": "how to scan on iphone, how to scan iphone",
        "traffic": "~2,184/mo",
        "why": "A tech tutorial with zero conversion overlap with Listn users.",
    },
    {
        "cluster": "Autobiographical memory (definitional)",
        "keywords": "autobiographical, autobiographical memory definition",
        "traffic": "~657/mo",
        "why": "StoryWorth #9, Remento #23 — two established competitors. Attack via the voice angle (Post 4) instead.",
    },
    {
        "cluster": "Mother's Day gift ideas (generic)",
        "keywords": "gift ideas for mom on mother's day, gift suggestions for mother's day",
        "traffic": "~972/mo",
        "why": "Crowded, seasonal, dominated by e-commerce players beyond these four. Not defensible.",
    },
]

_EXACT_EDGES = {
    "grandparent gift ideas":               ("Meminto #99",     "grandparent"),
    "grandparents gift idea":               ("Meminto #46",     "grandparent"),
    "presents grandparents":                ("Meminto #57",     "grandparent"),
    "christmas gifts for grandparents":     ("Meminto #52",     "grandparent"),
    "christmas gifts to give grandparents": ("Meminto #36",     "grandparent"),
    "gift ideas for 50th wedding anniversary": ("Meminto #55",  "gift"),
    "father's day gift":                    ("StoryWorth #38",  "dad"),
    "father birthday gifts":                ("StoryWorth #74",  "dad"),
    "christmas present for father":         ("StoryWorth #89",  "dad"),
    "christmas presents for your dad":      ("StoryWorth #88",  "dad"),
    "christmas present for dad":            ("StoryWorth #100", "dad"),
    "memories books":                       ("Meminto #90",     "memory"),
    "memory keeper":                        ("Storykeeper #31", "memory"),
    "parent memory book":                   ("Storykeeper #6",  "memory"),
    "memory book":                          ("Storykeeper #8",  "memory"),
    "life story":                           ("—",               "memory"),
    "family stories":                       ("—",               "memory"),
    "story keeper":                         ("Storykeeper #5",  "memory"),
    "grandma gift ideas":                   ("Meminto #60+",    "grandparent"),
}

_EDGE_MESSAGES = {
    "grandparent": "Meminto ranks 50s–90s with generic content. KD 0 — one post wins page one.",
    "dad":         "StoryWorth ranks 88–102 despite being the obvious brand. Easily beatable.",
    "memory":      "No competitor targets the voice-memory angle. Uncontested positioning.",
    "gift":        "Gift-intent buyer. Add waitlist CTA for pre-launch conversion.",
    "default":     "Low KD, weak competitor presence. Voice angle differentiates.",
}

def get_edge(keyword: str, fallback_comp: str) -> tuple[str, str]:
    kw_lower = keyword.lower()
    if kw_lower in _EXACT_EDGES:
        comp, edge_type = _EXACT_EDGES[kw_lower]
        return comp, _EDGE_MESSAGES[edge_type]
    # Pattern-based fallback
    if any(w in kw_lower for w in ("grandparent", "grandparents", "grandma", "grandpa")):
        return fallback_comp, _EDGE_MESSAGES["grandparent"]
    if any(w in kw_lower for w in ("dad", "father", "fathers")):
        return fallback_comp, _EDGE_MESSAGES["dad"]
    if any(w in kw_lower for w in ("memory", "memories", "memoir", "story", "stories")):
        return fallback_comp, _EDGE_MESSAGES["memory"]
    if any(w in kw_lower for w in ("gift", "gifts", "present", "presents")):
        return fallback_comp, _EDGE_MESSAGES["gift"]
    return fallback_comp, _EDGE_MESSAGES["default"]

# ── Data loading ───────────────────────────────────────────────────────────────
@st.cache_data
def load_seo_data():
    files = sorted(glob.glob(str(BASE / "seo_raw_*.json")))
    if files:
        path = files[-1]
        label = Path(path).name
    else:
        path = BASE.parent / "sample_data" / "seo_raw_latest.json"
        label = "seo_raw_latest.json"
    with open(path) as f:
        data = json.load(f)
    return data, label


@st.cache_data
def load_analysis():
    files = sorted(glob.glob(str(BASE / "seo_analysis_*.md")))
    if files:
        with open(files[-1]) as f:
            return f.read()
    fallback = BASE.parent / "sample_data" / "seo_analysis.md"
    if fallback.exists():
        with open(fallback) as f:
            return f.read()
    return ""


@st.cache_data
def build_kw_df(data_json: str) -> pd.DataFrame:
    d = json.loads(data_json)
    rows = []
    for comp, v in d["competitors"].items():
        for kw in v["keywords"]:
            rows.append({
                "competitor": comp,
                "keyword":    kw.get("keyword", ""),
                "volume":     int(kw.get("search_volume") or 0),
                "position":   int(kw.get("position") or 0),
                "kd":         int(kw.get("keyword_difficulty") or 0),
                "url":        kw.get("url", ""),
            })
    return pd.DataFrame(rows)


data, raw_filename = load_seo_data()
analysis_md = load_analysis()

if data is None:
    st.error("No seo_raw_*.json found in SEO_Intel/. Run seo_monitor.py first.")
    st.stop()

kw_df = build_kw_df(json.dumps(data))
fetched_date = data.get("fetched_date", "")

# ── Quick wins — filtered ──────────────────────────────────────────────────────
_base_qw = (
    kw_df[(kw_df["kd"] < 30) & (kw_df["volume"] > 500)]
    .drop_duplicates("keyword")
    .copy()
)
quick_wins = _base_qw[_base_qw["keyword"].apply(is_relevant)].sort_values("volume", ascending=False)
if len(quick_wins) < 5:                           # fallback: relax filter, use lowest KD
    quick_wins = _base_qw.sort_values("kd").head(20)

# ── KPIs ───────────────────────────────────────────────────────────────────────
total_kw_tracked = len(kw_df)
avg_kd = round(kw_df["kd"].mean(), 1)
n_content_gaps = len(CONTENT_GAPS)
_best_raw = quick_wins.iloc[0]["keyword"] if not quick_wins.empty else "N/A"
_best = _best_raw[:20] + "…" if len(_best_raw) > 20 else _best_raw

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">🔍 Listn SEO Intel</div>',
        unsafe_allow_html=True,
    )
    sections = [
        ("Metrics",   [("📊 KPI Overview",           "kpi-overview")]),
        ("Keywords",  [
            ("⚡ Quick Wins",             "quick-wins-table"),
            ("🗺 Competitor Map",         "competitor-keyword-map"),
        ]),
        ("Content",   [
            ("📝 Content Roadmap",        "content-roadmap"),
            ("🕳 Content Gaps",           "content-gaps"),
            ("⛔ Keywords to Avoid",      "keywords-to-avoid"),
        ]),
        ("Analysis",  [("📄 Full SEO Report",         "full-seo-analysis")]),
    ]
    nav_html = '<div class="sidebar-nav">'
    for section_label, items in sections:
        nav_html += f'<div class="sidebar-section">{section_label}</div>'
        for label, anchor in items:
            nav_html += f'<a href="#{anchor}">{label}</a>'
    nav_html += "</div>"
    st.markdown(nav_html, unsafe_allow_html=True)
    st.markdown(
        f'<p class="sidebar-meta">Data: {fetched_date}<br>{raw_filename}</p>',
        unsafe_allow_html=True,
    )

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 class="dash-title">Listn SEO Intelligence</h1>'
    f'<p class="dash-sub">DataForSEO · {fetched_date} · '
    f'{total_kw_tracked} keywords tracked across Remento, Meminto, StoryWorth &amp; Storykeeper</p>',
    unsafe_allow_html=True,
)
st.markdown('<a id="kpi-overview"></a>', unsafe_allow_html=True)

# ── KPI Row (custom HTML for equal height) ─────────────────────────────────────
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-value">{total_kw_tracked}</div>
    <div class="kpi-label">Keywords Tracked</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">{avg_kd}</div>
    <div class="kpi-label">Avg Competitor KD</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value" style="font-size:1.2rem;padding: 0 0.25rem;">{_best}</div>
    <div class="kpi-label">Biggest Quick Win</div>
  </div>
  <div class="kpi-card">
    <div class="kpi-value">{n_content_gaps}</div>
    <div class="kpi-label">Uncontested Content Gaps</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Quick Wins Table
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="quick-wins-table"></a>', unsafe_allow_html=True)
st.markdown(
    f'<p class="section-heading">⚡ Quick Wins</p>'
    f'<p class="section-sub">KD &lt; 30 · Volume &gt; 500 · Listn-relevant keywords only'
    f' · {len(quick_wins)} found · sorted by volume</p>',
    unsafe_allow_html=True,
)

def kd_pill(kd: int) -> str:
    if kd <= 10:  return f'<span class="kd-pill kd-green">{kd}</span>'
    if kd <= 20:  return f'<span class="kd-pill kd-yellow">{kd}</span>'
    return              f'<span class="kd-pill kd-orange">{kd}</span>'

rows_html = (
    '<div class="qw-wrap">'
    '<div class="qw-header">'
    '<span>Keyword</span><span>Volume / mo</span><span>KD</span>'
    '<span>Best Competitor</span><span>Listn\'s Edge</span>'
    '</div>'
)
for _, row in quick_wins.head(20).iterrows():
    comp_str, edge_str = get_edge(row["keyword"], row["competitor"])
    rows_html += (
        f'<div class="qw-row">'
        f'<span class="kw-mono">{row["keyword"]}</span>'
        f'<span class="vol-bold">{int(row["volume"]):,}</span>'
        f'<span>{kd_pill(int(row["kd"]))}</span>'
        f'<span class="comp-lbl">{comp_str}</span>'
        f'<span class="edge-lbl">{edge_str}</span>'
        f'</div>'
    )
rows_html += "</div>"
st.markdown(rows_html, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Content Roadmap
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="content-roadmap"></a>', unsafe_allow_html=True)
st.markdown(
    '<p class="section-heading">📝 Content Roadmap</p>'
    '<p class="section-sub">5 posts to write before launch — ordered by launch priority</p>',
    unsafe_allow_html=True,
)

col_a, col_b = st.columns(2)
for i, post in enumerate(BLOG_POSTS):
    chips = "".join(
        f'<span class="kw-chip">{kw} · {vol} · KD {kd}</span>'
        for kw, vol, kd in post["keywords"]
    )
    card = (
        f'<div class="blog-card">'
        f'<div class="blog-watermark">{post["num"]}</div>'
        f'<div class="blog-num">Post {post["num"]}</div>'
        f'<div class="blog-title">{post["title"]}</div>'
        f'<div style="margin-bottom:0.5rem;">{chips}</div>'
        f'<div class="blog-why">{post["why"]}</div>'
        f'</div>'
    )
    (col_a if i % 2 == 0 else col_b).markdown(card, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Competitor Keyword Map
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="competitor-keyword-map"></a>', unsafe_allow_html=True)
st.markdown(
    '<p class="section-heading">🗺 Competitor Keyword Map</p>'
    '<p class="section-sub">Top 10 keywords per competitor — toggle between volume view and position view</p>',
    unsafe_allow_html=True,
)

ctrl_col, chart_col = st.columns([1, 3])
with ctrl_col:
    selected_comp = st.selectbox("Competitor", sorted(kw_df["competitor"].unique()))
    view = st.radio("View", ["Search Volume", "Ranking Position"])

with chart_col:
    top10 = (
        kw_df[kw_df["competitor"] == selected_comp]
        .sort_values("volume", ascending=False)
        .head(10)
        .copy()
    )
    top10["label"] = top10["keyword"].str[:38]

    if view == "Search Volume":
        plot_df = top10.sort_values("volume")
        fig = px.bar(
            plot_df, x="volume", y="label", orientation="h",
            color="kd",
            color_continuous_scale=["#10B981", "#F59E0B", "#EF4444"],
            text=plot_df["volume"].apply(lambda v: f"{v:,.0f}"),
            labels={"volume": "Monthly Searches", "label": "", "kd": "KD"},
            title=f"{selected_comp} · Top 10 by Search Volume",
        )
        fig.update_coloraxes(
            colorbar_title="KD",
            colorbar_tickfont_color="#C4B5FD",
            colorbar_title_font_color="#A78BFA",
        )
    else:
        plot_df = top10[top10["position"] > 0].sort_values("position", ascending=False)
        fig = px.bar(
            plot_df, x="position", y="label", orientation="h",
            color="volume",
            color_continuous_scale=PURPLE_SCALE,
            text=plot_df["position"].astype(int).astype(str),
            labels={"position": "SERP Position (lower = better)", "label": "", "volume": "Volume"},
            title=f"{selected_comp} · Top 10 by Ranking Position",
        )
        fig.update_coloraxes(
            colorbar_title="Volume",
            colorbar_tickfont_color="#C4B5FD",
            colorbar_title_font_color="#A78BFA",
        )

    fig.update_traces(textposition="outside", textfont_color="#E2D9F3")
    fig.update_layout(
        **CHART_BG,
        height=400,
        title_font_color="#A78BFA",
        title_font_size=13,
    )
    fig.update_xaxes(gridcolor="rgba(167,139,250,0.12)", color="#9CA3AF", showgrid=True)
    fig.update_yaxes(gridcolor="rgba(167,139,250,0.08)", color="#C4B5FD", showgrid=False)
    st.plotly_chart(fig, use_container_width=True)

# All-competitor bubble chart
st.markdown(
    '<p style="color:#9CA3AF;font-size:0.83rem;margin-top:0.5rem;">'
    'All competitors — Volume vs. Position · bubble size = keyword difficulty (min 8)</p>',
    unsafe_allow_html=True,
)
bubble_df = kw_df[(kw_df["position"] > 0) & (kw_df["volume"] > 0)].copy()
bubble_df["kd_size"] = bubble_df["kd"].clip(lower=8).astype(float)

fig_b = px.scatter(
    bubble_df,
    x="volume",
    y="position",
    color="competitor",
    size="kd_size",
    hover_name="keyword",
    color_discrete_map=COMP_COLORS,
    log_x=True,
    labels={"volume": "Monthly Search Volume", "position": "SERP Position", "competitor": ""},
)
fig_b.update_layout(
    **CHART_BG,
    height=420,
    legend=dict(
        bgcolor="rgba(13,11,30,0.8)",
        bordercolor="rgba(167,139,250,0.2)",
        font=dict(color="#C4B5FD"),
    ),
)
fig_b.update_xaxes(
    gridcolor="rgba(167,139,250,0.12)", color="#9CA3AF",
    showgrid=True,
)
fig_b.update_yaxes(
    autorange="reversed",
    gridcolor="rgba(167,139,250,0.08)", color="#C4B5FD",
    showgrid=True,
)
st.plotly_chart(fig_b, use_container_width=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Content Gaps
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="content-gaps"></a>', unsafe_allow_html=True)
st.markdown(
    '<p class="section-heading">🕳 Content Gaps</p>'
    '<p class="section-sub">7 uncontested territories — no competitor has meaningful content here</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="note-box">'
    '<span class="note-label">The pattern</span>'
    '<span class="note-text"> Every competitor competes for gift-buyer keywords and '
    'romantic relationship questions. The entire <strong>caregiving, aging, legacy, and oral history</strong> '
    'space is uncontested. That is Listn\'s white space.</span>'
    '</div>',
    unsafe_allow_html=True,
)

col_g1, col_g2 = st.columns(2)
for i, (icon, title, body) in enumerate(CONTENT_GAPS):
    card = (
        f'<div class="gap-card">'
        f'<span class="gap-icon">{icon}</span>'
        f'<div class="gap-title">{title}</div>'
        f'<div class="gap-body">{body}</div>'
        f'</div>'
    )
    (col_g1 if i % 2 == 0 else col_g2).markdown(card, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Keywords to Avoid
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="keywords-to-avoid"></a>', unsafe_allow_html=True)
st.markdown(
    '<p class="section-heading">⛔ Keywords to Avoid</p>'
    '<p class="section-sub">Remento\'s irrelevant traffic clusters — do not replicate this strategy</p>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="note-box">'
    '<span class="note-label">Bottom line</span>'
    '<span class="note-text"> Remento\'s traffic wins are almost entirely from content unrelated to '
    'their product. Every Listn piece should connect to voice memory, aging adults, or family legacy.</span>'
    '</div>',
    unsafe_allow_html=True,
)

for item in KEYWORDS_TO_AVOID:
    st.markdown(
        f'<div class="avoid-card">'
        f'<div class="avoid-cluster">⚠️ {item["cluster"]}</div>'
        f'<div class="avoid-keywords">{item["keywords"]}</div>'
        f'<div class="avoid-traffic">Est. traffic: {item["traffic"]}</div>'
        f'<div class="avoid-why">{item["why"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Full SEO Analysis Report
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<a id="full-seo-analysis"></a>', unsafe_allow_html=True)
st.markdown(
    '<p class="section-heading">📄 Full SEO Analysis Report</p>'
    '<p class="section-sub">Claude-generated strategic analysis — generated from raw DataForSEO data</p>',
    unsafe_allow_html=True,
)
if analysis_md:
    st.markdown(analysis_md)
else:
    st.info("No seo_analysis_*.md found. Run seo_analyze.py to generate it.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    "<p style='text-align:center;color:#2D1150;font-size:0.78rem;'>"
    "Listn SEO Intelligence · DataForSEO · claude-sonnet-4-6</p>",
    unsafe_allow_html=True,
)
