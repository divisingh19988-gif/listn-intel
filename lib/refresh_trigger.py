"""
Trigger the Weekly Intelligence Refresh GitHub Actions workflow.

The workflow (.github/workflows/weekly_refresh.yml) is the single source of
truth for the full pipeline: scrape Meta ads, fetch SEO data, run AI-readiness
audit, generate the strategic brief via Claude, and email the report.

Dispatching it from the dashboard runs the exact same pipeline that the
Monday cron triggers, so behaviour stays consistent regardless of who hits
"Refresh".
"""

from __future__ import annotations

import os
from typing import Optional

import requests

# Repo + workflow are pinned to match weekly_refresh.yml's failure-alert URL.
DEFAULT_REPO = "divisingh19988-gif/listn-intel"
WORKFLOW_FILE = "weekly_refresh.yml"
DEFAULT_REF = "main"


def _read_secret(name: str) -> Optional[str]:
    """st.secrets first, then os.environ. Mirrors lib/supabase_client.py."""
    variants = {name, name.upper(), name.lower()}
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


def _resolve_token() -> Optional[str]:
    return _read_secret("GH_PAT") or _read_secret("GITHUB_TOKEN")


def _resolve_repo() -> str:
    return _read_secret("GITHUB_REPO") or DEFAULT_REPO


def actions_url() -> str:
    """URL of the workflow's run history — safe to render even without a token."""
    return f"https://github.com/{_resolve_repo()}/actions/workflows/{WORKFLOW_FILE}"


def trigger_weekly_refresh() -> tuple[bool, str]:
    """Dispatch the weekly_refresh workflow on main.

    Returns (ok, message). On success the GitHub API returns 204 with no body;
    the run shows up at actions_url() within a few seconds.
    """
    token = _resolve_token()
    if not token:
        return (
            False,
            "GitHub token not configured. Set GH_PAT (or GITHUB_TOKEN) in st.secrets "
            "or environment with `workflow` scope.",
        )

    repo = _resolve_repo()
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    try:
        resp = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"ref": DEFAULT_REF},
            timeout=15,
        )
    except requests.RequestException as e:
        return False, f"Could not reach GitHub API: {e}"

    if resp.status_code == 204:
        return True, "Refresh triggered. The pipeline takes ~5–10 minutes."
    return False, f"GitHub API returned {resp.status_code}: {resp.text[:200]}"
