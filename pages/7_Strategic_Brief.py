"""
Strategic Brief — render the weekly markdown brief produced by analyze_ads.py.

Defaults to data/strategic_brief_latest.md; a dropdown lets you switch to any
archived week. If no brief has been generated yet, shows an empty-state message.
"""

from datetime import datetime
from pathlib import Path

import streamlit as st

from lib.theme import inject_global_css, inject_sidebar, COLORS
from lib.data_freshness import show_freshness_banner

DATA_DIR = Path(__file__).parent.parent / "data"
LATEST = DATA_DIR / "strategic_brief_latest.md"

# ── Page chrome ───────────────────────────────────────────────────────────────
inject_global_css()
inject_sidebar()
show_freshness_banner()

st.markdown(
    '<h1 style="margin-bottom:0.2rem;">🧭 Strategic Brief</h1>'
    '<p class="muted" style="margin-top:0;">'
    "Claude's synthesis of this week's competitive ad activity — themes, gaps, and recommended moves."
    "</p>",
    unsafe_allow_html=True,
)


def _week_label(path: Path) -> str:
    """Extract a 'Week YYYY-Www' label from a filename like strategic_brief_2026-W19.md."""
    stem = path.stem.replace("strategic_brief_", "")
    if stem and stem != "latest":
        return f"Week {stem}"
    return path.stem


# ── Discover archived briefs ──────────────────────────────────────────────────
archived = sorted(
    [p for p in DATA_DIR.glob("strategic_brief_*.md") if p.stem != "strategic_brief_latest"],
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

if not LATEST.exists() and not archived:
    st.info(
        "No strategic brief generated yet. "
        "Run `analyze_ads.py` or wait for the next weekly refresh."
    )
    st.stop()

# ── Picker ────────────────────────────────────────────────────────────────────
options: list[tuple[str, Path]] = []
if LATEST.exists():
    options.append(("Latest", LATEST))
options.extend((_week_label(p), p) for p in archived)

labels = [label for label, _ in options]
selected_label = st.selectbox("Select brief", labels, index=0)
selected_path = dict(options)[selected_label]

# ── Caption: generation date + week label ─────────────────────────────────────
mtime = datetime.fromtimestamp(selected_path.stat().st_mtime)
display_label = _week_label(selected_path) if selected_path != LATEST else (
    _week_label(archived[0]) if archived else "Latest"
)
st.markdown(
    f'<p style="color:{COLORS["muted"]};font-size:0.82rem;margin-top:-0.25rem;">'
    f'{display_label} · generated {mtime.strftime("%b %d, %Y at %I:%M %p")}'
    "</p>",
    unsafe_allow_html=True,
)

st.markdown("---")

# ── Render brief ──────────────────────────────────────────────────────────────
st.markdown(selected_path.read_text(encoding="utf-8"))
