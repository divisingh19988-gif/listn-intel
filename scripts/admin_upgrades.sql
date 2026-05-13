-- Listn Intel — Admin upgrades migration
-- Paste this whole block into the Supabase SQL Editor:
--   Supabase Dashboard → SQL Editor → New query → paste → Run
-- Safe to re-run: every statement uses IF NOT EXISTS.

-- ── 1. Audit log table ───────────────────────────────────────────────────────
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

-- ── 2. Competitor candidates queue ───────────────────────────────────────────
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

-- ── 3. Soft-delete columns on existing tables ────────────────────────────────
alter table competitors add column if not exists deleted_at timestamptz;
create index if not exists idx_competitors_deleted on competitors (deleted_at);

alter table content_clusters add column if not exists deleted_at timestamptz;
create index if not exists idx_content_clusters_deleted on content_clusters (deleted_at);
