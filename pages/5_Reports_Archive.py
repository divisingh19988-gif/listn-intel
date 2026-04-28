"""
Reports Archive — list, download, and (re)generate the weekly Excel files.

The 'Generate Report Now' button calls lib/excel_export.build_all_reports().
Download buttons stream the saved xlsx bytes via st.download_button.
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from lib.theme import inject_global_css, COLORS
from lib.data_freshness import show_freshness_banner
from lib.excel_export import (
    REPORTS_DIR,
    build_all_reports,
    list_reports,
    parse_week_from_filename,
)
from lib.supabase_client import current_iso_week

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Reports Archive · Listn", page_icon="📄", layout="wide")
inject_global_css()
show_freshness_banner()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<h1 style="margin-bottom:0.2rem;">📄 Reports Archive</h1>'
    f'<p class="muted" style="margin-top:0;">'
    "Weekly Excel reports — Meta Intel, SEO Intel, AI Readiness. "
    "Each file has Summary / Raw / Delta sheets."
    "</p>",
    unsafe_allow_html=True,
)


# ── Generate now ──────────────────────────────────────────────────────────────
gc1, gc2 = st.columns([1, 3])
with gc1:
    if st.button("⚡ Generate report now", type="primary", use_container_width=True):
        with st.spinner(f"Building reports for {current_iso_week()}…"):
            try:
                result = build_all_reports()
                st.success(
                    "Built " + " · ".join(p.name for p in result.values())
                )
                st.rerun()
            except Exception as e:
                st.error(f"Build failed: {e}")
with gc2:
    st.markdown(
        f'<p class="muted" style="font-size:0.85rem;line-height:1.5;margin-top:0.5rem;">'
        "Generates three Excel files for the current ISO week using the latest data "
        "from <code>data/</code>. Existing files for the same week will be overwritten."
        "</p>",
        unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ── Build the table of reports per week ───────────────────────────────────────
def _by_week() -> dict[str, dict[str, Path]]:
    grouped: dict[str, dict[str, Path]] = {}
    for path in list_reports():
        week = parse_week_from_filename(path)
        if path.stem.startswith("meta_intel_"):
            kind = "meta"
        elif path.stem.startswith("seo_intel_"):
            kind = "seo"
        elif path.stem.startswith("ai_readiness_"):
            kind = "ai"
        else:
            kind = "other"
        grouped.setdefault(week, {})[kind] = path
    return grouped


grouped = _by_week()

if not grouped:
    st.info(
        "No reports yet. Click **⚡ Generate report now** above to create the first set."
    )
else:
    # Render one row per week — newest first
    weeks_sorted = sorted(grouped.keys(), reverse=True)
    st.markdown("## Weekly reports")

    for week in weeks_sorted:
        files = grouped[week]
        # When was the latest file in this group last modified?
        latest_mtime = max(p.stat().st_mtime for p in files.values())
        generated_at = datetime.fromtimestamp(latest_mtime).strftime("%Y-%m-%d %H:%M")

        # Row container
        st.markdown(
            f'<div style="background:{COLORS["surface"]};border:1px solid {COLORS["border"]};'
            f'border-radius:12px;padding:1rem 1.25rem;margin-bottom:0.85rem;'
            'animation:fadeInUp 0.4s ease both;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            'margin-bottom:0.6rem;flex-wrap:wrap;gap:0.5rem;">'
            f'<div style="font-size:1.1rem;font-weight:700;color:{COLORS["text"]};">{week}</div>'
            f'<div class="muted" style="font-size:0.8rem;">Generated {generated_at}</div>'
            "</div>",
            unsafe_allow_html=True,
        )
        cols = st.columns(3)
        for col, (kind, label, icon) in zip(
            cols,
            [
                ("meta", "Meta Intel",     "🎯"),
                ("seo",  "SEO Intel",      "🔍"),
                ("ai",   "AI Readiness",   "🤖"),
            ],
        ):
            path = files.get(kind)
            with col:
                if path is None:
                    st.markdown(
                        f'<div class="muted" style="font-size:0.82rem;padding:0.5rem 0;">'
                        f"{icon} {label} — <em>missing</em></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    size_kb = path.stat().st_size / 1024
                    st.download_button(
                        label=f"{icon} Download {label} ({size_kb:.0f} KB)",
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"dl_{week}_{kind}",
                        use_container_width=True,
                    )
        st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    f"Reports Archive · Listn · files stored in <code>reports/</code></p>",
    unsafe_allow_html=True,
)
