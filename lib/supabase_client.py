"""
Supabase client wrapper.

Reads SUPABASE_URL + SUPABASE_KEY from Streamlit secrets first,
then falls back to os.environ (for CLI / scrapers / GitHub Actions).

Expected schema for the `action_tracker` table:
    id            uuid PRIMARY KEY default uuid_generate_v4()
    source        text             -- 'meta' | 'seo' | 'ai_readiness' | 'manual'
    recommendation text NOT NULL
    priority      text             -- 'HIGH' | 'MEDIUM' | 'LOW'
    status        text             -- 'Not Started' | 'In Progress' | 'Testing' | 'Done'
    notes         text
    week_added    text             -- ISO week, e.g. '2026-W17'
    deadline      date             -- optional target date
    assigned_by   text             -- 'Digvijay' | 'Eli' | 'Intel Dashboard'
    assigned_to   text             -- 'Digvijay' | 'Eli'
    created_at    timestamptz default now()

Run once in Supabase if the table predates assigned_by/assigned_to:
    alter table action_tracker add column if not exists assigned_by text;
    alter table action_tracker add column if not exists assigned_to text;
"""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

# Resend / Supabase imports are optional at module-load time so a missing
# install only breaks the page that actually uses them.
try:
    from supabase import create_client, Client  # type: ignore
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore
    Client = None  # type: ignore


def _read_secret(name: str) -> Optional[str]:
    """st.secrets first, then os.environ. Tries case variants so configs that
    use 'Supabase_URL' or 'supabase_url' still resolve. Never raises."""
    variants = {name, name.upper(), name.lower()}
    # Friendlier aliases for the two Supabase keys we use everywhere.
    aliases = {
        "SUPABASE_URL": {"Supabase_URL", "supabase_url"},
        "SUPABASE_KEY": {"Supabase_anon_key", "SUPABASE_ANON_KEY", "supabase_anon_key", "SUPABASE_SERVICE_ROLE_KEY"},
    }
    if name in aliases:
        variants |= aliases[name]
    try:
        import streamlit as st
        for v in variants:
            if v in st.secrets:
                return st.secrets[v]
    except Exception:
        pass
    for v in variants:
        val = os.environ.get(v)
        if val:
            return val
    return None


def get_supabase_credentials() -> tuple[Optional[str], Optional[str]]:
    """Return (url, key). Either may be None if not configured."""
    return _read_secret("SUPABASE_URL"), _read_secret("SUPABASE_KEY")


def get_client() -> Optional["Client"]:
    """
    Return a configured Supabase client, or None if credentials are missing
    or the supabase package isn't installed. Callers should handle None.
    """
    if create_client is None:
        return None
    url, key = get_supabase_credentials()
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def is_configured() -> bool:
    """Cheap check used by pages to decide whether to show config nags."""
    url, key = get_supabase_credentials()
    return bool(url and key and create_client is not None)


def current_iso_week(today: Optional[date] = None) -> str:
    """Return the ISO-week label for today, e.g. '2026-W17'."""
    today = today or date.today()
    iso_year, iso_week, _ = today.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


# ── Action CRUD helpers ───────────────────────────────────────────────────────
TABLE = "action_tracker"


def list_actions(client: "Client") -> list[dict]:
    """Return all actions, newest first."""
    resp = (
        client.table(TABLE)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def add_action(
    client: "Client",
    *,
    source: str,
    recommendation: str,
    priority: str = "MEDIUM",
    status: str = "Not Started",
    notes: str = "",
    week_added: Optional[str] = None,
    deadline: Optional[str] = None,
    assigned_by: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> dict:
    """Insert a new action row. Returns the inserted row."""
    payload = {
        "source": source,
        "recommendation": recommendation,
        "priority": priority,
        "status": status,
        "notes": notes,
        "week_added": week_added or current_iso_week(),
        "deadline": deadline,
        "assigned_by": assigned_by,
        "assigned_to": assigned_to,
    }
    resp = client.table(TABLE).insert(payload).execute()
    return resp.data[0] if resp.data else payload


def update_action(client: "Client", action_id: str, fields: dict) -> None:
    """Update specific fields on an action row."""
    client.table(TABLE).update(fields).eq("id", action_id).execute()


def delete_action(client: "Client", action_id: str) -> None:
    """Hard-delete an action row."""
    client.table(TABLE).delete().eq("id", action_id).execute()


def has_action_tracker_for_week(client: "Client", week: Optional[str] = None) -> bool:
    week = week or current_iso_week()
    try:
        resp = (
            client.table(TABLE)
            .select("*")
            .eq("week_added", week)
            .execute()
        )
        return len(resp.data or []) > 0
    except Exception as e:
        print("DEBUG ERROR:", e)
        return False


# ── Reference-data tables (competitors / content_clusters / tone_keywords) ────
# Same CRUD shape as action_tracker above; list_* returns only rows where
# active=true for the two tables that have an `active` column (tone_keywords
# does not, so it returns everything).
COMPETITORS_TABLE = "competitors"
CONTENT_CLUSTERS_TABLE = "content_clusters"
TONE_KEYWORDS_TABLE = "tone_keywords"


def list_competitors(client: "Client") -> list[dict]:
    """Return all active competitor rows, newest first."""
    resp = (
        client.table(COMPETITORS_TABLE)
        .select("*")
        .eq("active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def add_competitors(client: "Client", **fields) -> dict:
    """Insert a new competitor row. Returns the inserted row."""
    resp = client.table(COMPETITORS_TABLE).insert(fields).execute()
    return resp.data[0] if resp.data else fields


def update_competitors(client: "Client", competitor_id: str, fields: dict) -> None:
    """Update specific fields on a competitor row."""
    client.table(COMPETITORS_TABLE).update(fields).eq("id", competitor_id).execute()


def delete_competitors(client: "Client", competitor_id: str) -> None:
    """Soft-delete: set deleted_at + active=false. Use hard_delete_competitors to remove."""
    from datetime import datetime, timezone
    client.table(COMPETITORS_TABLE).update({
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "active": False,
    }).eq("id", competitor_id).execute()


def restore_competitors(client: "Client", competitor_id: str) -> None:
    """Undo a soft-delete on a competitor row."""
    client.table(COMPETITORS_TABLE).update({
        "deleted_at": None,
        "active": True,
    }).eq("id", competitor_id).execute()


def hard_delete_competitors(client: "Client", competitor_id: str) -> None:
    """Permanent delete (no undo)."""
    client.table(COMPETITORS_TABLE).delete().eq("id", competitor_id).execute()


def list_content_clusters(client: "Client") -> list[dict]:
    """Return all active content-cluster rows, newest first."""
    resp = (
        client.table(CONTENT_CLUSTERS_TABLE)
        .select("*")
        .eq("active", True)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def add_content_clusters(client: "Client", **fields) -> dict:
    """Insert a new content-cluster row. Returns the inserted row."""
    resp = client.table(CONTENT_CLUSTERS_TABLE).insert(fields).execute()
    return resp.data[0] if resp.data else fields


def update_content_clusters(client: "Client", cluster_id: str, fields: dict) -> None:
    """Update specific fields on a content-cluster row."""
    client.table(CONTENT_CLUSTERS_TABLE).update(fields).eq("id", cluster_id).execute()


def delete_content_clusters(client: "Client", cluster_id: str) -> None:
    """Soft-delete: set deleted_at + active=false."""
    from datetime import datetime, timezone
    client.table(CONTENT_CLUSTERS_TABLE).update({
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "active": False,
    }).eq("id", cluster_id).execute()


def restore_content_clusters(client: "Client", cluster_id: str) -> None:
    """Undo a soft-delete on a content-cluster row."""
    client.table(CONTENT_CLUSTERS_TABLE).update({
        "deleted_at": None,
        "active": True,
    }).eq("id", cluster_id).execute()


def hard_delete_content_clusters(client: "Client", cluster_id: str) -> None:
    """Permanent delete (no undo)."""
    client.table(CONTENT_CLUSTERS_TABLE).delete().eq("id", cluster_id).execute()


def list_tone_keywords(client: "Client") -> list[dict]:
    """Return all tone-keyword rows, newest first. (No `active` column on this table.)"""
    resp = (
        client.table(TONE_KEYWORDS_TABLE)
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


def add_tone_keywords(client: "Client", **fields) -> dict:
    """Insert a new tone-keyword row. Returns the inserted row."""
    resp = client.table(TONE_KEYWORDS_TABLE).insert(fields).execute()
    return resp.data[0] if resp.data else fields


def update_tone_keywords(client: "Client", tone_id: str, fields: dict) -> None:
    """Update specific fields on a tone-keyword row."""
    client.table(TONE_KEYWORDS_TABLE).update(fields).eq("id", tone_id).execute()


def delete_tone_keywords(client: "Client", tone_id: str) -> None:
    """Hard-delete a tone-keyword row. (No soft-delete column on this table.)"""
    client.table(TONE_KEYWORDS_TABLE).delete().eq("id", tone_id).execute()


# ── Admin audit log ───────────────────────────────────────────────────────────
ADMIN_AUDIT_TABLE = "admin_audit"


def log_audit(
    client: "Client",
    *,
    table_name: str,
    action: str,
    row_id: Optional[str] = None,
    row_label: Optional[str] = None,
    field: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    actor: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    """Best-effort write — never raise back into the admin page."""
    try:
        client.table(ADMIN_AUDIT_TABLE).insert({
            "table_name": table_name,
            "row_id": row_id,
            "row_label": row_label,
            "action": action,
            "field": field,
            "old_value": None if old_value is None else str(old_value),
            "new_value": None if new_value is None else str(new_value),
            "actor": actor,
            "note": note,
        }).execute()
    except Exception:
        # Audit must never break the user's edit — swallow and move on.
        pass


def list_audit(client: "Client", limit: int = 50, table_name: Optional[str] = None) -> list[dict]:
    """Return the most recent audit rows, newest first."""
    try:
        q = client.table(ADMIN_AUDIT_TABLE).select("*").order("created_at", desc=True).limit(limit)
        if table_name:
            q = q.eq("table_name", table_name)
        return q.execute().data or []
    except Exception:
        return []


# ── Competitor candidates queue ───────────────────────────────────────────────
COMPETITOR_CANDIDATES_TABLE = "competitor_candidates"


def list_candidates(client: "Client", status: Optional[str] = "pending") -> list[dict]:
    """Return candidates, newest first. Pass status=None for all."""
    try:
        q = client.table(COMPETITOR_CANDIDATES_TABLE).select("*").order("created_at", desc=True)
        if status:
            q = q.eq("status", status)
        return q.execute().data or []
    except Exception:
        return []


def add_candidate(client: "Client", **fields) -> dict:
    """Insert a new candidate row."""
    resp = client.table(COMPETITOR_CANDIDATES_TABLE).insert(fields).execute()
    return resp.data[0] if resp.data else fields


def update_candidate(client: "Client", candidate_id: str, fields: dict) -> None:
    client.table(COMPETITOR_CANDIDATES_TABLE).update(fields).eq("id", candidate_id).execute()


def delete_candidate(client: "Client", candidate_id: str) -> None:
    client.table(COMPETITOR_CANDIDATES_TABLE).delete().eq("id", candidate_id).execute()

