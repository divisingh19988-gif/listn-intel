"""
Admin — manage the reference-data tables (competitors, content_clusters,
tone_keywords) directly from the dashboard.

Three tabs, one per Supabase table. Each tab has:
  • stat cards (totals)
  • editable inline table (st.data_editor) for the cheap edits
  • "Add" form in an expander
  • "Delete" picker in an expander

The list_* helpers in lib/supabase_client.py filter to active=true; on this
admin page we read each table directly so inactive rows are visible (and can
be re-activated). Inserts / updates / deletes use the helpers.
"""

from datetime import date

import pandas as pd
import streamlit as st

from lib.theme import inject_global_css, inject_sidebar, COLORS
from lib.data_freshness import show_freshness_banner
from lib.supabase_client import (
    get_client,
    is_configured as supabase_configured,
    COMPETITORS_TABLE,
    CONTENT_CLUSTERS_TABLE,
    TONE_KEYWORDS_TABLE,
    add_competitors,
    update_competitors,
    delete_competitors,
    add_content_clusters,
    update_content_clusters,
    delete_content_clusters,
    add_tone_keywords,
    update_tone_keywords,
    delete_tone_keywords,
)

# ── Page chrome (page config is set once in streamlit_app.py) ─────────────────
inject_global_css()
inject_sidebar()
show_freshness_banner()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="margin-bottom:0.2rem;">⚙️ Admin</h1>'
    '<p class="muted" style="margin-top:0;">'
    "Manage reference data (competitors, content clusters, tone keywords) "
    "without touching code. Edits save to Supabase instantly."
    "</p>",
    unsafe_allow_html=True,
)

if not supabase_configured():
    st.error(
        "Supabase is not configured. Add `SUPABASE_URL` and `SUPABASE_KEY` to "
        "`.streamlit/secrets.toml` (or `.env`)."
    )
    st.stop()

client = get_client()
if client is None:
    st.error("Supabase package is installed but the client could not connect. Check your credentials.")
    st.stop()


# ── Shared helpers ────────────────────────────────────────────────────────────
WINDOW_OPTIONS = ["URGENT", "SOON", "EVERGREEN", "COMMERCIAL INTENT"]


def _csv_to_list(s) -> list[str]:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return []
    return [x.strip() for x in str(s).split(",") if x.strip()]


def _list_to_csv(arr) -> str:
    if arr is None or (isinstance(arr, float) and pd.isna(arr)):
        return ""
    if not isinstance(arr, (list, tuple)):
        return str(arr)
    return ", ".join(str(x) for x in arr)


def _stat(value, label, color=None) -> str:
    color = color or COLORS["accent"]
    return (
        '<div class="stat-card">'
        f'<div class="stat-value" style="color:{color};">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        '</div>'
    )


def _read_table(table_name: str) -> list[dict]:
    """Read every row (active OR inactive) so the admin can re-activate."""
    try:
        resp = (
            client.table(table_name)
            .select("*")
            .order("created_at", desc=True)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        st.error(f"Failed to load `{table_name}`: {e}")
        return []


def _clear_keys(keys: tuple[str, ...]) -> None:
    for k in keys:
        st.session_state.pop(k, None)


def _diff_value_changed(ov, nv) -> bool:
    """Skip pseudo-changes where both sides are NaN/None."""
    if pd.isna(ov) and pd.isna(nv):
        return False
    return ov != nv


def _cell_or_none(v):
    return None if pd.isna(v) else v


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_comp, tab_cluster, tab_tone = st.tabs(
    ["🏢 Competitors", "📅 Content Clusters", "🎭 Tone Keywords"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Competitors
# ══════════════════════════════════════════════════════════════════════════════
with tab_comp:
    rows = _read_table(COMPETITORS_TABLE)
    total = len(rows)
    active_n = sum(1 for r in rows if r.get("active"))

    cards = '<div class="stat-grid">'
    cards += _stat(total,            "Total competitors", COLORS["accent"])
    cards += _stat(active_n,         "Active",            COLORS["evergreen"])
    cards += _stat(total - active_n, "Inactive",          COLORS["muted"])
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Add a new competitor ──────────────────────────────────────────────────
    with st.expander("➕ Add a new competitor"):
        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("Name", key="new_comp_name", placeholder="e.g. Storyteller")
            new_seo = st.text_input("SEO domain", key="new_comp_seo", placeholder="example.com")
            new_appstore = st.text_input("App Store ID", key="new_comp_appstore", placeholder="optional")
        with c2:
            new_terms = st.text_input(
                "Meta search terms (comma-separated)",
                key="new_comp_terms",
                placeholder="e.g. Storyteller, StoryTeller App",
            )
            new_notes = st.text_input("Notes", key="new_comp_notes", placeholder="optional")
            new_active = st.checkbox("Active", value=True, key="new_comp_active")

        if st.button(
            "Add competitor", type="primary",
            disabled=not new_name.strip(),
            key="add_comp_btn",
        ):
            try:
                add_competitors(
                    client,
                    name=new_name.strip(),
                    meta_search_terms=_csv_to_list(new_terms),
                    seo_domain=new_seo.strip() or None,
                    appstore_id=new_appstore.strip() or None,
                    active=bool(new_active),
                    notes=new_notes.strip() or None,
                )
                st.success(f"Added competitor: {new_name.strip()}")
                _clear_keys(("new_comp_name", "new_comp_seo", "new_comp_appstore",
                             "new_comp_terms", "new_comp_notes", "new_comp_active"))
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Add failed: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Editable table ────────────────────────────────────────────────────────
    if not rows:
        st.info("No competitors yet. Use the form above to add one.")
    else:
        df = pd.DataFrame(rows)
        for col in ("name", "seo_domain", "active", "notes"):
            if col not in df.columns:
                df[col] = None
        display = df[["id", "name", "seo_domain", "active", "notes"]].copy().reset_index(drop=True)
        display["name"]       = display["name"].fillna("").astype(str)
        display["seo_domain"] = display["seo_domain"].fillna("").astype(str)
        display["active"]     = display["active"].fillna(True).astype(bool)
        display["notes"]      = display["notes"].fillna("").astype(str)

        id_list = display["id"].tolist()
        display = display.drop(columns=["id"])

        edited = st.data_editor(
            display,
            use_container_width=True,
            height=420,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "name":       st.column_config.TextColumn("Name", width="medium", disabled=True),
                "seo_domain": st.column_config.TextColumn("SEO domain", width="medium", disabled=True),
                "active":     st.column_config.CheckboxColumn("Active", width="small"),
                "notes":      st.column_config.TextColumn("Notes", width="large"),
            },
            key="competitors_editor",
        )

        if not edited.equals(display):
            diffs = []
            for idx in range(len(edited)):
                cid = id_list[idx]
                o, n = display.iloc[idx], edited.iloc[idx]
                patch = {}
                for col in ("active", "notes"):
                    if _diff_value_changed(o[col], n[col]):
                        patch[col] = _cell_or_none(n[col])
                if patch:
                    diffs.append((cid, patch))
            if diffs:
                for cid, patch in diffs:
                    try:
                        update_competitors(client, cid, patch)
                    except Exception as e:
                        st.warning(f"Failed to save competitor {cid}: {e}")
                st.success(f"Saved {len(diffs)} change(s).")
                st.cache_data.clear()
                st.rerun()

    # ── Delete a competitor ───────────────────────────────────────────────────
    with st.expander("🗑 Delete a competitor"):
        if not rows:
            st.caption("Nothing to delete.")
        else:
            del_id = st.selectbox(
                "Pick a competitor to delete",
                options=[r["id"] for r in rows],
                format_func=lambda i: next((r["name"] for r in rows if r["id"] == i), "?"),
                key="del_comp_id",
            )
            if st.button("Delete this competitor", type="secondary", key="del_comp_btn"):
                try:
                    delete_competitors(client, del_id)
                    st.success("Deleted.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Content Clusters
# ══════════════════════════════════════════════════════════════════════════════
with tab_cluster:
    rows = _read_table(CONTENT_CLUSTERS_TABLE)
    total = len(rows)
    active_n = sum(1 for r in rows if r.get("active"))

    cards = '<div class="stat-grid">'
    cards += _stat(total,            "Total clusters", COLORS["accent"])
    cards += _stat(active_n,         "Active",         COLORS["evergreen"])
    cards += _stat(total - active_n, "Inactive",       COLORS["muted"])
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Add a new cluster ─────────────────────────────────────────────────────
    with st.expander("➕ Add a new cluster"):
        c1, c2 = st.columns(2)
        with c1:
            nc_name = st.text_input("Name", key="new_cl_name", placeholder="e.g. Mother's Day")
            nc_window = st.selectbox("Window", WINDOW_OPTIONS, key="new_cl_window")
        with c2:
            nc_deadline = st.date_input("Deadline (optional)", value=None, key="new_cl_deadline")
            nc_active = st.checkbox("Active", value=True, key="new_cl_active")
        st.caption(
            "Keywords are managed in code for now — add the cluster first, then edit "
            "its `keywords` column directly in Supabase if needed."
        )

        if st.button(
            "Add cluster", type="primary",
            disabled=not nc_name.strip(),
            key="add_cl_btn",
        ):
            try:
                add_content_clusters(
                    client,
                    name=nc_name.strip(),
                    window_label=nc_window,
                    deadline=nc_deadline.isoformat() if nc_deadline else None,
                    active=bool(nc_active),
                    keywords=[],
                )
                st.success(f"Added cluster: {nc_name.strip()}")
                _clear_keys(("new_cl_name", "new_cl_window", "new_cl_deadline", "new_cl_active"))
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Add failed: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Editable table ────────────────────────────────────────────────────────
    if not rows:
        st.info("No content clusters yet. Use the form above to add one.")
    else:
        df = pd.DataFrame(rows)
        for col in ("name", "window_label", "deadline", "active", "keywords"):
            if col not in df.columns:
                df[col] = None

        # Read-only derived column: just show how many keywords each cluster has.
        df["keywords_summary"] = df["keywords"].apply(
            lambda v: f"{len(v)} keywords" if isinstance(v, list) else "—"
        )
        display = df[[
            "id", "name", "window_label", "deadline", "active", "keywords_summary",
        ]].copy().reset_index(drop=True)
        display["name"]             = display["name"].fillna("").astype(str)
        display["window_label"]     = display["window_label"].fillna("").astype(str)
        display["deadline"]         = pd.to_datetime(display["deadline"], errors="coerce").dt.date
        display["active"]           = display["active"].fillna(True).astype(bool)
        display["keywords_summary"] = display["keywords_summary"].fillna("").astype(str)

        id_list = display["id"].tolist()
        display = display.drop(columns=["id"])

        edited = st.data_editor(
            display,
            use_container_width=True,
            height=420,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "name":             st.column_config.TextColumn("Name", width="medium"),
                "window_label":     st.column_config.SelectboxColumn(
                    "Window", options=WINDOW_OPTIONS, width="medium",
                ),
                "deadline":         st.column_config.DateColumn(
                    "Deadline", width="small", format="YYYY-MM-DD",
                ),
                "active":           st.column_config.CheckboxColumn("Active", width="small"),
                "keywords_summary": st.column_config.TextColumn(
                    "Keywords", width="small", disabled=True,
                    help="Read-only here — edit the `keywords` JSON column in Supabase.",
                ),
            },
            key="clusters_editor",
        )

        if not edited.equals(display):
            diffs = []
            for idx in range(len(edited)):
                cid = id_list[idx]
                o, n = display.iloc[idx], edited.iloc[idx]
                patch = {}
                for col in ("name", "window_label", "deadline", "active"):
                    if _diff_value_changed(o[col], n[col]):
                        nv = n[col]
                        if col == "deadline" and isinstance(nv, (date, pd.Timestamp)):
                            patch[col] = pd.Timestamp(nv).date().isoformat()
                        else:
                            patch[col] = _cell_or_none(nv)
                if patch:
                    diffs.append((cid, patch))
            if diffs:
                for cid, patch in diffs:
                    try:
                        update_content_clusters(client, cid, patch)
                    except Exception as e:
                        st.warning(f"Failed to save cluster {cid}: {e}")
                st.success(f"Saved {len(diffs)} change(s).")
                st.cache_data.clear()
                st.rerun()

    # ── Delete a cluster ──────────────────────────────────────────────────────
    with st.expander("🗑 Delete a cluster"):
        if not rows:
            st.caption("Nothing to delete.")
        else:
            del_id = st.selectbox(
                "Pick a cluster to delete",
                options=[r["id"] for r in rows],
                format_func=lambda i: next((r["name"] for r in rows if r["id"] == i), "?"),
                key="del_cl_id",
            )
            if st.button("Delete this cluster", type="secondary", key="del_cl_btn"):
                try:
                    delete_content_clusters(client, del_id)
                    st.success("Deleted.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Tone Keywords
# ══════════════════════════════════════════════════════════════════════════════
with tab_tone:
    rows = _read_table(TONE_KEYWORDS_TABLE)
    total = len(rows)
    total_kw = sum(len(r.get("keyword_list") or []) for r in rows)

    cards = '<div class="stat-grid">'
    cards += _stat(total,    "Total tones",     COLORS["accent"])
    cards += _stat(total_kw, "Total keywords",  COLORS["evergreen"])
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Add a new tone ────────────────────────────────────────────────────────
    with st.expander("➕ Add a new tone"):
        c1, c2 = st.columns([1, 2])
        with c1:
            nt_tone = st.text_input("Tone", key="new_tone", placeholder="e.g. curiosity")
        with c2:
            nt_keywords = st.text_input(
                "Keywords (comma-separated)",
                key="new_tone_keywords",
                placeholder="e.g. wonder, discover, why, what if",
            )

        if st.button(
            "Add tone", type="primary",
            disabled=not nt_tone.strip(),
            key="add_tone_btn",
        ):
            try:
                add_tone_keywords(
                    client,
                    tone=nt_tone.strip(),
                    keyword_list=_csv_to_list(nt_keywords),
                )
                st.success(f"Added tone: {nt_tone.strip()}")
                _clear_keys(("new_tone", "new_tone_keywords"))
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Add failed: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Editable table ────────────────────────────────────────────────────────
    if not rows:
        st.info("No tones yet. Use the form above to add one.")
    else:
        df = pd.DataFrame(rows)
        for col in ("tone", "keyword_list"):
            if col not in df.columns:
                df[col] = None
        # Render the array as comma-separated text so it's edit-friendly.
        df["keyword_list_csv"] = df["keyword_list"].apply(_list_to_csv)
        display = df[["id", "tone", "keyword_list_csv"]].copy().reset_index(drop=True)
        display["tone"]             = display["tone"].fillna("").astype(str)
        display["keyword_list_csv"] = display["keyword_list_csv"].fillna("").astype(str)

        id_list = display["id"].tolist()
        display = display.drop(columns=["id"])

        edited = st.data_editor(
            display,
            use_container_width=True,
            height=420,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "tone":             st.column_config.TextColumn("Tone", width="small"),
                "keyword_list_csv": st.column_config.TextColumn(
                    "Keywords (comma-separated)", width="large",
                ),
            },
            key="tones_editor",
        )

        if not edited.equals(display):
            diffs = []
            for idx in range(len(edited)):
                tid = id_list[idx]
                o, n = display.iloc[idx], edited.iloc[idx]
                patch = {}
                if _diff_value_changed(o["tone"], n["tone"]):
                    patch["tone"] = _cell_or_none(n["tone"])
                if _diff_value_changed(o["keyword_list_csv"], n["keyword_list_csv"]):
                    patch["keyword_list"] = _csv_to_list(n["keyword_list_csv"])
                if patch:
                    diffs.append((tid, patch))
            if diffs:
                for tid, patch in diffs:
                    try:
                        update_tone_keywords(client, tid, patch)
                    except Exception as e:
                        st.warning(f"Failed to save tone {tid}: {e}")
                st.success(f"Saved {len(diffs)} change(s).")
                st.cache_data.clear()
                st.rerun()

    # ── Delete a tone ─────────────────────────────────────────────────────────
    with st.expander("🗑 Delete a tone"):
        if not rows:
            st.caption("Nothing to delete.")
        else:
            del_id = st.selectbox(
                "Pick a tone to delete",
                options=[r["id"] for r in rows],
                format_func=lambda i: next((r["tone"] for r in rows if r["id"] == i), "?"),
                key="del_tone_id",
            )
            if st.button("Delete this tone", type="secondary", key="del_tone_btn"):
                try:
                    delete_tone_keywords(client, del_id)
                    st.success("Deleted.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Delete failed: {e}")


st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    "Admin · Listn Intel · changes save instantly to Supabase</p>",
    unsafe_allow_html=True,
)
