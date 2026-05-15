"""
Admin — manage reference data + run the auto-discovery queue.

Tabs:
  1. Competitors    — CRUD, validation, usage stats, Claude enrich-on-add, soft-delete
  2. Content Clusters — CRUD, chip-style keyword editor, Claude keyword generator
  3. Tone Keywords  — CRUD, Claude tone expander grounded in recent ad copy
  4. Candidates     — auto-discovery queue (Approve / Reject / Snooze)
  5. Audit Log      — last 50 admin edits with actor + timestamp

All mutations write an audit row. All destructive actions are soft-delete with
restore (except tone_keywords, which has no soft-delete column today).
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime

import pandas as pd
import streamlit as st

from lib.theme import inject_global_css, inject_sidebar, COLORS
from lib.data_freshness import show_freshness_banner
from lib import admin_claude
from lib.dashboard_hygiene import run_hygiene_check, get_last_review
from lib.admin_validation import (
    validate_competitor,
    validate_cluster,
    validate_tone,
    clean_seo_domain,
)
from lib.admin_usage import competitor_usage_stats, lookup_usage, coverage_gaps
from lib.supabase_client import (
    get_client,
    is_configured as supabase_configured,
    COMPETITORS_TABLE,
    CONTENT_CLUSTERS_TABLE,
    TONE_KEYWORDS_TABLE,
    add_competitors,
    update_competitors,
    delete_competitors,
    restore_competitors,
    hard_delete_competitors,
    add_content_clusters,
    update_content_clusters,
    delete_content_clusters,
    restore_content_clusters,
    hard_delete_content_clusters,
    add_tone_keywords,
    update_tone_keywords,
    delete_tone_keywords,
    log_audit,
    list_audit,
    list_candidates,
    add_candidate,
    update_candidate,
    delete_candidate,
)

# ── Page chrome ───────────────────────────────────────────────────────────────
inject_global_css()
inject_sidebar()
show_freshness_banner()

st.markdown(
    '<h1 style="margin-bottom:0.2rem;">⚙️ Admin</h1>'
    '<p class="muted" style="margin-top:0;">'
    "Manage reference data without touching code. Edits save to Supabase, "
    "validate on the way in, and write an audit trail."
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


# ── Actor selector (drives audit log) ─────────────────────────────────────────
with st.sidebar:
    st.markdown("### Admin session")
    actor = st.selectbox(
        "Acting as",
        options=["Digvijay", "Eli", "Intel Dashboard", "Other"],
        key="admin_actor",
    )
    if actor == "Other":
        actor = st.text_input("Name", value="", key="admin_actor_custom").strip() or "Unknown"
    claude_ready = admin_claude.is_configured()
    st.caption(
        f"Claude: {'🟢 ready' if claude_ready else '⚪️ no API key'}"
    )

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


def _read_table(table_name: str, include_deleted: bool = True) -> list[dict]:
    """Read every row so admin can re-activate / restore. Newest first."""
    try:
        q = client.table(table_name).select("*").order("created_at", desc=True)
        resp = q.execute()
        rows = resp.data or []
        if not include_deleted:
            rows = [r for r in rows if not r.get("deleted_at")]
        return rows
    except Exception as e:
        st.error(f"Failed to load `{table_name}`: {e}")
        return []


def _clear_keys(keys) -> None:
    for k in keys:
        st.session_state.pop(k, None)


def _diff_value_changed(ov, nv) -> bool:
    if pd.isna(ov) and pd.isna(nv):
        return False
    return ov != nv


def _cell_or_none(v):
    return None if pd.isna(v) else v


def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _normalize_keywords(raw) -> list[str]:
    """
    The keywords column has drifted across seed scripts — accept any of:
      - ['phrase', 'phrase']
      - [['phrase', 'TAG'], ...]
      - [{'phrase': 'phrase', ...}, ...]
    and return a clean list[str].
    """
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        if isinstance(item, str):
            s = item.strip()
        elif isinstance(item, (list, tuple)) and item:
            s = str(item[0]).strip()
        elif isinstance(item, dict):
            s = str(item.get("phrase") or item.get("keyword") or "").strip()
        else:
            s = ""
        if s:
            out.append(s)
    return out


def _ad_copy_corpus(limit: int = 40) -> list[str]:
    """Pull a sample of recent ad copy to ground the tone expander."""
    try:
        from lib.admin_usage import ADS_FILE_LATEST
        if not ADS_FILE_LATEST.exists():
            return []
        with ADS_FILE_LATEST.open() as f:
            data = json.load(f)
        out = []
        for ads in (data.get("competitors") or {}).values():
            if not isinstance(ads, list):
                continue
            for a in ads[:10]:
                copy = (a.get("ad_copy") or a.get("ad_creative_body") or "").strip()
                if copy:
                    out.append(copy)
                if len(out) >= limit:
                    return out
        return out
    except Exception:
        return []


# ── Coverage gaps panel (top-of-page nag) ─────────────────────────────────────
all_competitors = _read_table(COMPETITORS_TABLE, include_deleted=False)
all_clusters = _read_table(CONTENT_CLUSTERS_TABLE, include_deleted=False)
all_tones = _read_table(TONE_KEYWORDS_TABLE, include_deleted=False)
gaps = coverage_gaps(
    competitors=all_competitors, clusters=all_clusters, tones=all_tones
)
total_gaps = sum(len(v) for v in gaps.values())
if total_gaps:
    with st.expander(f"⚠️ Coverage gaps ({total_gaps})", expanded=False):
        labels = {
            "competitors_missing_domain": "Active competitors with no SEO domain",
            "competitors_missing_terms": "Active competitors with no Meta search terms",
            "clusters_empty_keywords": "Active clusters with zero keywords",
            "clusters_past_deadline_active": "Active clusters past their deadline",
            "tones_thin_keywords": "Tones with fewer than 3 keywords",
        }
        for key, items in gaps.items():
            if not items:
                continue
            st.markdown(f"**{labels[key]}** — {len(items)}")
            st.caption(", ".join(items[:20]) + (" …" if len(items) > 20 else ""))

# ── Dashboard hygiene (Claude-powered review) ────────────────────────────────
_SEVERITY_EMOJI = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

_last_review = get_last_review()
_review_label = "🔍 Dashboard hygiene"
if _last_review:
    _n = len(_last_review.get("findings", []))
    _review_label += f" ({_n} finding{'s' if _n != 1 else ''} · last run {_last_review['reviewed_at'][:10]})"
with st.expander(_review_label, expanded=False):
    st.caption(
        "Claude reviews the dashboard for issues a deterministic rule can't catch — "
        "wrong dates baked into data, placeholders left in production, contradictions "
        "between sections, methodology markers older than they should be."
    )
    col_run, col_status = st.columns([1, 3])
    with col_run:
        run_clicked = st.button("Run review", key="run_hygiene", type="primary")
    with col_status:
        if not os.getenv("ANTHROPIC_API_KEY"):
            st.warning("Set ANTHROPIC_API_KEY in .env to enable.")
        elif _last_review:
            usage = _last_review.get("usage") or {}
            in_tok = usage.get("input_tokens") or 0
            out_tok = usage.get("output_tokens") or 0
            st.caption(f"Last run used {in_tok:,} input + {out_tok:,} output tokens.")

    if run_clicked:
        with st.spinner("Reviewing dashboard with Claude (this takes ~15-30s)..."):
            try:
                _last_review = run_hygiene_check()
                st.success(f"Review complete — {len(_last_review['findings'])} findings.")
            except Exception as _exc:
                st.error(f"Review failed: {_exc}")
                _last_review = get_last_review()

    _findings = (_last_review or {}).get("findings", [])
    if _findings:
        _sorted = sorted(_findings, key=lambda f: _SEVERITY_ORDER.get(f.get("severity"), 99))
        for f in _sorted:
            sev = f.get("severity", "low")
            emoji = _SEVERITY_EMOJI.get(sev, "ℹ️")
            st.markdown(f"#### {emoji} {f.get('title','(no title)')}")
            meta_bits = [sev.upper(), f.get("category", "other")]
            loc = f.get("location")
            if loc:
                meta_bits.append(f"location: {loc}")
            st.caption(" · ".join(meta_bits))
            st.markdown(f.get("details", ""))
            fix = f.get("suggested_fix")
            if fix and fix.strip().lower() not in ("none", "n/a", ""):
                st.markdown(f"**Fix:** {fix}")
    elif _last_review:
        st.info("No issues found in the last review — dashboard looks clean.")
    else:
        st.info("No review on file. Click **Run review** to ask Claude.")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_comp, tab_cluster, tab_tone, tab_cand, tab_audit = st.tabs(
    ["🏢 Competitors", "📅 Content Clusters", "🎭 Tone Keywords", "🔍 Candidates", "📜 Audit Log"]
)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Competitors
# ══════════════════════════════════════════════════════════════════════════════
with tab_comp:
    rows = _read_table(COMPETITORS_TABLE, include_deleted=True)
    active_rows = [r for r in rows if not r.get("deleted_at")]
    deleted_rows = [r for r in rows if r.get("deleted_at")]
    active_on = sum(1 for r in active_rows if r.get("active"))

    usage = competitor_usage_stats()

    cards = '<div class="stat-grid">'
    cards += _stat(len(active_rows), "Tracked", COLORS["accent"])
    cards += _stat(active_on, "Active", COLORS["evergreen"])
    cards += _stat(len(active_rows) - active_on, "Paused", COLORS["muted"])
    cards += _stat(len(deleted_rows), "Trash", COLORS["urgent"])
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Add a competitor (with Claude enrich) ─────────────────────────────────
    with st.expander("➕ Add a competitor", expanded=False):
        c1, c2 = st.columns([2, 1])
        with c1:
            new_name = st.text_input("Name", key="new_comp_name", placeholder="e.g. Storyteller")
        with c2:
            enrich_btn = st.button(
                "✨ Enrich with Claude",
                disabled=not (claude_ready and new_name.strip()),
                key="enrich_comp_btn",
                help="Claude proposes domain, App Store ID, search terms, and notes from just the name.",
            )

        if enrich_btn:
            with st.spinner("Asking Claude…"):
                enriched = admin_claude.enrich_competitor(new_name.strip())
            if not enriched.get("ok"):
                st.error(enriched.get("error") or "Enrichment failed.")
            else:
                if not enriched.get("is_competitor"):
                    st.warning(
                        f"Claude is not confident this is a Listn competitor "
                        f"(confidence {enriched.get('confidence', 0):.0%}). "
                        f"{enriched.get('notes', '')}"
                    )
                st.session_state["new_comp_seo"] = enriched.get("seo_domain") or ""
                st.session_state["new_comp_appstore"] = enriched.get("appstore_id") or ""
                st.session_state["new_comp_terms"] = ", ".join(enriched.get("meta_search_terms") or [])
                st.session_state["new_comp_notes"] = enriched.get("notes") or ""
                st.success(
                    f"Pre-filled from Claude (confidence {enriched.get('confidence', 0):.0%}). "
                    "Review and click Add."
                )

        cc1, cc2 = st.columns(2)
        with cc1:
            new_seo = st.text_input("SEO domain", key="new_comp_seo", placeholder="example.com")
            new_appstore = st.text_input("App Store ID", key="new_comp_appstore", placeholder="optional, digits only")
        with cc2:
            new_terms = st.text_input(
                "Meta search terms (comma-separated)",
                key="new_comp_terms",
                placeholder="e.g. Storyteller, StoryTeller App",
            )
            new_notes = st.text_input("Notes", key="new_comp_notes", placeholder="optional")
            new_active = st.checkbox("Active", value=True, key="new_comp_active")

        if st.button(
            "Add competitor", type="primary",
            disabled=not (new_name or "").strip(),
            key="add_comp_btn",
        ):
            terms_list = _csv_to_list(new_terms)
            ok, errors, warnings = validate_competitor(
                name=new_name,
                seo_domain=new_seo,
                appstore_id=new_appstore,
                meta_search_terms=terms_list,
                existing_names=[r.get("name", "") for r in rows],
            )
            for w in warnings:
                st.warning(w)
            if not ok:
                for e in errors:
                    st.error(e)
            else:
                try:
                    inserted = add_competitors(
                        client,
                        name=new_name.strip(),
                        meta_search_terms=terms_list,
                        seo_domain=clean_seo_domain(new_seo),
                        appstore_id=(new_appstore or "").strip() or None,
                        active=bool(new_active),
                        notes=(new_notes or "").strip() or None,
                    )
                    log_audit(
                        client,
                        table_name=COMPETITORS_TABLE,
                        action="insert",
                        row_id=str(inserted.get("id")) if isinstance(inserted, dict) else None,
                        row_label=new_name.strip(),
                        new_value=json.dumps({k: inserted.get(k) for k in ("name", "seo_domain", "appstore_id", "active")} if isinstance(inserted, dict) else {}),
                        actor=actor,
                    )
                    st.success(f"Added competitor: {new_name.strip()}")
                    _clear_keys(("new_comp_name", "new_comp_seo", "new_comp_appstore",
                                 "new_comp_terms", "new_comp_notes", "new_comp_active"))
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Add failed: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Editable table with usage stats ───────────────────────────────────────
    if not active_rows:
        st.info("No competitors yet. Use the form above to add one.")
    else:
        df = pd.DataFrame(active_rows)
        for col in ("name", "seo_domain", "appstore_id", "active", "notes"):
            if col not in df.columns:
                df[col] = None

        # Enrich with usage stats columns
        df["ads_7d"] = df["name"].apply(lambda n: lookup_usage(usage, n).get("ads_7d", 0))
        df["last_scrape"] = df["name"].apply(lambda n: lookup_usage(usage, n).get("last_scrape") or "—")

        display = df[[
            "id", "name", "seo_domain", "appstore_id", "active",
            "ads_7d", "last_scrape", "notes",
        ]].copy().reset_index(drop=True)
        display["name"]        = display["name"].fillna("").astype(str)
        display["seo_domain"]  = display["seo_domain"].fillna("").astype(str)
        display["appstore_id"] = display["appstore_id"].fillna("").astype(str)
        display["active"]      = display["active"].fillna(True).astype(bool)
        display["notes"]       = display["notes"].fillna("").astype(str)
        display["last_scrape"] = display["last_scrape"].fillna("—").astype(str)

        id_list = display["id"].tolist()
        name_list = display["name"].tolist()
        display = display.drop(columns=["id"])

        edited = st.data_editor(
            display,
            use_container_width=True,
            height=460,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "name":        st.column_config.TextColumn("Name", width="medium", disabled=True),
                "seo_domain":  st.column_config.TextColumn("SEO domain", width="medium"),
                "appstore_id": st.column_config.TextColumn("App Store ID", width="small"),
                "active":      st.column_config.CheckboxColumn("Active", width="small"),
                "ads_7d":      st.column_config.NumberColumn("Ads (7d)", width="small", disabled=True, help="From data/ads_scraped_latest.json"),
                "last_scrape": st.column_config.TextColumn("Last scrape", width="small", disabled=True),
                "notes":       st.column_config.TextColumn("Notes", width="large"),
            },
            key="competitors_editor",
        )

        # Diff preview + apply
        if not edited.equals(display):
            diffs = []
            for idx in range(len(edited)):
                cid = id_list[idx]
                label = name_list[idx]
                o, n = display.iloc[idx], edited.iloc[idx]
                patch = {}
                changed_fields = {}
                for col in ("seo_domain", "appstore_id", "active", "notes"):
                    if _diff_value_changed(o[col], n[col]):
                        nv = _cell_or_none(n[col])
                        if col == "seo_domain":
                            nv = clean_seo_domain(nv) if nv else None
                        patch[col] = nv
                        changed_fields[col] = (o[col], n[col])
                if patch:
                    diffs.append((cid, label, patch, changed_fields))
            if diffs:
                st.markdown(f"**{len(diffs)} row(s) changed — review before saving:**")
                with st.container(border=True):
                    for cid, label, patch, fields in diffs:
                        bullets = ", ".join(
                            f"`{f}`: {o!r} → {n!r}" for f, (o, n) in fields.items()
                        )
                        st.markdown(f"- **{label}** — {bullets}")
                c_apply, c_cancel = st.columns([1, 1])
                with c_apply:
                    if st.button(f"✅ Save {len(diffs)} change(s)", type="primary", key="apply_comp_diffs"):
                        applied = 0
                        for cid, label, patch, fields in diffs:
                            try:
                                update_competitors(client, cid, patch)
                                for f, (old, new) in fields.items():
                                    log_audit(
                                        client,
                                        table_name=COMPETITORS_TABLE,
                                        action="update",
                                        row_id=str(cid),
                                        row_label=label,
                                        field=f,
                                        old_value=str(old),
                                        new_value=str(new),
                                        actor=actor,
                                    )
                                applied += 1
                            except Exception as e:
                                st.warning(f"Failed to save {label}: {e}")
                        st.success(f"Saved {applied} change(s).")
                        st.cache_data.clear()
                        st.rerun()
                with c_cancel:
                    if st.button("Discard", key="discard_comp_diffs"):
                        st.rerun()

        # CSV export
        export_df = pd.DataFrame(active_rows)[["name", "seo_domain", "appstore_id", "active", "meta_search_terms", "notes"]]
        st.download_button(
            "⬇ Export competitors CSV",
            _df_to_csv_bytes(export_df),
            file_name=f"competitors_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="export_comp_csv",
        )

    # ── Soft-delete + restore ─────────────────────────────────────────────────
    cd1, cd2 = st.columns(2)
    with cd1:
        with st.expander("🗑 Move a competitor to trash (soft delete)"):
            if not active_rows:
                st.caption("Nothing to delete.")
            else:
                del_id = st.selectbox(
                    "Pick a competitor",
                    options=[r["id"] for r in active_rows],
                    format_func=lambda i: next((r["name"] for r in active_rows if r["id"] == i), "?"),
                    key="del_comp_id",
                )
                if st.button("Move to trash", type="secondary", key="del_comp_btn"):
                    try:
                        label = next((r["name"] for r in active_rows if r["id"] == del_id), "?")
                        delete_competitors(client, del_id)
                        log_audit(
                            client,
                            table_name=COMPETITORS_TABLE,
                            action="delete",
                            row_id=str(del_id),
                            row_label=label,
                            actor=actor,
                        )
                        st.success("Moved to trash. Restore from the panel on the right.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete failed: {e}")
    with cd2:
        with st.expander(f"♻️ Restore from trash ({len(deleted_rows)})"):
            if not deleted_rows:
                st.caption("Trash is empty.")
            else:
                restore_id = st.selectbox(
                    "Pick a deleted competitor",
                    options=[r["id"] for r in deleted_rows],
                    format_func=lambda i: next((r["name"] for r in deleted_rows if r["id"] == i), "?"),
                    key="restore_comp_id",
                )
                rc1, rc2 = st.columns(2)
                with rc1:
                    if st.button("Restore", type="primary", key="restore_comp_btn"):
                        label = next((r["name"] for r in deleted_rows if r["id"] == restore_id), "?")
                        try:
                            restore_competitors(client, restore_id)
                            log_audit(
                                client,
                                table_name=COMPETITORS_TABLE,
                                action="restore",
                                row_id=str(restore_id),
                                row_label=label,
                                actor=actor,
                            )
                            st.success(f"Restored: {label}")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Restore failed: {e}")
                with rc2:
                    if st.button("Permanently delete", type="secondary", key="hard_del_comp_btn"):
                        label = next((r["name"] for r in deleted_rows if r["id"] == restore_id), "?")
                        try:
                            hard_delete_competitors(client, restore_id)
                            log_audit(
                                client,
                                table_name=COMPETITORS_TABLE,
                                action="hard_delete",
                                row_id=str(restore_id),
                                row_label=label,
                                actor=actor,
                            )
                            st.success(f"Permanently deleted: {label}")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hard delete failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Content Clusters (with chip-style keyword editor + Claude generator)
# ══════════════════════════════════════════════════════════════════════════════
with tab_cluster:
    rows = _read_table(CONTENT_CLUSTERS_TABLE, include_deleted=True)
    active_rows = [r for r in rows if not r.get("deleted_at")]
    deleted_rows = [r for r in rows if r.get("deleted_at")]
    active_on = sum(1 for r in active_rows if r.get("active"))
    total_kw = sum(len(_normalize_keywords(r.get("keywords"))) for r in active_rows)

    cards = '<div class="stat-grid">'
    cards += _stat(len(active_rows), "Tracked", COLORS["accent"])
    cards += _stat(active_on, "Active", COLORS["evergreen"])
    cards += _stat(total_kw, "Keywords", COLORS["accent"])
    cards += _stat(len(deleted_rows), "Trash", COLORS["urgent"])
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Add a cluster ─────────────────────────────────────────────────────────
    with st.expander("➕ Add a cluster", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            nc_name = st.text_input("Name", key="new_cl_name", placeholder="e.g. Mother's Day")
            nc_window = st.selectbox("Window", WINDOW_OPTIONS, key="new_cl_window")
        with c2:
            nc_deadline = st.date_input("Deadline (optional)", value=None, key="new_cl_deadline")
            nc_active = st.checkbox("Active", value=True, key="new_cl_active")
        nc_keywords_text = st.text_area(
            "Keywords (one per line)",
            key="new_cl_keywords",
            placeholder="mother's day gift ideas\nmemory gift for mom\n…",
            height=120,
        )
        gen_btn = st.button(
            "✨ Suggest keywords with Claude",
            disabled=not (claude_ready and (nc_name or "").strip()),
            key="gen_cl_kw",
            help="Claude proposes 15 keywords with intent + competition labels.",
        )
        if gen_btn:
            with st.spinner("Asking Claude…"):
                gen = admin_claude.suggest_cluster_keywords(nc_name, existing=_csv_to_list(nc_keywords_text.replace("\n", ",")))
            if not gen.get("ok"):
                st.error(gen.get("error") or "Suggestion failed.")
            else:
                st.session_state["_new_cl_suggestions"] = gen["keywords"]

        suggestions = st.session_state.get("_new_cl_suggestions") or []
        if suggestions:
            st.caption(f"Claude proposed {len(suggestions)} keywords — pick the ones to add:")
            picks = []
            for i, kw in enumerate(suggestions):
                label = f"{kw['phrase']}  ·  {kw.get('intent','?')}  ·  {kw.get('estimated_competition','?')}  — {kw.get('rationale','')}"
                if st.checkbox(label, value=True, key=f"_pick_cl_{i}"):
                    picks.append(kw["phrase"])
            if st.button("Append picked keywords to text box", key="append_cl_kw"):
                current = [k.strip() for k in (nc_keywords_text or "").splitlines() if k.strip()]
                merged = current + [p for p in picks if p not in current]
                st.session_state["new_cl_keywords"] = "\n".join(merged)
                st.session_state.pop("_new_cl_suggestions", None)
                st.rerun()

        if st.button(
            "Add cluster", type="primary",
            disabled=not (nc_name or "").strip(),
            key="add_cl_btn",
        ):
            kw_list = [k.strip() for k in (nc_keywords_text or "").splitlines() if k.strip()]
            ok, errors, warnings = validate_cluster(
                name=nc_name,
                window_label=nc_window,
                keywords=kw_list,
                existing_names=[r.get("name", "") for r in rows],
            )
            for w in warnings:
                st.warning(w)
            if not ok:
                for e in errors:
                    st.error(e)
            else:
                try:
                    inserted = add_content_clusters(
                        client,
                        name=nc_name.strip(),
                        window_label=nc_window,
                        deadline=nc_deadline.isoformat() if nc_deadline else None,
                        active=bool(nc_active),
                        keywords=kw_list,
                    )
                    log_audit(
                        client,
                        table_name=CONTENT_CLUSTERS_TABLE,
                        action="insert",
                        row_id=str(inserted.get("id")) if isinstance(inserted, dict) else None,
                        row_label=nc_name.strip(),
                        new_value=json.dumps({"window_label": nc_window, "keywords_count": len(kw_list)}),
                        actor=actor,
                    )
                    st.success(f"Added cluster: {nc_name.strip()} ({len(kw_list)} keywords)")
                    _clear_keys(("new_cl_name", "new_cl_window", "new_cl_deadline",
                                 "new_cl_active", "new_cl_keywords", "_new_cl_suggestions"))
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Add failed: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Per-cluster row with chip-style keyword editor ────────────────────────
    if not active_rows:
        st.info("No content clusters yet.")
    else:
        for cl in active_rows:
            cid = cl.get("id")
            name = cl.get("name") or "?"
            kw_list = _normalize_keywords(cl.get("keywords"))
            window_lbl = cl.get("window_label") or "EVERGREEN"
            deadline_val = cl.get("deadline")
            active_val = bool(cl.get("active", True))

            with st.container(border=True):
                hdr1, hdr2, hdr3, hdr4 = st.columns([3, 2, 2, 1])
                with hdr1:
                    st.markdown(f"**{name}**")
                    st.caption(f"{len(kw_list)} keywords")
                with hdr2:
                    new_window = st.selectbox(
                        "Window", WINDOW_OPTIONS,
                        index=WINDOW_OPTIONS.index(window_lbl) if window_lbl in WINDOW_OPTIONS else 2,
                        key=f"cl_win_{cid}",
                    )
                with hdr3:
                    dl_parsed = None
                    if deadline_val:
                        try:
                            dl_parsed = datetime.fromisoformat(str(deadline_val)[:10]).date()
                        except Exception:
                            dl_parsed = None
                    new_deadline = st.date_input(
                        "Deadline", value=dl_parsed, key=f"cl_dl_{cid}"
                    )
                with hdr4:
                    new_active = st.checkbox("Active", value=active_val, key=f"cl_act_{cid}")

                kw_text = st.text_area(
                    "Keywords (one per line)",
                    value="\n".join(kw_list),
                    key=f"cl_kw_{cid}",
                    height=120,
                )

                bc1, bc2, bc3 = st.columns([1, 1, 1])
                with bc1:
                    if st.button("💾 Save", key=f"cl_save_{cid}", type="primary"):
                        new_kw = [k.strip() for k in kw_text.splitlines() if k.strip()]
                        patch, changes = {}, {}
                        if new_window != window_lbl:
                            patch["window_label"] = new_window
                            changes["window_label"] = (window_lbl, new_window)
                        new_dl_iso = new_deadline.isoformat() if new_deadline else None
                        old_dl_iso = str(deadline_val)[:10] if deadline_val else None
                        if new_dl_iso != old_dl_iso:
                            patch["deadline"] = new_dl_iso
                            changes["deadline"] = (old_dl_iso, new_dl_iso)
                        if new_active != active_val:
                            patch["active"] = new_active
                            changes["active"] = (active_val, new_active)
                        if new_kw != kw_list:
                            patch["keywords"] = new_kw
                            changes["keywords"] = (f"{len(kw_list)} kws", f"{len(new_kw)} kws")
                        if not patch:
                            st.info("No changes.")
                        else:
                            try:
                                update_content_clusters(client, cid, patch)
                                for f, (old, new) in changes.items():
                                    log_audit(
                                        client,
                                        table_name=CONTENT_CLUSTERS_TABLE,
                                        action="update",
                                        row_id=str(cid),
                                        row_label=name,
                                        field=f,
                                        old_value=str(old),
                                        new_value=str(new),
                                        actor=actor,
                                    )
                                st.success("Saved.")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Save failed: {e}")
                with bc2:
                    if st.button("✨ Suggest more keywords", key=f"cl_gen_{cid}", disabled=not claude_ready):
                        with st.spinner("Asking Claude…"):
                            g = admin_claude.suggest_cluster_keywords(name, existing=kw_list)
                        if not g.get("ok"):
                            st.error(g.get("error") or "Suggestion failed.")
                        else:
                            st.session_state[f"_cl_sugg_{cid}"] = g["keywords"]
                with bc3:
                    if st.button("🗑 Move to trash", key=f"cl_del_{cid}"):
                        try:
                            delete_content_clusters(client, cid)
                            log_audit(
                                client, table_name=CONTENT_CLUSTERS_TABLE, action="delete",
                                row_id=str(cid), row_label=name, actor=actor,
                            )
                            st.success(f"Deleted {name}.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")

                sugg = st.session_state.get(f"_cl_sugg_{cid}") or []
                if sugg:
                    st.caption(f"Claude proposed {len(sugg)} additions — accept to append:")
                    accepted = []
                    for i, kw in enumerate(sugg):
                        label = f"{kw['phrase']}  ·  {kw.get('intent','?')}  ·  {kw.get('estimated_competition','?')}"
                        if st.checkbox(label, value=True, key=f"_accept_cl_{cid}_{i}"):
                            accepted.append(kw["phrase"])
                    a1, a2 = st.columns(2)
                    with a1:
                        if st.button("Append to keyword list", key=f"_apply_sugg_{cid}"):
                            current = [k.strip() for k in kw_text.splitlines() if k.strip()]
                            merged = current + [p for p in accepted if p not in current]
                            st.session_state[f"cl_kw_{cid}"] = "\n".join(merged)
                            st.session_state.pop(f"_cl_sugg_{cid}", None)
                            st.rerun()
                    with a2:
                        if st.button("Dismiss suggestions", key=f"_dismiss_sugg_{cid}"):
                            st.session_state.pop(f"_cl_sugg_{cid}", None)
                            st.rerun()

        # CSV export
        export_rows = []
        for r in active_rows:
            export_rows.append({
                "name": r.get("name"),
                "window_label": r.get("window_label"),
                "deadline": r.get("deadline"),
                "active": r.get("active"),
                "keywords": ", ".join(_normalize_keywords(r.get("keywords"))),
            })
        st.download_button(
            "⬇ Export clusters CSV",
            _df_to_csv_bytes(pd.DataFrame(export_rows)),
            file_name=f"content_clusters_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="export_cl_csv",
        )

    # ── Restore panel ─────────────────────────────────────────────────────────
    if deleted_rows:
        with st.expander(f"♻️ Restore from trash ({len(deleted_rows)})"):
            rid = st.selectbox(
                "Pick a deleted cluster",
                options=[r["id"] for r in deleted_rows],
                format_func=lambda i: next((r["name"] for r in deleted_rows if r["id"] == i), "?"),
                key="restore_cl_id",
            )
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("Restore", type="primary", key="restore_cl_btn"):
                    label = next((r["name"] for r in deleted_rows if r["id"] == rid), "?")
                    try:
                        restore_content_clusters(client, rid)
                        log_audit(client, table_name=CONTENT_CLUSTERS_TABLE, action="restore",
                                  row_id=str(rid), row_label=label, actor=actor)
                        st.success(f"Restored: {label}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Restore failed: {e}")
            with rc2:
                if st.button("Permanently delete", type="secondary", key="hard_del_cl_btn"):
                    label = next((r["name"] for r in deleted_rows if r["id"] == rid), "?")
                    try:
                        hard_delete_content_clusters(client, rid)
                        log_audit(client, table_name=CONTENT_CLUSTERS_TABLE, action="hard_delete",
                                  row_id=str(rid), row_label=label, actor=actor)
                        st.success(f"Permanently deleted: {label}")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hard delete failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Tone Keywords (with Claude expander grounded in ad copy)
# ══════════════════════════════════════════════════════════════════════════════
with tab_tone:
    rows = _read_table(TONE_KEYWORDS_TABLE)
    total = len(rows)
    total_kw = sum(len(r.get("keyword_list") or []) for r in rows)

    cards = '<div class="stat-grid">'
    cards += _stat(total, "Total tones", COLORS["accent"])
    cards += _stat(total_kw, "Total keywords", COLORS["evergreen"])
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Add a tone ────────────────────────────────────────────────────────────
    with st.expander("➕ Add a tone", expanded=False):
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
            disabled=not (nt_tone or "").strip(),
            key="add_tone_btn",
        ):
            kw_list = _csv_to_list(nt_keywords)
            ok, errors, warnings = validate_tone(
                tone=nt_tone,
                keyword_list=kw_list,
                existing_tones=[r.get("tone", "") for r in rows],
            )
            for w in warnings:
                st.warning(w)
            if not ok:
                for e in errors:
                    st.error(e)
            else:
                try:
                    inserted = add_tone_keywords(
                        client,
                        tone=nt_tone.strip(),
                        keyword_list=kw_list,
                    )
                    log_audit(
                        client, table_name=TONE_KEYWORDS_TABLE, action="insert",
                        row_id=str(inserted.get("id")) if isinstance(inserted, dict) else None,
                        row_label=nt_tone.strip(),
                        new_value=json.dumps({"keyword_count": len(kw_list)}),
                        actor=actor,
                    )
                    st.success(f"Added tone: {nt_tone.strip()}")
                    _clear_keys(("new_tone", "new_tone_keywords"))
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Add failed: {e}")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Per-tone row with Claude expander ─────────────────────────────────────
    if not rows:
        st.info("No tones yet.")
    else:
        corpus = _ad_copy_corpus(40)
        for t in rows:
            tid = t.get("id")
            tone = t.get("tone") or "?"
            kw_list = t.get("keyword_list") if isinstance(t.get("keyword_list"), list) else []

            with st.container(border=True):
                hdr1, hdr2 = st.columns([3, 1])
                with hdr1:
                    st.markdown(f"**{tone}**")
                    st.caption(f"{len(kw_list)} keywords")
                with hdr2:
                    expand_btn = st.button(
                        "✨ Expand with Claude",
                        disabled=not claude_ready,
                        key=f"tone_exp_{tid}",
                        help="Reads recent competitor ad copy and proposes new tone keywords grounded in it.",
                    )

                kw_csv = st.text_input(
                    "Keywords (comma-separated)",
                    value=", ".join(kw_list),
                    key=f"tone_kw_{tid}",
                )

                if expand_btn:
                    with st.spinner("Asking Claude…"):
                        ex = admin_claude.expand_tone_keywords(
                            tone, existing=kw_list, ad_copy_corpus=corpus, n=10,
                        )
                    if not ex.get("ok"):
                        st.error(ex.get("error") or "Expansion failed.")
                    else:
                        st.session_state[f"_tone_sugg_{tid}"] = ex["phrases"]

                sugg = st.session_state.get(f"_tone_sugg_{tid}") or []
                if sugg:
                    st.caption(f"Claude proposed {len(sugg)} additions:")
                    accepted = []
                    for i, kw in enumerate(sugg):
                        flag = "🔗 grounded" if kw.get("grounded") else "💭 inferred"
                        ex_snip = f" — _{kw['example'][:70]}…_" if kw.get("example") else ""
                        if st.checkbox(f"`{kw['phrase']}`  {flag}{ex_snip}", value=kw.get("grounded", False), key=f"_t_accept_{tid}_{i}"):
                            accepted.append(kw["phrase"])
                    a1, a2 = st.columns(2)
                    with a1:
                        if st.button("Append to keyword list", key=f"_t_apply_{tid}"):
                            current = _csv_to_list(kw_csv)
                            merged = current + [p for p in accepted if p not in current]
                            st.session_state[f"tone_kw_{tid}"] = ", ".join(merged)
                            st.session_state.pop(f"_tone_sugg_{tid}", None)
                            st.rerun()
                    with a2:
                        if st.button("Dismiss", key=f"_t_dismiss_{tid}"):
                            st.session_state.pop(f"_tone_sugg_{tid}", None)
                            st.rerun()

                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("💾 Save", key=f"tone_save_{tid}", type="primary"):
                        new_kw = _csv_to_list(kw_csv)
                        if new_kw != kw_list:
                            try:
                                update_tone_keywords(client, tid, {"keyword_list": new_kw})
                                log_audit(
                                    client, table_name=TONE_KEYWORDS_TABLE, action="update",
                                    row_id=str(tid), row_label=tone, field="keyword_list",
                                    old_value=f"{len(kw_list)} kws", new_value=f"{len(new_kw)} kws",
                                    actor=actor,
                                )
                                st.success("Saved.")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Save failed: {e}")
                        else:
                            st.info("No changes.")
                with bc2:
                    if st.button("🗑 Delete", key=f"tone_del_{tid}"):
                        try:
                            delete_tone_keywords(client, tid)
                            log_audit(
                                client, table_name=TONE_KEYWORDS_TABLE, action="hard_delete",
                                row_id=str(tid), row_label=tone, actor=actor,
                            )
                            st.success(f"Deleted {tone}.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete failed: {e}")

        # CSV export
        export_rows = [{"tone": r.get("tone"),
                        "keyword_list": ", ".join(r.get("keyword_list") or []) if isinstance(r.get("keyword_list"), list) else ""}
                       for r in rows]
        st.download_button(
            "⬇ Export tones CSV",
            _df_to_csv_bytes(pd.DataFrame(export_rows)),
            file_name=f"tone_keywords_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="export_tone_csv",
        )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Candidates queue
# ══════════════════════════════════════════════════════════════════════════════
with tab_cand:
    pending = list_candidates(client, status="pending")
    snoozed = list_candidates(client, status="snoozed")
    all_competitors_names = [r.get("name", "") for r in all_competitors]

    cards = '<div class="stat-grid">'
    cards += _stat(len(pending), "Pending review", COLORS["accent"])
    cards += _stat(len(snoozed), "Snoozed", COLORS["soon"])
    cards += "</div>"
    st.markdown(cards, unsafe_allow_html=True)
    st.markdown("<hr>", unsafe_allow_html=True)

    # ── Discover with Claude ──────────────────────────────────────────────────
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown(
            "**Auto-discovery** — Claude reads our current competitor list and "
            "the Listn product context, then proposes brands we should consider "
            "tracking. Each proposal lands here for Approve / Reject / Snooze."
        )
    with c2:
        if st.button(
            "🔎 Discover with Claude",
            disabled=not claude_ready,
            type="primary",
            key="discover_btn",
        ):
            with st.spinner("Asking Claude for fresh candidates…"):
                d = admin_claude.discover_competitor_candidates(
                    current_competitors=all_competitors_names + [r.get("name", "") for r in pending],
                    n=8,
                )
            result = {"added": 0, "claude_error": None, "raw": None, "insert_errors": [], "candidates": []}
            if not d.get("ok"):
                result["claude_error"] = d.get("error") or "Discovery failed."
                result["raw"] = d.get("raw")
            else:
                proposals = d.get("candidates") or []
                result["candidates"] = proposals
                for c in proposals:
                    try:
                        add_candidate(
                            client,
                            name=c["name"],
                            seo_domain=c.get("seo_domain"),
                            suggested_terms=c.get("suggested_terms") or [],
                            source="claude_discovery",
                            signal_strength=c.get("signal_strength"),
                            reason=c.get("reason"),
                            sample_evidence=c.get("sample_evidence"),
                            status="pending",
                        )
                        result["added"] += 1
                    except Exception as e:
                        result["insert_errors"].append(f"{c.get('name', '?')}: {e}")
                if result["added"]:
                    log_audit(
                        client, table_name="competitor_candidates", action="insert",
                        row_label=f"{result['added']} new candidates via claude_discovery",
                        actor=actor,
                    )
            st.session_state["_discover_result"] = result
            st.cache_data.clear()
            st.rerun()

        # Persist last discovery result across the rerun so the user sees it
        dr = st.session_state.get("_discover_result")
        if dr:
            if dr.get("claude_error"):
                st.error(f"Claude error: {dr['claude_error']}")
                if dr.get("raw"):
                    with st.expander("Show Claude's raw response"):
                        st.code(dr["raw"][:4000])
            else:
                proposed = len(dr.get("candidates") or [])
                if dr["added"]:
                    st.success(f"✅ Added {dr['added']} of {proposed} proposed candidates.")
                elif proposed == 0:
                    st.warning("Claude returned 0 candidates. Try again — it varies between calls.")
                else:
                    st.error(f"Claude proposed {proposed} but 0 were inserted. See errors below.")
            if dr.get("insert_errors"):
                with st.expander(f"Insert errors ({len(dr['insert_errors'])})"):
                    for e in dr["insert_errors"]:
                        st.write(f"• {e}")
            if st.button("Dismiss", key="dismiss_discover_result"):
                st.session_state.pop("_discover_result", None)
                st.rerun()

    if not pending:
        st.info("No pending candidates. Click ‘Discover with Claude’ to populate the queue.")
    else:
        for cand in pending:
            cid = cand.get("id")
            name = cand.get("name") or "?"
            with st.container(border=True):
                hdr1, hdr2 = st.columns([3, 1])
                with hdr1:
                    confidence = cand.get("signal_strength") or 0
                    st.markdown(f"**{name}**  ·  confidence {float(confidence):.0%}")
                    if cand.get("seo_domain"):
                        st.caption(f"🌐 {cand['seo_domain']}")
                    if cand.get("suggested_terms"):
                        terms = ", ".join(cand["suggested_terms"]) if isinstance(cand["suggested_terms"], list) else str(cand["suggested_terms"])
                        st.caption(f"🔎 Search terms: {terms}")
                    if cand.get("reason"):
                        st.markdown(f"_{cand['reason']}_")
                    if cand.get("sample_evidence"):
                        st.caption(f"📎 {cand['sample_evidence']}")
                with hdr2:
                    if st.button("✅ Approve", key=f"cand_approve_{cid}", type="primary"):
                        # Promote: insert into competitors, mark candidate approved
                        try:
                            inserted = add_competitors(
                                client,
                                name=name,
                                meta_search_terms=cand.get("suggested_terms") or [],
                                seo_domain=clean_seo_domain(cand.get("seo_domain")),
                                appstore_id=cand.get("appstore_id"),
                                active=True,
                                notes=cand.get("reason"),
                            )
                            new_comp_id = inserted.get("id") if isinstance(inserted, dict) else None
                            update_candidate(client, cid, {
                                "status": "approved",
                                "decided_at": datetime.utcnow().isoformat(),
                                "decided_by": actor,
                                "promoted_to_competitor_id": new_comp_id,
                            })
                            log_audit(
                                client, table_name=COMPETITORS_TABLE, action="insert",
                                row_id=str(new_comp_id) if new_comp_id else None,
                                row_label=name, note=f"approved from candidate {cid}",
                                actor=actor,
                            )
                            st.success(f"Promoted {name} to competitors.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Approve failed: {e}")
                    if st.button("❌ Reject", key=f"cand_reject_{cid}"):
                        try:
                            update_candidate(client, cid, {
                                "status": "rejected",
                                "decided_at": datetime.utcnow().isoformat(),
                                "decided_by": actor,
                            })
                            log_audit(
                                client, table_name="competitor_candidates", action="update",
                                row_id=str(cid), row_label=name, field="status",
                                old_value="pending", new_value="rejected", actor=actor,
                            )
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Reject failed: {e}")
                    if st.button("⏰ Snooze", key=f"cand_snooze_{cid}"):
                        try:
                            update_candidate(client, cid, {
                                "status": "snoozed",
                                "decided_at": datetime.utcnow().isoformat(),
                                "decided_by": actor,
                            })
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Snooze failed: {e}")

    if snoozed:
        with st.expander(f"⏰ Snoozed ({len(snoozed)})"):
            for cand in snoozed:
                cid = cand.get("id")
                cols = st.columns([4, 1, 1])
                with cols[0]:
                    st.markdown(f"**{cand.get('name')}** — {cand.get('reason') or ''}")
                with cols[1]:
                    if st.button("Wake up", key=f"wake_{cid}"):
                        update_candidate(client, cid, {"status": "pending"})
                        st.cache_data.clear()
                        st.rerun()
                with cols[2]:
                    if st.button("Delete", key=f"snoozed_del_{cid}"):
                        delete_candidate(client, cid)
                        st.cache_data.clear()
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Audit Log
# ══════════════════════════════════════════════════════════════════════════════
with tab_audit:
    cf1, cf2 = st.columns([1, 3])
    with cf1:
        filter_table = st.selectbox(
            "Filter",
            options=["(all tables)", COMPETITORS_TABLE, CONTENT_CLUSTERS_TABLE, TONE_KEYWORDS_TABLE, "competitor_candidates"],
            key="audit_filter",
        )
    events = list_audit(
        client,
        limit=100,
        table_name=None if filter_table == "(all tables)" else filter_table,
    )

    if not events:
        st.info("No audit events yet. Make any edit and it'll show up here.")
    else:
        rows = []
        for e in events:
            ts = e.get("created_at", "")
            try:
                ts_pretty = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
            except Exception:
                ts_pretty = str(ts)[:16]
            change = e.get("field") or ""
            if e.get("old_value") is not None and e.get("new_value") is not None and change:
                change = f"{change}: {e['old_value']} → {e['new_value']}"
            elif e.get("new_value"):
                change = e["new_value"][:80]
            rows.append({
                "When": ts_pretty,
                "Table": e.get("table_name", ""),
                "Row": e.get("row_label", "") or e.get("row_id", "")[:8],
                "Action": e.get("action", ""),
                "Change": change,
                "Actor": e.get("actor", ""),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=520)


st.markdown("<hr>", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;color:{COLORS["muted"]};font-size:0.75rem;">'
    "Admin · Listn Intel · changes save instantly to Supabase · "
    f"{'Claude-assisted' if claude_ready else 'Claude offline (no API key)'}"
    "</p>",
    unsafe_allow_html=True,
)
