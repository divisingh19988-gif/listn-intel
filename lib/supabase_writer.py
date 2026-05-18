"""
Supabase storage + metadata writer for briefs and reports (Step D-3).

The Streamlit `lib/supabase_client.py` module uses the anon key for table CRUD
under the assumption that RLS is permissive (or that writes come from a logged-
in user). This module is different: it uses the **service-role key** so the
weekly cron can upload to Storage and insert metadata rows without per-bucket
or per-table policy grants. Service role bypasses RLS, so callers must trust
the environment.

Two public functions:

  upload_brief(week_label, markdown, workspace_id=...) -> dict
      Uploads markdown to the 'briefs' bucket and upserts a row in
      strategic_briefs. Idempotent on (workspace_id, week_label).

  upload_report(local_filepath, report_type, report_date, workspace_id=...) -> dict
      Uploads an xlsx / pdf / image to the 'reports' bucket and upserts a row
      in reports. Idempotent on (workspace_id, report_type, report_date,
      storage_path).

Both functions catch all errors and return them in the result dict, so a
failed Supabase upload never bubbles up and breaks the local file write.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from supabase import Client, create_client

DEFAULT_WORKSPACE_ID = "5e6e0dbd-fe7b-41fc-ac31-c0fd2ab8a1a6"

BRIEFS_BUCKET = "briefs"
REPORTS_BUCKET = "reports"

BRIEFS_TABLE = "strategic_briefs"
REPORTS_TABLE = "reports"

MIME_MAP = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def get_supabase_client() -> Client:
    """
    Build a service-role Supabase client from env. Raises RuntimeError with a
    clear message if either var is missing — caller decides whether that's
    fatal.
    """
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url:
        raise RuntimeError(
            "Supabase URL is not set. Add SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) "
            "to your .env or GitHub Actions secrets."
        )
    if not key:
        raise RuntimeError(
            "SUPABASE_SERVICE_ROLE_KEY is not set. Add it to your .env or GitHub "
            "Actions secrets. (This is the service-role key, NOT the anon key.)"
        )
    return create_client(url, key)


def _upload_to_storage(
    client: Client,
    bucket: str,
    storage_path: str,
    data: bytes,
    content_type: str,
) -> None:
    """
    Upload bytes to Supabase Storage with upsert=True. supabase-py 2.x expects
    file_options as string values, not booleans.
    """
    client.storage.from_(bucket).upload(
        path=storage_path,
        file=data,
        file_options={
            "content-type": content_type,
            "upsert": "true",
        },
    )


def upload_brief(
    week_label: str,
    markdown: str,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> dict:
    """
    Upload a strategic brief markdown to Supabase. Idempotent: re-running for
    the same week overwrites the storage object and leaves the metadata row
    unchanged (one row per workspace/week).

    Returns:
        {"storage_path": str, "uploaded": True}   on success
        {"storage_path": str, "error": str}       on failure
    """
    storage_path = f"{workspace_id}/{week_label}/strategic_brief.md"
    try:
        client = get_supabase_client()
        _upload_to_storage(
            client,
            BRIEFS_BUCKET,
            storage_path,
            markdown.encode("utf-8"),
            "text/markdown",
        )
        client.table(BRIEFS_TABLE).upsert(
            {
                "workspace_id": workspace_id,
                "week_label": week_label,
                "storage_path": storage_path,
            },
            on_conflict="workspace_id,week_label",
        ).execute()
        print(f"[supabase] brief uploaded: {BRIEFS_BUCKET}/{storage_path}")
        return {"storage_path": storage_path, "uploaded": True}
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"[supabase] brief upload FAILED ({storage_path}): {msg}")
        return {"storage_path": storage_path, "error": msg}


def upload_report(
    local_filepath: str,
    report_type: str,
    report_date: str,
    workspace_id: str = DEFAULT_WORKSPACE_ID,
) -> dict:
    """
    Upload a generated report file (xlsx / pdf / png / jpg) to Supabase.
    Idempotent: re-running with the same (workspace, type, date, path) tuple
    overwrites the storage object and leaves the metadata row unchanged.

    Args:
        local_filepath: absolute or relative path to the file on disk.
        report_type:    'meta_intel' | 'seo_intel' | 'ai_readiness' | ...
        report_date:    'YYYY-MM-DD' — typically Monday of the ISO week.
        workspace_id:   defaults to the single workspace.

    Returns:
        {"storage_path": str, "uploaded": True, "size_bytes": int}  on success
        {"error": str, ...}                                          on failure
    """
    path = Path(local_filepath)
    filename = path.name
    ext = path.suffix.lstrip(".").lower()
    storage_path = f"{workspace_id}/{report_type}/{report_date}__{filename}"

    if ext not in MIME_MAP:
        msg = f"Unsupported extension '.{ext}' (allowed: {sorted(MIME_MAP)})"
        print(f"[supabase] report upload REJECTED ({filename}): {msg}")
        return {"storage_path": storage_path, "error": msg}

    if not path.exists():
        msg = f"File not found: {local_filepath}"
        print(f"[supabase] report upload FAILED ({storage_path}): {msg}")
        return {"storage_path": storage_path, "error": msg}

    try:
        data = path.read_bytes()
        size_bytes = len(data)
        mime_type = MIME_MAP[ext]

        client = get_supabase_client()
        _upload_to_storage(client, REPORTS_BUCKET, storage_path, data, mime_type)

        y, m, d = report_date.split("-")
        report_dt = date(int(y), int(m), int(d))
        iso_year, iso_week, _ = report_dt.isocalendar()
        title = f"{report_type.replace('_', ' ').title()} — Week {iso_week} {iso_year}"

        client.table(REPORTS_TABLE).upsert(
            {
                "workspace_id": workspace_id,
                "report_type": report_type,
                "report_date": report_date,
                "storage_path": storage_path,
                "mime_type": mime_type,
                "file_size_bytes": size_bytes,
                "title": title,
            },
            on_conflict="workspace_id,report_type,report_date,storage_path",
        ).execute()
        print(
            f"[supabase] report uploaded: {REPORTS_BUCKET}/{storage_path} "
            f"({size_bytes:,} bytes)"
        )
        return {
            "storage_path": storage_path,
            "uploaded": True,
            "size_bytes": size_bytes,
        }
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"[supabase] report upload FAILED ({storage_path}): {msg}")
        return {"storage_path": storage_path, "error": msg}
