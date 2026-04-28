"""
Meta Intel — competitive ad intelligence from the Meta Ad Library.

KEEP: 4 stat cards, total ads bar chart, strategic playbook, top 10 longest,
new-this-week, ad copy swipe file, emotional tone breakdown.

REMOVE: Activity timeline (Gantt), Weekly Delta, Export button, Action Tracker.

ADD: Heritage Whisper tracking-gap insight card, "Where nobody is playing"
table after the tone chart.

Competitor scrape list (for scrapers/scrape_ads.py — managed there, not here):
  Remento, Meminto, StoryWorth, Storykeeper, Keepsake,
  Heritage Whisper, StoriedLife AI, LifeEcho, Storii
  (Tell me, HereAfter AI, No Story Lost, Tell Mel — DO NOT add Tell Mel,
   it is phone-based and runs no Meta ads.)
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lib.theme import inject_global_css, COLORS, comp_color, PLOTLY_LAYOUT
from lib.data_freshness import show_freshness_banner
from lib.synthesis import TONE_KEYWORDS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Meta Intel · Listn", page_icon="🎯", layout="wide")
inject_global_css()
show_freshness_banner()

# ── Constants ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "ads_scraped_latest.json"

TONE_COLORS = {
    "nostalgia":     "#FFB4A2",            # soft salmon — sentimental warmth, no purple
    "urgency":       COLORS["urgent"],
    "gifting":       COLORS["evergreen"],
    "fear of loss":  COLORS["soon"],
    "pride":         COLORS["accent"],
    "transactional": "#22D3EE",            # cyan — distinct from accent
}


# ── Tone helpers ──────────────────────────────────────────────────────────────
def tag_tone(text):
    """Primary tone (first match)."""
    t = str(text or "").lower()
    for tone, words in TONE_KEYWORDS.items():
        if any(w in t for w in words):
            return tone
    return "nostalgia"


def all_tones(text):
    if not text or (isinstance(text, float) and pd.isna(text)):
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


def comp_badge(name: str) -> str:
    color = comp_color(name)
    return (
        f'<span style="display:inline-block;border-radius:999px;padding:2px 10px;'
        f'font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;'
        f'background:{color}22;color:{color};border:1px solid {color}55;">{name}</span>'
    )


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data
def load_ads():
    if not DATA_FILE.exists():
        return pd.DataFrame(), "", 0, 0
    with open(DATA_FILE) as f:
        raw = json.load(f)
    rows = []
    for ads in raw["competitors"].values():
        rows.extend(ads)
    if not rows:
        return pd.DataFrame(), raw.get("fetched_date", ""), 0, len(raw.get("competitors", {}))
    df = pd.DataFrame(rows)
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["stop_date"]  = pd.to_datetime(df["stop_date"],  errors="coerce")
    df["is_active"]  = df["stop_date"].isna()
    df["days_running"] = pd.to_numeric(df["days_running"], errors="coerce").fillna(0).astype(int)
    df["snippet"]    = df["ad_copy"].fillna("").str[:130].str.strip() + "..."
    fetched = pd.Timestamp(raw.get("fetched_date") or pd.Timestamp.utcnow().date())
    df["days_since_start"]  = (fetched - df["start_date"]).dt.days.clip(lower=0)
    df["is_new14"]          = df["days_since_start"] <= 14
    df["is_new7"]           = df["days_since_start"] <= 7
    df["tone"]              = df["ad_copy"].fillna("").apply(tag_tone)
    df["cta_label"]         = df.apply(lambda r: extract_cta(r.to_dict()), axis=1)
    return df, raw.get("fetched_date", ""), raw.get("total_ads", len(rows)), len(raw.get("competitors", {}))


df, fetched_date, total_ads, n_competitors = load_ads()

if df.empty:
    st.error(
        "No Meta ad data found in `data/ads_scraped_latest.json`. "
        "Run `python scrapers/scrape_ads.py` first."
    )
    st.stop()

active_df = df[df["is_active"]]
new14_df  = df[df["is_new14"]]
new7_df   = df[df["is_new7"]]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="margin-bottom:0.2rem;">🎯 Meta Intel</h1>'
    f'<p class="muted" style="margin-top:0;">'
    f"Meta Ad Library · fetched {fetched_date} · {total_ads} total ads · "
    f"{n_competitors} competitors tracked"
    "</p>",
    unsafe_allow_html=True,
)

# ── 4 stat cards ──────────────────────────────────────────────────────────────
def _stat(value, label, *, color=None):
    color = color or COLORS["accent"]
    return (
        '<div class="stat-card">'
        f'<div class="stat-value" style="color:{color};">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        '</div>'
    )


cards_html = '<div class="stat-grid">'
cards_html += _stat(total_ads, "Total ads scraped")
cards_html += _stat(len(active_df), "Active ads", color=COLORS["evergreen"])
cards_html += _stat(len(new14_df), "New this week (14d)", color=COLORS["soon"])
cards_html += _stat(n_competitors, "Competitors tracked")
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Total ads per competitor
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📊 Total ads per competitor")
total_counts = (
    df.groupby("competitor").size()
    .reset_index(name="total")
    .sort_values("total", ascending=True)
)
bar_colors = [comp_color(c) for c in total_counts["competitor"]]
fig_bar = go.Figure(go.Bar(
    x=total_counts["total"],
    y=total_counts["competitor"],
    orientation="h",
    marker=dict(color=bar_colors, opacity=0.9, line=dict(color=COLORS["border"], width=1)),
    text=total_counts["total"],
    textposition="outside",
    textfont=dict(color=COLORS["text"], size=13, family="Inter"),
    hovertemplate="<b>%{y}</b><br>Total Ads: %{x}<extra></extra>",
))
fig_bar.update_layout(**PLOTLY_LAYOUT, height=320, showlegend=False, transition_duration=400)
fig_bar.update_xaxes(showgrid=True)
fig_bar.update_yaxes(showgrid=False, tickfont=dict(size=13))
st.plotly_chart(fig_bar, use_container_width=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Strategic Playbook
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🎯 Listn Strategic Playbook")

PLAYBOOK = [
    {"priority": "HIGH",   "title": "Make the elder the hero of your adult-child-targeted ads",
     "action": "Keep targeting adult children (35–55) on Meta but reframe creatives — show the parent as a protagonist with a remarkable life, not a passive gift recipient.",
     "why": "Every competitor shows the elder as an object to be preserved. Listn's angle: your parent has a story that will blow your mind — and you haven't asked yet."},
    {"priority": "HIGH",   "title": "Make voice the product, not the book",
     "action": "Build brand identity around the irreplaceable nature of a human voice, not a printed artifact.",
     "why": "Remento quotes 'you will always have their voice' but doesn't build their brand around it — Listn can own this entirely."},
    {"priority": "HIGH",   "title": "Test grief-adjacent urgency with warmth",
     "action": "Lead with a specific wistful moment ('I forgot to ask him what he was most proud of') then redirect to possibility, not guilt.",
     "why": "Storykeeper just started testing this tone — Listn must move faster."},
    {"priority": "MEDIUM", "title": "Own specificity over autobiography",
     "action": "Run ads zoomed into one moment — 'Ask her about the summer of 1968' — not 'capture their whole life story'.",
     "why": "Entire category frames memory preservation as homework — specificity removes the overwhelm entirely."},
    {"priority": "MEDIUM", "title": "Target the caregiver segment",
     "action": "Create a dedicated campaign for adult children of parents with early cognitive decline.",
     "why": "Remento touched this once (18 days, then stopped) — high-urgency audience with nowhere to go in the market."},
    {"priority": "MEDIUM", "title": "Test the multilingual / cultural legacy angle",
     "action": "'Some stories can only be told in the language they were lived in' — target immigrant families directly.",
     "why": "Zero competitors have run a single ad acknowledging multilingual families — enormous untapped scale."},
    {"priority": "MEDIUM", "title": "Reach elders directly through non-Meta channels",
     "action": "Partner with senior Facebook groups, senior-living newsletters, retirement community noticeboards.",
     "why": "Elders who self-motivate to preserve their own story are higher-retention users — channel is community, not paid social."},
]

remento_total = int(df[df["competitor"] == "Remento"].shape[0])
st.markdown(
    f'<div class="insight-card blue">'
    f'<div class="insight-title">📊 Competitive whitespace summary</div>'
    f'<div class="insight-body">'
    f'<strong>Remento:</strong> {remento_total} total ads — 100% targeting the adult-child gifter, '
    "zero speaking to elders directly.<br>"
    "<strong>Listn opportunity:</strong> elder-as-hero reframe + voice-as-product + "
    'caregiver segment = <strong>3 uncontested lanes</strong>.'
    "</div></div>",
    unsafe_allow_html=True,
)


def _playbook_card(item: dict) -> str:
    border_class = "blue" if item["priority"] == "HIGH" else "amber"
    pill_color = COLORS["accent"] if item["priority"] == "HIGH" else COLORS["soon"]
    icon = "⚡" if item["priority"] == "HIGH" else "◆"
    return (
        f'<div class="insight-card {border_class}">'
        f'<div style="display:inline-block;background:{pill_color};color:white;'
        'border-radius:999px;padding:2px 10px;font-size:0.62rem;font-weight:800;'
        'text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem;">'
        f'{icon} {item["priority"]} priority</div>'
        f'<div class="insight-title">{item["title"]}</div>'
        f'<div class="insight-body" style="margin-bottom:0.4rem;">{item["action"]}</div>'
        f'<div class="insight-body" style="font-size:0.82rem;">'
        f'<strong>Why: </strong>{item["why"]}'
        '</div></div>'
    )


col_l, col_r = st.columns(2)
for i, item in enumerate(PLAYBOOK):
    (col_l if i % 2 == 0 else col_r).markdown(_playbook_card(item), unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Tracking Gap insight (Heritage Whisper)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(
    '<div class="insight-card amber">'
    '<div class="insight-title">⚠️ Tracking Gap — Heritage Whisper</div>'
    '<div class="insight-body">'
    "Heritage Whisper runs <strong>minimal Meta ads</strong> but leads the industry on "
    "<strong>AI search readiness (45/100)</strong>. Their growth strategy is organic + "
    "AI citation. Listn must match their AI readiness before competing on content volume."
    "</div>"
    '<a href="AI_Readiness" class="insight-link">→ View AI Readiness page</a>'
    '</div>',
    unsafe_allow_html=True,
)
st.markdown("<hr>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Top 10 Longest-Running Ads
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🏆 Top 10 longest-running ads")
top10 = df.nlargest(10, "days_running").reset_index(drop=True)
for i, row in top10.iterrows():
    dot_color = COLORS["evergreen"] if row["is_active"] else COLORS["urgent"]
    status_txt = "Active" if row["is_active"] else "Stopped"
    days = int(row["days_running"])
    st.markdown(
        '<div style="background:{surface};border:1px solid {border};border-radius:10px;'
        'padding:0.85rem 1.1rem;margin-bottom:0.55rem;display:grid;'
        'grid-template-columns: 1fr auto;align-items:center;gap:1rem;">'
        '<div>'
        '<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">'
        '{badge}'
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        'background:{dot_color};box-shadow:0 0 6px {dot_color};"></span>'
        '<span class="muted" style="font-size:0.75rem;">{status}</span>'
        '</div>'
        '<div style="color:{muted};font-size:0.85rem;margin-top:0.4rem;line-height:1.5;">{snippet}</div>'
        '</div>'
        '<div style="text-align:right;">'
        '<div style="font-size:1.6rem;font-weight:800;color:{accent};line-height:1;">{days}</div>'
        '<div style="font-size:0.7rem;color:{muted};text-transform:uppercase;letter-spacing:0.06em;">days</div>'
        '</div></div>'.format(
            surface=COLORS["surface"], border=COLORS["border"], muted=COLORS["muted"],
            accent=COLORS["accent"], badge=comp_badge(row["competitor"]),
            dot_color=dot_color, status=status_txt, snippet=row["snippet"],
            days=days,
        ),
        unsafe_allow_html=True,
    )
st.markdown("<hr>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# New This Week (14d)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## ✨ New this week  *(ads started within 14 days)*")
if new14_df.empty:
    st.info("No ads started in the last 14 days.")
else:
    for competitor, group in new14_df.sort_values("days_since_start").groupby("competitor", sort=False):
        st.markdown(f"### {competitor}")
        for _, row in group.iterrows():
            age = f"{int(row['days_since_start'])}d old"
            stat = "🟢 Active" if row["is_active"] else "🔴 Stopped"
            st.markdown(
                f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
                f'border-left:3px solid {COLORS["evergreen"]};border-radius:10px;padding:0.85rem 1.1rem;'
                'margin-bottom:0.55rem;">'
                '<div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;">'
                f'{comp_badge(competitor)}'
                f'<span style="background:{COLORS["accent"]}22;color:{COLORS["accent"]};'
                'border-radius:999px;padding:1px 8px;font-size:0.68rem;font-weight:700;'
                f'letter-spacing:0.06em;">NEW · {age}</span>'
                f'<span class="muted" style="font-size:0.75rem;">{stat}</span>'
                '</div>'
                f'<div style="color:{COLORS["muted"]};font-size:0.85rem;margin-top:0.4rem;line-height:1.5;">{row["snippet"]}</div>'
                '</div>',
                unsafe_allow_html=True,
            )
st.markdown("<hr>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Ad Copy Swipe File
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🗂 Ad copy swipe file")
swipe = df[["competitor", "ad_copy", "tone", "cta_label", "days_running", "is_active"]].copy()
swipe["Ad Copy"] = df["ad_copy"].fillna("").str[:140] + "..."
swipe["Status"] = swipe["is_active"].map({True: "🟢 Active", False: "🔴 Stopped"})
swipe = swipe.rename(columns={
    "competitor": "Competitor",
    "tone": "Tone",
    "cta_label": "CTA",
    "days_running": "Days",
})

sf1, sf2, sf3 = st.columns([2, 1, 1])
with sf1:
    search = st.text_input("🔍 Search ad copy", placeholder="Type any keyword...")
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
st.markdown("<hr>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Emotional Tone Breakdown + "Where nobody is playing"
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 🎭 Emotional tone breakdown")
tone_rows = []
for comp, copy_text in zip(df["competitor"], df["ad_copy"].fillna("")):
    for t in all_tones(copy_text):
        tone_rows.append({"competitor": comp, "tone": t})
tone_df = pd.DataFrame(tone_rows)
tone_counts = tone_df.groupby(["competitor", "tone"]).size().reset_index(name="count")
tone_totals = tone_counts.groupby("competitor")["count"].transform("sum")
tone_counts["pct"] = (tone_counts["count"] / tone_totals * 100).round(1)
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
fig_tone.update_traces(textposition="outside", textfont=dict(size=10, color=COLORS["text"]))
fig_tone.update_layout(**PLOTLY_LAYOUT, height=420, transition_duration=400)
st.plotly_chart(fig_tone, use_container_width=True)

# Where nobody is playing — tone gap table
avg_per_tone = (
    tone_counts.groupby("tone")["pct"].mean().round(1).reset_index()
    .sort_values("pct")
)
gap = avg_per_tone[avg_per_tone["pct"] < 10].copy()
gap["Listn's opening"] = gap["tone"].map({
    "nostalgia":     "Test 'irreplaceable voice' creatives.",
    "urgency":       "Lead with 'before it's too late' but warm.",
    "gifting":       "Reframe gifting around the elder, not the buyer.",
    "fear of loss":  "Specific moments — 'I forgot to ask him what he was most proud of'.",
    "pride":         "'My grandparents are heroes now' testimonials.",
    "transactional": "Skip — Meminto already owns the price lane.",
})
gap = gap.rename(columns={"tone": "Tone", "pct": "Avg % across competitors"})

st.markdown("#### Where nobody is playing")
if gap.empty:
    st.info("No tones are under 10% share — every register is contested.")
else:
    st.dataframe(
        gap.reset_index(drop=True),
        use_container_width=True,
        column_config={
            "Tone":                       st.column_config.TextColumn(width="small"),
            "Avg % across competitors":   st.column_config.NumberColumn(width="medium", format="%.1f%%"),
            "Listn's opening":            st.column_config.TextColumn(width="large"),
        },
    )
    st.caption("Tones < 10% average — Listn's unowned creative territory.")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    "Meta Intel · Listn · scraped from Meta Ad Library</p>",
    unsafe_allow_html=True,
)
