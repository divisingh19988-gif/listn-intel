"""
Action Tracker — Supabase-backed CRUD over the `actions` table.

Layout:
  • 5 stat cards:  Total / Not Started / In Progress / Testing / Done
  • Filter row:    Source · Priority · Status · Week Added
  • Editable table (st.data_editor)
  • Auto-populate: if no rows for current ISO week, offer a one-click button
    that pulls the top 3 Meta playbook items + top 2 SEO posts due this week
    + top 2 AI readiness quick wins.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from lib.theme import inject_global_css, COLORS
from lib.data_freshness import show_freshness_banner
from lib.supabase_client import (
    get_client,
    is_configured as supabase_configured,
    list_actions,
    add_action,
    update_action,
    delete_action,
    has_actions_for_week,
    current_iso_week,
)
from lib.synthesis import SEO_CLUSTERS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Action Tracker · Listn", page_icon="✅", layout="wide")
inject_global_css()
show_freshness_banner()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<h1 style="margin-bottom:0.2rem;">✅ Action Tracker</h1>'
    f'<p class="muted" style="margin-top:0;">'
    "Live Supabase store. Status changes save instantly · "
    f"current ISO week: <strong>{current_iso_week()}</strong>"
    "</p>",
    unsafe_allow_html=True,
)

if not supabase_configured():
    st.error(
        "Supabase is not configured. Add `SUPABASE_URL` and `SUPABASE_KEY` to "
        "`.streamlit/secrets.toml` (or `.env`). The page will render once the "
        "credentials are in place."
    )
    st.stop()

client = get_client()
if client is None:
    st.error("Supabase package is installed but the client could not connect. Check your credentials.")
    st.stop()


# ── Auto-populate offer (only if no rows for this week) ───────────────────────
this_week = current_iso_week()


def _seed_actions() -> list[dict]:
    """3 Meta + 2 SEO + 2 AI = 7 actions."""
    seeds: list[dict] = []
    # 3 highest-priority Meta playbook items
    for title, prio in [
        ("Make the elder the hero of your adult-child-targeted ads", "HIGH"),
        ("Make voice the product, not the book",                     "HIGH"),
        ("Test grief-adjacent urgency with warmth",                  "HIGH"),
    ]:
        seeds.append({"source": "meta", "recommendation": title, "priority": prio})

    # 2 SEO posts: nearest-deadline cluster's top 2 KD<=10 keywords as "Publish post on …"
    today = date.today()
    dated = [c for c in SEO_CLUSTERS if c["deadline"] and c["deadline"] >= today]
    dated.sort(key=lambda c: c["deadline"])
    cluster = dated[0] if dated else SEO_CLUSTERS[0]
    candidates = [k for k in cluster["keywords"] if k[2] <= 10]
    if not candidates:
        candidates = list(cluster["keywords"])
    candidates.sort(key=lambda k: k[1], reverse=True)
    for kw, vol, kd in candidates[:2]:
        seeds.append({
            "source": "seo",
            "recommendation": f'Publish post targeting "{kw}" (vol {vol:,} · KD {kd}) — {cluster["name"]} cluster',
            "priority": "HIGH",
        })

    # 2 AI readiness quick wins
    for title in [
        "Add llms.txt to listn-app.com",
        "Allow GPTBot + ClaudeBot + PerplexityBot in robots.txt",
    ]:
        seeds.append({"source": "ai_readiness", "recommendation": title, "priority": "HIGH"})

    return seeds


if not has_actions_for_week(client, this_week):
    st.info(
        f"No actions for week **{this_week}** yet. "
        "Click below to auto-populate the top 7 actions from Meta, SEO, and AI Readiness."
    )
    if st.button("✨ Populate this week's actions", type="primary"):
        seeded = 0
        for s in _seed_actions():
            try:
                add_action(
                    client,
                    source=s["source"],
                    recommendation=s["recommendation"],
                    priority=s["priority"],
                    status="Not Started",
                    week_added=this_week,
                )
                seeded += 1
            except Exception as e:
                st.warning(f"Skipped one: {e}")
        st.success(f"Seeded {seeded} actions for {this_week}.")
        st.cache_data.clear()
        st.rerun()


# ── Load + render ─────────────────────────────────────────────────────────────
try:
    rows = list_actions(client)
except Exception as e:
    st.error(f"Failed to load actions from Supabase: {e}")
    st.stop()

df = pd.DataFrame(rows)


def _stat(value, label, color):
    return (
        '<div class="stat-card">'
        f'<div class="stat-value" style="color:{color};">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        '</div>'
    )


# 5 stat cards
total = len(df)
not_started = int((df.get("status") == "Not Started").sum()) if total else 0
in_progress = int((df.get("status") == "In Progress").sum()) if total else 0
testing     = int((df.get("status") == "Testing").sum()) if total else 0
done        = int((df.get("status") == "Done").sum()) if total else 0

cards_html = '<div class="stat-grid">'
cards_html += _stat(total,       "Total",       COLORS["accent"])
cards_html += _stat(not_started, "Not Started", COLORS["muted"])
cards_html += _stat(in_progress, "In Progress", COLORS["soon"])
cards_html += _stat(testing,     "Testing",     COLORS["accent"])
cards_html += _stat(done,        "Done",        COLORS["evergreen"])
cards_html += "</div>"
st.markdown(cards_html, unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)


# ── Filters ───────────────────────────────────────────────────────────────────
fc1, fc2, fc3, fc4 = st.columns(4)
with fc1:
    source_options = ["All"] + (sorted(df["source"].dropna().unique()) if total else [])
    source_filter = st.selectbox("Source", source_options)
with fc2:
    priority_options = ["All", "HIGH", "MEDIUM", "LOW"]
    priority_filter = st.selectbox("Priority", priority_options)
with fc3:
    status_options = ["All", "Not Started", "In Progress", "Testing", "Done"]
    status_filter = st.selectbox("Status", status_options)
with fc4:
    week_options = ["All"] + (sorted(df["week_added"].dropna().unique(), reverse=True) if total else [])
    week_filter = st.selectbox("Week added", week_options)

# Apply filters
mask = pd.Series([True] * len(df))
if total:
    if source_filter   != "All": mask &= df["source"]     == source_filter
    if priority_filter != "All": mask &= df["priority"]   == priority_filter
    if status_filter   != "All": mask &= df["status"]     == status_filter
    if week_filter     != "All": mask &= df["week_added"] == week_filter

filtered = df.loc[mask].copy() if total else df

# ── Add Action form ───────────────────────────────────────────────────────────
with st.expander("➕ Add a new action"):
    f1, f2 = st.columns([1, 2])
    with f1:
        new_source = st.selectbox(
            "Source",
            ["manual", "meta", "seo", "ai_readiness"],
            key="new_source",
        )
        new_priority = st.selectbox("Priority", ["HIGH", "MEDIUM", "LOW"], key="new_priority")
    with f2:
        new_rec = st.text_input("Recommendation", key="new_rec",
                                placeholder="e.g. Test wistful-urgency creative on Father's Day audience")
        new_notes = st.text_input("Notes (optional)", key="new_notes", placeholder="Anything to remember…")
    if st.button("Add action", type="primary", disabled=not new_rec.strip()):
        try:
            add_action(
                client,
                source=new_source,
                recommendation=new_rec.strip(),
                priority=new_priority,
                status="Not Started",
                notes=new_notes.strip(),
                week_added=this_week,
            )
            st.success("Added.")
            st.rerun()
        except Exception as e:
            st.error(f"Add failed: {e}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Editable table ────────────────────────────────────────────────────────────
if filtered.empty:
    st.info("No actions match the current filters.")
else:
    # Build a simplified editable view
    display = filtered[[
        "id", "source", "week_added", "recommendation",
        "priority", "status", "notes",
    ]].copy().reset_index(drop=True)
    display = display.sort_values(
        by=["priority", "week_added"],
        ascending=[True, False],
        key=lambda c: c.map({"HIGH": 0, "MEDIUM": 1, "LOW": 2}) if c.name == "priority" else c,
    )

    edited = st.data_editor(
        display,
        use_container_width=True,
        height=500,
        hide_index=True,
        num_rows="fixed",
        column_config={
            "id":             None,  # hide UUID
            "source":         st.column_config.TextColumn("Source", width="small", disabled=True),
            "week_added":     st.column_config.TextColumn("Week", width="small", disabled=True),
            "recommendation": st.column_config.TextColumn("Recommendation", width="large", disabled=True),
            "priority":       st.column_config.SelectboxColumn(
                "Priority", options=["HIGH", "MEDIUM", "LOW"], width="small",
            ),
            "status":         st.column_config.SelectboxColumn(
                "Status",
                options=["Not Started", "In Progress", "Testing", "Done"],
                width="medium",
            ),
            "notes":          st.column_config.TextColumn("Notes", width="large"),
        },
        key="actions_editor",
    )

    # Detect diffs and write back to Supabase
    if not edited.equals(display):
        diffs = []
        original = display.set_index("id")
        modified = edited.set_index("id")
        for action_id in modified.index:
            o = original.loc[action_id]
            n = modified.loc[action_id]
            patch = {}
            for col in ("priority", "status", "notes"):
                if o[col] != n[col]:
                    patch[col] = n[col]
            if patch:
                diffs.append((action_id, patch))
        if diffs:
            for action_id, patch in diffs:
                try:
                    update_action(client, action_id, patch)
                except Exception as e:
                    st.warning(f"Failed to save row {action_id}: {e}")
            st.success(f"Saved {len(diffs)} change(s).")
            st.rerun()

# ── Delete row controls (separate, less likely to misclick) ──────────────────
with st.expander("🗑 Delete an action"):
    if filtered.empty:
        st.caption("No actions in current filter.")
    else:
        delete_id = st.selectbox(
            "Pick an action to delete",
            options=filtered["id"].tolist(),
            format_func=lambda i: f"{i[:8]}… · {filtered.loc[filtered['id']==i, 'recommendation'].iloc[0][:80]}",
        )
        if st.button("Delete this action", type="secondary"):
            try:
                delete_action(client, delete_id)
                st.success("Deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")

st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    "Action Tracker · Listn · Supabase-backed</p>",
    unsafe_allow_html=True,
)
