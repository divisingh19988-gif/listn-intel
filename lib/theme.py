"""
Listn Intel design system.

One source of truth for colors, typography, spacing, and global CSS injection.
Every page must call inject_global_css() once near the top of the file.
"""

import streamlit as st

# ── Color tokens (used by Plotly, st.markdown, and conditional logic) ─────────
COLORS = {
    "bg":         "#0F1117",
    "surface":    "#1C1E26",
    "border":     "#2A2D3A",
    "text":       "#F0F0F0",
    "muted":      "#8B8FA8",
    "accent":     "#4F8EF7",
    "urgent":     "#E5534B",
    "soon":       "#F5A623",
    "evergreen":  "#34C984",
}

# ── Plotly defaults — pass with **PLOTLY_LAYOUT into fig.update_layout ────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text"], family="Inter, system-ui, sans-serif", size=13),
    margin=dict(l=0, r=20, t=20, b=10),
    xaxis=dict(
        gridcolor=COLORS["border"],
        color=COLORS["muted"],
        showline=False,
        zeroline=False,
    ),
    yaxis=dict(
        gridcolor=COLORS["border"],
        color=COLORS["muted"],
        showline=False,
        zeroline=False,
    ),
    legend=dict(
        bgcolor=COLORS["surface"],
        bordercolor=COLORS["border"],
        font=dict(color=COLORS["text"]),
    ),
)

# Per-competitor color map. Listn = accent. Heritage Whisper = evergreen
# (industry leader on AI readiness). Everyone else = a muted distinct hue.
COMP_COLOR = {
    "Listn":             COLORS["accent"],         # accent blue
    "Remento":           "#FF6B6B",                # coral (strongest competitor — needs prominent hue)
    "Heritage Whisper":  COLORS["evergreen"],      # green — AI-readiness leader
    "Meminto":           "#FCD34D",                # amber-yellow
    "StoryWorth":        "#F97316",                # orange
    "Storykeeper":       "#A3E635",                # lime
    "StoryKeeper":       "#A3E635",
    "Keepsake":          "#F472B6",                # pink
    "StoriedLife AI":    "#22D3EE",                # cyan
    "LifeEcho":          "#EC4899",                # magenta
    "Storii":            "#06B6D4",                # teal
    "Tell me":           "#9CA3AF",                # muted gray (no Meta presence)
    "HereAfter AI":      "#9CA3AF",
    "No Story Lost":     "#9CA3AF",
}


def comp_color(name: str) -> str:
    """Return brand color for a competitor name; muted gray for unknowns."""
    return COMP_COLOR.get(name, COLORS["muted"])


# ── Window badge helper (URGENT / SOON / EVERGREEN / COMMERCIAL INTENT) ───────
WINDOW_BADGE_COLOR = {
    "URGENT":            COLORS["urgent"],
    "SOON":              COLORS["soon"],
    "EVERGREEN":         COLORS["evergreen"],
    "COMMERCIAL INTENT": COLORS["accent"],
}


def window_badge(label: str) -> str:
    """Return inline HTML for a window pill."""
    color = WINDOW_BADGE_COLOR.get(label, COLORS["muted"])
    return (
        f'<span style="display:inline-block;border-radius:999px;'
        f'padding:2px 10px;font-size:0.7rem;font-weight:700;'
        f'letter-spacing:0.06em;text-transform:uppercase;'
        f'background:{color}22;color:{color};border:1px solid {color}55;">'
        f'{label}</span>'
    )


# ── Stat card helper ──────────────────────────────────────────────────────────
def stat_card(value: str, label: str, implication: str = "", *, accent: str = None) -> str:
    """
    Stat card markup: big number, label below, 11px muted implication line.
    Returns an HTML string suitable for st.markdown(..., unsafe_allow_html=True).
    """
    accent_color = accent or COLORS["accent"]
    impl_html = (
        f'<div class="stat-impl">{implication}</div>' if implication else ""
    )
    return (
        '<div class="stat-card">'
        f'<div class="stat-value" style="color:{accent_color};">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        f'{impl_html}'
        '</div>'
    )


# ── Global CSS — inject once per page ─────────────────────────────────────────
_GLOBAL_CSS = f"""
<style>
  /* Inter via Google Fonts */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  /* Base */
  html, body, [data-testid="stAppViewContainer"] {{
    background-color: {COLORS["bg"]} !important;
    color: {COLORS["text"]};
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    -webkit-font-smoothing: antialiased;
  }}
  .stApp {{ background-color: {COLORS["bg"]} !important; }}

  /* Hide "streamlit app" from sidebar navigation */
  [data-testid="stSidebarNav"] li:first-child {{
    display: none !important;
  }
  
  /* Hide keyboard shortcuts indicator */
  [data-testid="stCaptionContainer"],
  [title*="Keyboard"],
  [aria-label*="Keyboard"] {{
    display: none !important;
  }

  /* Streamlit's header bar (~60–70px tall) sits sticky over the top of the
     main content area. Push content down so nothing is clipped under it. */
  [data-testid="stHeader"] {{
    background: {COLORS["bg"]} !important;
    border-bottom: 1px solid {COLORS["border"]};
    height: 56px;
  }}
  [data-testid="stToolbar"] {{ right: 1rem; }}
  .block-container {{
    padding-top: 5rem !important;
    padding-bottom: 3rem;
    max-width: 1400px;
  }}

  /* First child of the main column is usually the freshness banner — give it
     extra top breathing room so it never gets clipped. */
  .main .block-container > div:first-child .freshness-banner:first-child,
  .main .block-container .freshness-banner {{
    margin-top: 0.25rem;
  }}

  /* Headings + body text */
  h1, h2, h3, h4, h5, h6 {{
    color: {COLORS["text"]} !important;
    font-family: 'Inter', system-ui, sans-serif !important;
    font-weight: 700;
    letter-spacing: -0.01em;
  }}
  h1 {{ font-size: 1.85rem; font-weight: 800; }}
  h2 {{ font-size: 1.35rem; }}
  h3 {{ font-size: 1.1rem; }}
  p, li, td, th, label, .stMarkdown, .stCaption p {{
    color: {COLORS["text"]} !important;
    font-family: 'Inter', system-ui, sans-serif !important;
  }}
  .stCaption p {{ color: {COLORS["muted"]} !important; font-size: 0.8rem; }}
  small, .muted {{ color: {COLORS["muted"]} !important; }}

  /* Dividers */
  hr {{ border: none; border-top: 1px solid {COLORS["border"]}; margin: 1.25rem 0; }}

  /* Sidebar */
  [data-testid="stSidebar"] {{
    background: {COLORS["surface"]} !important;
    border-right: 1px solid {COLORS["border"]};
  }}
  [data-testid="stSidebar"] * {{ color: {COLORS["text"]} !important; font-family: 'Inter', sans-serif !important; }}
  [data-testid="stSidebar"] .muted {{ color: {COLORS["muted"]} !important; }}

  /* Freshness banner */
  .freshness-banner {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    padding: 10px 16px;
    margin-bottom: 1rem;
    font-size: 0.82rem;
    color: {COLORS["muted"]};
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 40px;
  }}
  .freshness-banner.stale {{
    background: {COLORS["urgent"]}15;
    border-color: {COLORS["urgent"]};
    color: {COLORS["urgent"]};
  }}
  .freshness-banner strong {{ color: {COLORS["text"]}; }}
  .freshness-banner.stale strong {{ color: {COLORS["urgent"]}; }}

  /* Stat cards */
  .stat-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
    margin-bottom: 1rem;
  }}
  .stat-card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 1.1rem 1.25rem;
    transition: border-color 0.2s ease, transform 0.15s ease;
    animation: fadeInUp 0.4s ease both;
  }}
  .stat-card:hover {{ border-color: {COLORS["accent"]}66; transform: translateY(-1px); }}
  .stat-value {{
    font-size: 2.1rem;
    font-weight: 800;
    line-height: 1.05;
    margin-bottom: 0.25rem;
    letter-spacing: -0.02em;
  }}
  .stat-label {{
    font-size: 0.78rem;
    color: {COLORS["muted"]};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
  }}
  .stat-impl {{
    color: {COLORS["muted"]};
    font-size: 11px;
    margin-top: 0.5rem;
    line-height: 1.45;
  }}

  /* Insight cards (left-border accent) */
  .insight-card {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
    padding: 1.1rem 1.3rem;
    margin-bottom: 1rem;
    animation: fadeInUp 0.45s ease both;
  }}
  .insight-card.amber  {{ border-left: 4px solid {COLORS["soon"]}; }}
  .insight-card.blue   {{ border-left: 4px solid {COLORS["accent"]}; }}
  .insight-card.urgent {{ border-left: 4px solid {COLORS["urgent"]}; }}
  .insight-card.green  {{ border-left: 4px solid {COLORS["evergreen"]}; }}
  .insight-title {{
    font-size: 0.97rem; font-weight: 700;
    color: {COLORS["text"]};
    margin-bottom: 0.45rem;
  }}
  .insight-body {{ color: {COLORS["muted"]}; font-size: 0.87rem; line-height: 1.6; }}
  .insight-body strong {{ color: {COLORS["text"]}; }}
  .insight-link {{
    display: inline-block;
    margin-top: 0.65rem;
    color: {COLORS["accent"]} !important;
    font-size: 0.82rem;
    font-weight: 600;
    text-decoration: none;
  }}
  .insight-link:hover {{ text-decoration: underline; }}

  /* Inputs */
  .stTextInput input, .stSelectbox > div, .stNumberInput input {{
    background: {COLORS["surface"]} !important;
    color: {COLORS["text"]} !important;
    border-color: {COLORS["border"]} !important;
  }}
  .stTextInput input:focus {{
    border-color: {COLORS["accent"]} !important;
    box-shadow: 0 0 0 2px {COLORS["accent"]}33 !important;
  }}

  /* Buttons */
  .stButton button {{
    border-radius: 8px;
    font-weight: 600;
    border: 1px solid {COLORS["border"]};
    background: {COLORS["surface"]};
    color: {COLORS["text"]};
    transition: all 0.15s ease;
  }}
  .stButton button:hover {{
    border-color: {COLORS["accent"]};
    color: {COLORS["accent"]};
  }}
  .stButton button[kind="primary"] {{
    background: {COLORS["accent"]};
    color: white;
    border-color: {COLORS["accent"]};
  }}

  /* Dataframe */
  [data-testid="stDataFrame"] {{ border-radius: 10px; }}
  [data-testid="stDataFrame"] thead tr th {{
    background: {COLORS["surface"]} !important;
    color: {COLORS["muted"]} !important;
  }}

  /* Animations */
  @keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}

  /* Mobile */
  @media (max-width: 640px) {{
    .stat-grid {{ grid-template-columns: 1fr; }}
    .block-container {{ padding-top: 0.75rem; }}
  }}
</style>
"""


def inject_global_css() -> None:
    """Inject the global stylesheet. Call once per page near the top."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
