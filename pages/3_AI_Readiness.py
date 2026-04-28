"""
AI Readiness — how well each competitor's site is set up for AI search engines.

Reads data/ai_readiness_latest.json (produced by scrapers/ai_readiness_check.py).
Falls back to a hardcoded baseline (from the manual audits we ran in late April).

Listn opportunity is to close the gap on Heritage Whisper (95) — they lead the
industry on AI-citation readiness while running barely any Meta ads.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from lib.theme import inject_global_css, COLORS
from lib.data_freshness import show_freshness_banner
from lib.supabase_client import (
    get_client,
    is_configured as supabase_configured,
    add_action,
    current_iso_week,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Readiness · Listn", page_icon="🤖", layout="wide")
inject_global_css()
show_freshness_banner()

ROOT = Path(__file__).parent.parent
AI_FILE = ROOT / "data" / "ai_readiness_latest.json"

# ── Baseline (manual audit, late April 2026) ──────────────────────────────────
BASELINE = [
    {"name": "Heritage Whisper", "llms_txt": "Yes", "ai_bots": 20, "faq_schema": "Yes",
     "article_schema": "Yes", "canonical_pct": 95, "metadesc_pct": 90, "score": 95},
    {"name": "Remento", "llms_txt": "No", "ai_bots": 0, "faq_schema": "No",
     "article_schema": "No", "canonical_pct": 8, "metadesc_pct": 0, "score": 20},
    {"name": "StoryWorth", "llms_txt": "No", "ai_bots": 0, "faq_schema": "No",
     "article_schema": "No", "canonical_pct": "Unknown", "metadesc_pct": "Unknown", "score": 15},
    {"name": "Meminto", "llms_txt": "No", "ai_bots": 0, "faq_schema": "No",
     "article_schema": "No", "canonical_pct": "Unknown", "metadesc_pct": "Unknown", "score": 10},
    {"name": "Listn", "llms_txt": "No", "ai_bots": 0, "faq_schema": "No",
     "article_schema": "No", "canonical_pct": 0, "metadesc_pct": 0, "score": 5},
    {"name": "Storykeeper", "llms_txt": "—", "ai_bots": "—", "faq_schema": "—",
     "article_schema": "—", "canonical_pct": "—", "metadesc_pct": "—", "score": "Not yet audited"},
    {"name": "StoriedLife AI", "llms_txt": "—", "ai_bots": "—", "faq_schema": "—",
     "article_schema": "—", "canonical_pct": "—", "metadesc_pct": "—", "score": "Not yet audited"},
    {"name": "LifeEcho", "llms_txt": "—", "ai_bots": "—", "faq_schema": "—",
     "article_schema": "—", "canonical_pct": "—", "metadesc_pct": "—", "score": "Not yet audited"},
    {"name": "Storii", "llms_txt": "—", "ai_bots": "—", "faq_schema": "—",
     "article_schema": "—", "canonical_pct": "—", "metadesc_pct": "—", "score": "Not yet audited"},
]


@st.cache_data
def load_audit() -> tuple[list[dict], str]:
    """Prefer real audit, fall back to baseline."""
    if AI_FILE.exists():
        with open(AI_FILE) as f:
            data = json.load(f)
        rows = data.get("sites") or data.get("results")
        if rows:
            return rows, data.get("fetched_date", "")
    return BASELINE, "baseline (manual audit, Apr 2026)"


rows, audit_label = load_audit()
df = pd.DataFrame(rows)


# ── Header + 4 stat cards ─────────────────────────────────────────────────────
st.markdown(
    f'<h1 style="margin-bottom:0.2rem;">🤖 AI Readiness</h1>'
    f'<p class="muted" style="margin-top:0;">'
    f"7 signals × {len(df)} sites · source: {audit_label}"
    "</p>",
    unsafe_allow_html=True,
)


def _numeric_score(v):
    return v if isinstance(v, (int, float)) else None


df["_num_score"] = df["score"].apply(_numeric_score)
listn_score = df.loc[df["name"] == "Listn", "_num_score"].iloc[0] if not df[df["name"] == "Listn"].empty else 0
leader_idx = df["_num_score"].idxmax()
leader = df.loc[leader_idx]
numeric_scores = df["_num_score"].dropna()
industry_avg = round(numeric_scores.mean(), 1) if not numeric_scores.empty else 0
gap = listn_score - leader["_num_score"] if isinstance(listn_score, (int, float)) else 0


def _stat(value, label, color):
    return (
        '<div class="stat-card">'
        f'<div class="stat-value" style="color:{color};">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        '</div>'
    )


def _score_color(score) -> str:
    if not isinstance(score, (int, float)):
        return COLORS["muted"]
    if score >= 75:
        return COLORS["evergreen"]
    if score >= 40:
        return COLORS["soon"]
    return COLORS["urgent"]


cards_html = '<div class="stat-grid">'
cards_html += _stat(f"{listn_score}/100", "Listn AI Score", _score_color(listn_score))
cards_html += _stat(f"{leader['name']} {int(leader['_num_score'])}/100", "Industry leader", COLORS["evergreen"])
cards_html += _stat(industry_avg, "Industry average", COLORS["accent"])
gap_int = int(gap) if pd.notna(gap) else 0
cards_html += _stat(f"{gap_int:+d} pts", "Listn's gap to leader",
                    COLORS["urgent"] if gap_int < 0 else COLORS["evergreen"])
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 7-signal table
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## 📋 Per-site AI readiness signals")
st.markdown(
    f'<p class="muted" style="margin-top:-0.5rem;font-size:0.86rem;">'
    "llms.txt · AI bots allowed · FAQ schema · Article schema · "
    "canonical % · meta-desc % · composite score"
    "</p>",
    unsafe_allow_html=True,
)


def _yesno_chip(v) -> str:
    if v == "Yes":
        c = COLORS["evergreen"]
    elif v == "No":
        c = COLORS["urgent"]
    else:
        c = COLORS["muted"]
    return (
        f'<span style="display:inline-block;padding:1px 8px;border-radius:999px;'
        f'background:{c}1F;color:{c};border:1px solid {c}55;'
        f'font-size:0.74rem;font-weight:700;">{v}</span>'
    )


def _bots_chip(v) -> str:
    if isinstance(v, (int, float)):
        if v >= 3:
            c = COLORS["evergreen"]
        elif v == 0:
            c = COLORS["urgent"]
        else:
            c = COLORS["soon"]
        return (
            f'<span style="display:inline-block;padding:1px 8px;border-radius:999px;'
            f'background:{c}1F;color:{c};border:1px solid {c}55;'
            f'font-size:0.74rem;font-weight:700;">{v}</span>'
        )
    return f'<span class="muted">{v}</span>'


def _pct_chip(v) -> str:
    if isinstance(v, (int, float)):
        c = COLORS["evergreen"] if v >= 75 else COLORS["soon"] if v >= 40 else COLORS["urgent"]
        return (
            f'<span style="display:inline-block;padding:1px 8px;border-radius:999px;'
            f'background:{c}1F;color:{c};border:1px solid {c}55;'
            f'font-size:0.74rem;font-weight:700;">{v}%</span>'
        )
    return f'<span class="muted">{v}</span>'


def _score_chip(v) -> str:
    if isinstance(v, (int, float)):
        c = _score_color(v)
        return (
            f'<span style="display:inline-block;padding:2px 11px;border-radius:999px;'
            f'background:{c}26;color:{c};border:1px solid {c}66;'
            f'font-size:0.85rem;font-weight:800;">{int(v)}</span>'
        )
    return f'<span class="muted">{v}</span>'


# Build a custom HTML table so we can keep colored chips
header_cols = ["Competitor", "llms.txt", "AI bots", "FAQ schema", "Article schema",
               "Canonical %", "Meta desc %", "Score"]
table_html = (
    f'<div style="border:1px solid {COLORS["border"]};border-radius:12px;overflow:hidden;'
    'animation:fadeInUp 0.4s ease both;">'
    f'<div style="display:grid;grid-template-columns: 1.4fr 0.7fr 0.7fr 0.9fr 0.9fr 0.9fr 0.9fr 0.7fr;'
    f'background:{COLORS["surface"]};padding:0.55rem 1rem;font-size:0.7rem;font-weight:700;'
    f'color:{COLORS["muted"]};text-transform:uppercase;letter-spacing:0.08em;gap:0.5rem;">'
    + "".join(f"<span>{h}</span>" for h in header_cols)
    + "</div>"
)

# Sort by numeric score desc, "Not yet audited" rows last; Listn always highlighted
def _sort_key(row):
    s = row["_num_score"]
    if isinstance(s, (int, float)):
        return (0, -s)
    return (1, row["name"])


df_sorted = df.sort_values(
    by="_num_score",
    ascending=False,
    key=lambda col: col.fillna(-1),
).reset_index(drop=True)

for i, row in df_sorted.iterrows():
    is_listn = row["name"] == "Listn"
    bg = "rgba(79,142,247,0.08)" if is_listn else ("rgba(79,142,247,0.04)" if i % 2 else "transparent")
    border_left = (
        f'border-left:4px solid {COLORS["accent"]};' if is_listn else "border-left:4px solid transparent;"
    )
    table_html += (
        '<div style="display:grid;grid-template-columns: 1.4fr 0.7fr 0.7fr 0.9fr 0.9fr 0.9fr 0.9fr 0.7fr;'
        f'padding:0.55rem 1rem;gap:0.5rem;background:{bg};{border_left}'
        f'border-top:1px solid {COLORS["border"]};font-size:0.86rem;align-items:center;">'
        f'<span style="font-weight:{700 if is_listn else 600};color:{COLORS["text"]};">{row["name"]}</span>'
        f'<span>{_yesno_chip(row["llms_txt"])}</span>'
        f'<span>{_bots_chip(row["ai_bots"])}</span>'
        f'<span>{_yesno_chip(row["faq_schema"])}</span>'
        f'<span>{_yesno_chip(row["article_schema"])}</span>'
        f'<span>{_pct_chip(row["canonical_pct"])}</span>'
        f'<span>{_pct_chip(row["metadesc_pct"])}</span>'
        f'<span>{_score_chip(row["score"])}</span>'
        '</div>'
    )
table_html += "</div>"
st.markdown(table_html, unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Quick Wins for Listn
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("## ⚡ Quick wins for Listn")
st.markdown(
    f'<p class="muted" style="margin-top:-0.5rem;font-size:0.86rem;">'
    "Click <strong>+ Add to Action Tracker</strong> on any card to push it to the live tracker."
    "</p>",
    unsafe_allow_html=True,
)

QUICK_WINS = [
    {"title": "Add llms.txt to listn-app.com",
     "impact": "+15 pts",
     "detail": "Single static file at /llms.txt declaring crawl preferences. Heritage Whisper has one, Remento doesn't.",
     "priority": "HIGH"},
    {"title": "Allow GPTBot + ClaudeBot + PerplexityBot in robots.txt",
     "impact": "+10 pts",
     "detail": "Three User-agent lines. Today Listn blocks all of them by default.",
     "priority": "HIGH"},
    {"title": "Add FAQPage schema to any FAQ page",
     "impact": "+15 pts",
     "detail": "Single JSON-LD block per FAQ page. AI Overviews lift FAQ-marked answers verbatim.",
     "priority": "HIGH"},
    {"title": "Add Article schema to first blog post",
     "impact": "+10 pts",
     "detail": "Establishes E-E-A-T signal for authorship. Required before any AI citation.",
     "priority": "MEDIUM"},
]


def _push_to_tracker(title: str, priority: str) -> tuple[bool, str]:
    if not supabase_configured():
        return False, "Supabase not configured — set SUPABASE_URL and SUPABASE_KEY in secrets."
    client = get_client()
    if client is None:
        return False, "Could not connect to Supabase."
    try:
        add_action(
            client,
            source="ai_readiness",
            recommendation=title,
            priority=priority,
            status="Not Started",
            notes="",
            week_added=current_iso_week(),
        )
        return True, "Added to Action Tracker."
    except Exception as e:
        return False, f"Error: {e}"


col_a, col_b = st.columns(2)
for i, qw in enumerate(QUICK_WINS):
    target = col_a if i % 2 == 0 else col_b
    with target:
        st.markdown(
            '<div style="background:{surface};border:1px solid {border};'
            'border-left:4px solid {accent};border-radius:12px;padding:1.1rem 1.3rem;'
            'margin-bottom:0.75rem;animation:fadeInUp 0.4s ease both;">'
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            'margin-bottom:0.45rem;">'
            '<div style="font-size:0.62rem;font-weight:800;color:{accent};'
            'text-transform:uppercase;letter-spacing:0.1em;">QUICK WIN</div>'
            '<div style="font-size:0.78rem;font-weight:700;color:{evergreen};">{impact}</div>'
            '</div>'
            '<div style="font-size:0.97rem;font-weight:700;color:{text};margin-bottom:0.4rem;'
            'line-height:1.4;">{title}</div>'
            '<div style="color:{muted};font-size:0.85rem;line-height:1.55;'
            'margin-bottom:0.6rem;">{detail}</div>'
            '</div>'.format(
                surface=COLORS["surface"], border=COLORS["border"],
                accent=COLORS["accent"], evergreen=COLORS["evergreen"],
                text=COLORS["text"], muted=COLORS["muted"],
                impact=qw["impact"], title=qw["title"], detail=qw["detail"],
            ),
            unsafe_allow_html=True,
        )
        if st.button(f"+ Add to Action Tracker", key=f"qw_{i}", use_container_width=True):
            ok, msg = _push_to_tracker(qw["title"], qw["priority"])
            (st.success if ok else st.warning)(msg)

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    f"AI Readiness · Listn · last audit {audit_label}</p>",
    unsafe_allow_html=True,
)
