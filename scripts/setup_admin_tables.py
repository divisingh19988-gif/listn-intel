#!/usr/bin/env python3
"""
Setup script for the admin upgrades.

Adds two new tables and two new columns to existing ones:

  - admin_audit              — change log for every admin edit
  - competitor_candidates    — auto-discovered competitor queue (Approve/Reject/Snooze)
  - competitors.deleted_at   — soft-delete column
  - content_clusters.deleted_at — soft-delete column

Same DDL strategy as scripts/setup_supabase_tables.py: try an exec_sql RPC,
otherwise print the SQL for the Supabase SQL Editor.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


# Reuse the shared helper so casing aliases (Supabase_URL / Supabase_anon_key etc.)
# are honoured here too.
from lib.supabase_client import _read_secret  # noqa: E402

SUPABASE_URL = _read_secret("SUPABASE_URL")
SUPABASE_KEY = _read_secret("SUPABASE_KEY")


DDL = {
    "admin_audit": """
create table if not exists admin_audit (
    id uuid primary key default uuid_generate_v4(),
    table_name text not null,
    row_id text,
    row_label text,
    action text not null,            -- 'insert' | 'update' | 'delete' | 'restore' | 'hard_delete'
    field text,                       -- nullable for whole-row inserts/deletes
    old_value text,
    new_value text,
    actor text,                       -- 'Digvijay' | 'Eli' | etc.
    note text,                        -- optional reason / context
    created_at timestamptz default now()
);
create index if not exists idx_admin_audit_created on admin_audit (created_at desc);
create index if not exists idx_admin_audit_table on admin_audit (table_name, created_at desc);
""".strip(),
    "competitor_candidates": """
create table if not exists competitor_candidates (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    seo_domain text,
    appstore_id text,
    suggested_terms text[] default '{}',
    source text,                       -- 'claude_discovery' | 'manual' | etc.
    signal_strength numeric,           -- 0..1 confidence
    reason text,                       -- human-readable why-it-matters
    sample_evidence text,              -- ad copy snippet or SERP neighbour list
    status text not null default 'pending',  -- 'pending' | 'approved' | 'rejected' | 'snoozed'
    snoozed_until date,
    promoted_to_competitor_id uuid,
    created_at timestamptz default now(),
    decided_at timestamptz,
    decided_by text
);
create index if not exists idx_candidates_status on competitor_candidates (status, created_at desc);
""".strip(),
    "competitors_deleted_at": """
alter table competitors add column if not exists deleted_at timestamptz;
create index if not exists idx_competitors_deleted on competitors (deleted_at);
""".strip(),
    "content_clusters_deleted_at": """
alter table content_clusters add column if not exists deleted_at timestamptz;
create index if not exists idx_content_clusters_deleted on content_clusters (deleted_at);
""".strip(),
}


def try_exec_ddl_via_rpc(client, sql: str) -> bool:
    for fn_name, key in (("exec_sql", "sql"), ("execute_sql", "sql"),
                         ("exec_sql", "query"), ("run_sql", "query")):
        try:
            client.rpc(fn_name, {key: sql}).execute()
            return True
        except Exception:
            continue
    return False


def main() -> int:
    print("=" * 70)
    print(" Supabase setup — Admin upgrades (audit + candidates + soft-delete)")
    print("=" * 70)

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\nSUPABASE_URL / SUPABASE_KEY not configured.")
        print("DDL to apply manually in the Supabase SQL Editor:\n")
        for name, sql in DDL.items():
            print(f"-- {name} --\n{sql}\n")
        return 1

    try:
        from supabase import create_client
    except ImportError:
        print("supabase-py not installed.")
        return 1

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    all_ok = True
    for name, sql in DDL.items():
        ok = try_exec_ddl_via_rpc(client, sql)
        if ok:
            print(f"  ok {name}: applied via exec_sql RPC")
        else:
            all_ok = False
            print(f"  -- {name}: could not run via REST, paste manually")

    if not all_ok:
        print("\nFalling back to manual DDL — paste into Supabase SQL Editor:\n")
        print("-" * 70)
        for name, sql in DDL.items():
            print(f"-- {name}\n{sql}\n")
        print("-" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
