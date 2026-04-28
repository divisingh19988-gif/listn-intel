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
from datetime import date

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

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
     unsafe_allow_html=True,
)

