"""
Strategic Brief — render the weekly markdown synthesis produced by analyze_ads.py.

Parses the brief into H2 sections, renders each as a styled card with a
sticky TOC on the right. Tables and blockquotes are themed inline so this
page's CSS doesn't leak into the rest of the app.
"""

import re
from datetime import datetime
from pathlib import Path

import streamlit as st

from lib.theme import inject_global_css, inject_sidebar, COLORS, COMP_COLOR
from lib.data_freshness import show_freshness_banner

DATA_DIR = Path(__file__).parent.parent / "data"
LATEST = DATA_DIR / "strategic_brief_latest.md"

# ── Page chrome ───────────────────────────────────────────────────────────────
inject_global_css()
inject_sidebar()
show_freshness_banner()


def _week_from_path(path: Path) -> str:
    """Pull '2026-W19' out of 'strategic_brief_2026-W19.md'. '' for _latest."""
    stem = path.stem.replace("strategic_brief_", "")
    return "" if stem == "latest" else stem


def _week_label(week: str) -> str:
    return f"Week {week}" if week else "Latest"


def _parse_sections(md: str) -> list[tuple[str, str]]:
    """Split markdown by H2 headers. Skip everything before the first H2."""
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_body: list[str] = []
    for line in md.splitlines():
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line[3:].strip()
            current_body = []
        elif current_title is not None:
            current_body.append(line)
    if current_title is not None:
        sections.append((current_title, "\n".join(current_body).strip()))
    return sections


def _color_competitor_headers(body: str) -> str:
    """Color H3 headers (competitor names) using COMP_COLOR brand mapping."""
    def replace(match: re.Match) -> str:
        name = match.group(1).strip()
        color = COMP_COLOR.get(name, COLORS["accent"])
        return f'### <span style="color:{color};">{name}</span>'
    return re.sub(r"^### (.+)$", replace, body, flags=re.MULTILINE)


def _escape_dollars(md: str) -> str:
    """Prevent Streamlit from interpreting `$...$` as LaTeX math by escaping
    standalone dollars. Skips content inside backtick code spans."""
    parts = re.split(r"(`[^`]*`)", md)
    for i in range(0, len(parts), 2):  # even indices = non-code text
        parts[i] = parts[i].replace("$", "\\$")
    return "".join(parts)


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="margin-bottom:0.2rem;">🧭 Strategic Brief</h1>'
    '<p class="muted" style="margin-top:0;">'
    "Claude's read of this week's competitor ads — themes, gaps, and the "
    "moves Listn should be making."
    "</p>",
    unsafe_allow_html=True,
)

# ── Discover briefs ───────────────────────────────────────────────────────────
archived = sorted(
    [p for p in DATA_DIR.glob("strategic_brief_*.md")
     if p.stem != "strategic_brief_latest"],
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)

# ── Empty state ───────────────────────────────────────────────────────────────
if not LATEST.exists() and not archived:
    st.info(
        "No strategic brief generated yet. "
        "Run `python analyze_ads.py` or wait for the next weekly refresh."
    )
    st.stop()

# ── Picker ────────────────────────────────────────────────────────────────────
options: list[tuple[str, Path]] = []
if LATEST.exists():
    latest_week = _week_from_path(archived[0]) if archived else ""
    label = f"Latest ({latest_week})" if latest_week else "Latest"
    options.append((label, LATEST))
for p in archived:
    options.append((_week_label(_week_from_path(p)), p))

# Deduplicate labels (latest and newest archive may share a week)
seen, deduped = set(), []
for label, path in options:
    if label in seen:
        continue
    seen.add(label)
    deduped.append((label, path))

labels = [label for label, _ in deduped]
path_by_label = dict(deduped)

selected_label = st.selectbox("Select brief", labels, index=0)
selected_path = path_by_label[selected_label]

# ── Caption: week label + timestamp ───────────────────────────────────────────
mtime = datetime.fromtimestamp(selected_path.stat().st_mtime)
week = (
    _week_from_path(archived[0]) if (selected_path == LATEST and archived)
    else _week_from_path(selected_path)
)
display_week = _week_label(week)
timestamp = mtime.strftime("%b %-d, %Y · %-I:%M %p")
st.markdown(
    f'<p style="color:{COLORS["muted"]};font-size:0.82rem;margin-top:-0.25rem;">'
    f'{display_week} · generated {timestamp}'
    "</p>",
    unsafe_allow_html=True,
)

# ── Page-scoped CSS for cards, tables, blockquotes, TOC ───────────────────────
st.markdown(
    f"""
<style>
  .brief-section {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-left: 4px solid {COLORS["accent"]};
    border-radius: 14px;
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.25rem;
    animation: fadeInUp 0.4s ease both;
    scroll-margin-top: 5rem;
  }}
  .brief-section .brief-kicker {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {COLORS["accent"]};
    margin-bottom: 0.4rem;
  }}
  .brief-section h2.brief-title {{
    font-size: 1.25rem !important;
    font-weight: 700 !important;
    margin: 0 0 1rem 0 !important;
    padding-bottom: 0.7rem !important;
    border-bottom: 1px solid {COLORS["border"]};
    color: {COLORS["text"]} !important;
  }}

  /* Tables inside the brief — themed, alt rows, padded cells */
  .brief-section table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.75rem 0 1rem 0;
    font-size: 0.86rem;
  }}
  .brief-section thead th {{
    background: {COLORS["bg"]};
    color: {COLORS["text"]} !important;
    text-align: left;
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid {COLORS["border"]};
    font-weight: 600;
  }}
  .brief-section tbody td {{
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid {COLORS["border"]};
    color: {COLORS["text"]} !important;
    vertical-align: top;
  }}
  .brief-section tbody tr:nth-child(even) td {{
    background: rgba(159, 155, 255, 0.04);
  }}
  .brief-section tbody tr:last-child td {{
    border-bottom: none;
  }}

  /* Blockquotes — swipe-file card style for ad copy */
  .brief-section blockquote {{
    background: rgba(159, 155, 255, 0.06);
    border-left: 3px solid {COLORS["accent"]};
    padding: 0.75rem 1rem;
    margin: 0.6rem 0;
    border-radius: 6px;
    font-style: italic;
    color: {COLORS["text"]};
  }}
  .brief-section blockquote p {{
    margin: 0;
    color: {COLORS["text"]} !important;
  }}

  /* Suppress markdown HR separators inside the brief — the section card
     border-left already separates content; an extra red/colored line is noise. */
  .brief-section hr {{
    display: none;
  }}

  /* Body text rhythm */
  .brief-section h3 {{
    display: block;
    background: rgba(159, 155, 255, 0.08);
    border-left: 3px solid {COLORS["accent"]};
    padding: 0.5rem 0.85rem;
    border-radius: 6px;
    margin: 1.5rem 0 0.75rem 0 !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    color: {COLORS["text"]} !important;
  }}
  /* Indent the body that follows a competitor H3 so the visual grouping is
     clear, without a dangling left-border stub on just the first sibling. */
  .brief-section h3 ~ p,
  .brief-section h3 ~ ul,
  .brief-section h3 ~ table,
  .brief-section h3 ~ blockquote {{
    margin-left: 0.4rem;
    padding-left: 0.85rem;
  }}
  .brief-section p, .brief-section li {{
    color: {COLORS["text"]} !important;
    line-height: 1.65;
  }}
  .brief-section strong {{ color: {COLORS["text"]}; }}

  /* TOC */
  .brief-toc {{
    position: sticky;
    top: 5rem;
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 1rem 1.1rem;
  }}
  .brief-toc-heading {{
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {COLORS["muted"]};
    margin-bottom: 0.7rem;
  }}
  .brief-toc a {{
    display: block;
    color: {COLORS["text"]} !important;
    text-decoration: none;
    font-size: 0.84rem;
    line-height: 1.45;
    padding: 0.32rem 0;
    border-bottom: 1px solid transparent;
    transition: color 0.15s ease;
  }}
  .brief-toc a:hover {{
    color: {COLORS["accent"]} !important;
  }}
  .brief-toc a + a {{
    border-top: 1px solid {COLORS["border"]};
  }}
</style>
""",
    unsafe_allow_html=True,
)

# ── Parse + render ────────────────────────────────────────────────────────────
sections = _parse_sections(selected_path.read_text(encoding="utf-8"))

if not sections:
    st.warning("This brief has no H2 sections — falling back to raw render.")
    st.markdown(
        _escape_dollars(selected_path.read_text(encoding="utf-8")),
        unsafe_allow_html=True,
        help=None,
    )
    st.stop()

content_col, toc_col = st.columns([3, 1])

with content_col:
    for i, (title, body) in enumerate(sections, start=1):
        # Escape standalone $ so Streamlit doesn't render "$99" as LaTeX math.
        body = _escape_dollars(body)
        # Tint H3 competitor names with their brand color from COMP_COLOR.
        body = _color_competitor_headers(body)
        # Wrap each section in a div with id="section-N". The blank lines
        # around `body` let markdown-it process tables/blockquotes/lists
        # inside the HTML wrapper.
        st.markdown(
            f'<div class="brief-section" id="section-{i}">\n'
            f'<div class="brief-kicker">Section {i}</div>\n'
            f'<h2 class="brief-title">{title}</h2>\n\n'
            f'{body}\n\n'
            f'</div>',
            unsafe_allow_html=True,
            help=None,
        )

with toc_col:
    toc_links = "".join(
        f'<a href="#section-{i}">{title}</a>'
        for i, (title, _) in enumerate(sections, start=1)
    )
    st.markdown(
        '<div class="brief-toc">'
        '<div class="brief-toc-heading">On this page</div>'
        f'{toc_links}'
        '</div>',
        unsafe_allow_html=True,
    )
