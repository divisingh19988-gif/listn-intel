#!/usr/bin/env python3
"""
One-time Supabase setup — creates three tables (competitors, content_clusters,
tone_keywords) and seeds them from the current hardcoded data in
scrapers/scrape_ads.py and lib/synthesis.py.

Credentials are read the same way lib/supabase_client.py does:
Streamlit secrets first, then os.environ (with a .env fallback).

DDL note: Supabase's REST API (PostgREST) cannot run CREATE TABLE directly.
This script will try an `exec_sql(sql text)` RPC if one exists in your DB,
and otherwise prints the DDL for you to paste into the Supabase SQL Editor.
All DDL uses CREATE TABLE IF NOT EXISTS, so re-running is safe.

Seeding is idempotent: if a table already contains rows, that table is left
alone ("X rows already present — skipping").
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ── .env fallback (optional) ──────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass


# ── Credentials — same pattern as lib/supabase_client.py ──────────────────────
def _read_secret(name: str):
    """st.secrets first, then os.environ. Never raises."""
    try:
        import streamlit as st
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.environ.get(name)


SUPABASE_URL = _read_secret("SUPABASE_URL")
SUPABASE_KEY = _read_secret("SUPABASE_KEY")


# ── DDL ───────────────────────────────────────────────────────────────────────
DDL = {
    "competitors": """
create table if not exists competitors (
    id uuid primary key default uuid_generate_v4(),
    name text not null unique,
    meta_search_terms text[] default '{}',
    seo_domain text,
    appstore_id text,
    active boolean not null default true,
    notes text,
    created_at timestamptz default now()
);
""".strip(),
    "content_clusters": """
create table if not exists content_clusters (
    id uuid primary key default uuid_generate_v4(),
    name text not null,
    deadline date,
    window_label text not null,
    keywords jsonb not null default '[]',
    active boolean not null default true,
    created_at timestamptz default now()
);
""".strip(),
    "tone_keywords": """
create table if not exists tone_keywords (
    id uuid primary key default uuid_generate_v4(),
    tone text not null unique,
    keyword_list text[] not null default '{}',
    created_at timestamptz default now()
);
""".strip(),
}


# ── Seed-data loaders (import the source files by path) ───────────────────────
def _load_module(module_name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relpath)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {relpath}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_seed_data():
    """Returns (competitors, content_clusters, tone_keywords)."""
    competitors = []
    try:
        scrape = _load_module("_scrape_ads_src", "scrapers/scrape_ads.py")
        for name in scrape.COMPETITORS:
            plan = scrape.COMPETITOR_SEARCH_PLAN.get(name, [])
            seen, terms = set(), []
            for term, _type in plan:
                if term not in seen:
                    seen.add(term)
                    terms.append(term)
            competitors.append({
                "name": name,
                "meta_search_terms": terms,
                "seo_domain": None,
                "appstore_id": None,
                "active": True,
                "notes": None,
            })
    except Exception as e:
        print(f"  ⚠️  could not load scrapers/scrape_ads.py: {e}")
        print("      (competitors will be skipped)")

    synth = _load_module("_synthesis_src", "lib/synthesis.py")

    clusters = [{
        "name": c["name"],
        "deadline": c["deadline"].isoformat() if c.get("deadline") else None,
        "window_label": c["window"],
        "keywords": [list(k) for k in c["keywords"]],
        "active": True,
    } for c in synth.SEO_CLUSTERS]

    tones = [{"tone": k, "keyword_list": list(v)} for k, v in synth.TONE_KEYWORDS.items()]

    return competitors, clusters, tones


# ── DDL execution helpers ─────────────────────────────────────────────────────
def try_exec_ddl_via_rpc(client, sql: str) -> bool:
    """Try a few common SQL-runner RPC names. Return True if one worked."""
    for fn_name, key in (("exec_sql", "sql"), ("execute_sql", "sql"),
                         ("exec_sql", "query"), ("run_sql", "query")):
        try:
            client.rpc(fn_name, {key: sql}).execute()
            return True
        except Exception:
            continue
    return False


def table_row_count(client, table: str) -> int | None:
    """Return row count, or None if the table doesn't exist / can't be read."""
    try:
        resp = client.table(table).select("id", count="exact").limit(1).execute()
        return resp.count if resp.count is not None else len(resp.data or [])
    except Exception:
        return None


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> int:
    print("=" * 70)
    print(" Supabase setup — Listn Intel Meta")
    print("=" * 70)

    # Build seed data regardless of whether creds are available — useful as a
    # dry-run preview.
    competitors, clusters, tones = build_seed_data()
    print(f"\nSeed data prepared from source files:")
    print(f"  competitors      → {len(competitors):>3} rows  ({', '.join(c['name'] for c in competitors)})")
    print(f"  content_clusters → {len(clusters):>3} rows  ({', '.join(c['name'] for c in clusters)})")
    print(f"  tone_keywords    → {len(tones):>3} rows  ({', '.join(t['tone'] for t in tones)})")

    if not SUPABASE_URL or not SUPABASE_KEY:
        print("\n❌  SUPABASE_URL / SUPABASE_KEY not configured "
              "(set them in .env, .streamlit/secrets.toml, or env vars).")
        print("\nDDL that would be applied:\n")
        for name, ddl in DDL.items():
            print(f"-- {name} --\n{ddl}\n")
        print("Re-run this script once credentials are in place.")
        return 1

    try:
        from supabase import create_client
    except ImportError:
        print("\n❌  supabase-py is not installed.  pip install supabase")
        return 1

    print(f"\nConnecting to {SUPABASE_URL} …")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # ── DDL ──
    print("\n— Step 1: create tables —")
    all_via_rpc = True
    for name, sql in DDL.items():
        ok = try_exec_ddl_via_rpc(client, sql)
        if ok:
            print(f"  ✓ {name}: created (or already existed) via exec_sql RPC")
        else:
            all_via_rpc = False
            print(f"  ⚠️  {name}: could not run DDL via REST API (no exec_sql RPC available)")

    if not all_via_rpc:
        print("\n  Supabase's REST API can't run CREATE TABLE directly. Paste the DDL")
        print("  below into the Supabase SQL Editor (Project → SQL Editor → New query),")
        print("  then re-run this script to seed:\n")
        print("-" * 70)
        for name, sql in DDL.items():
            print(f"-- {name}\n{sql}\n")
        print("-" * 70)

    # ── Seed ──
    print("\n— Step 2: seed —")
    summary = []
    for table, rows in (
        ("competitors", competitors),
        ("content_clusters", clusters),
        ("tone_keywords", tones),
    ):
        if not rows:
            print(f"  ⏭  {table}: no rows to insert (source data missing)")
            summary.append((table, "skipped (no source data)"))
            continue

        existing = table_row_count(client, table)
        if existing is None:
            print(f"  ❌ {table}: table not reachable — create it first (see DDL above)")
            summary.append((table, "skipped (table not found)"))
            continue
        if existing > 0:
            print(f"  ⏭  {table}: {existing} rows already present — skipping seed")
            summary.append((table, f"skipped ({existing} rows already present)"))
            continue

        try:
            client.table(table).insert(rows).execute()
            print(f"  ✓ {table}: inserted {len(rows)} rows")
            summary.append((table, f"seeded {len(rows)} rows"))
        except Exception as e:
            print(f"  ❌ {table}: insert failed — {e}")
            summary.append((table, f"failed: {e}"))

    # ── Summary ──
    print("\n" + "=" * 70)
    print(" Summary")
    print("=" * 70)
    for table, status in summary:
        print(f"  {table:<18} {status}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
