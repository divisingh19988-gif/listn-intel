"""
Listn Intel — multipage entry point.

Defines the navigation (st.navigation) and the single global st.set_page_config.
Each page script (views/overview.py and pages/*.py) handles its own chrome via
inject_global_css() / inject_sidebar() / show_freshness_banner().
"""

from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

st.set_page_config(
    page_title="Listn Intel",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = [
    st.Page("views/overview.py",          title="Overview",        icon="🎙", default=True),
    st.Page("pages/1_Meta_Intel.py",      title="Meta Intel",      icon="🎯", url_path="Meta_Intel"),
    st.Page("pages/2_SEO_Intel.py",       title="SEO Intel",       icon="🔍", url_path="SEO_Intel"),
    st.Page("pages/3_AI_Readiness.py",    title="AI Readiness",    icon="🤖", url_path="AI_Readiness"),
    st.Page("pages/4_Action_Tracker.py",  title="Action Tracker",  icon="✅", url_path="Action_Tracker"),
    st.Page("pages/5_Reports_Archive.py", title="Reports Archive", icon="📄", url_path="Reports_Archive"),
    st.Page("pages/7_Strategic_Brief.py", title="Strategic Brief", icon="🧭", url_path="Strategic_Brief"),
    st.Page("pages/6_Admin.py",           title="Admin",           icon="⚙️", url_path="Admin"),
]

st.navigation(PAGES).run()
