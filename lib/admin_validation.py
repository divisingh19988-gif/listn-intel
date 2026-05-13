"""
Validation + dedupe helpers for the admin page.

All validators return (ok: bool, errors: list[str], warnings: list[str]).
The page renders errors as st.error and warnings as st.warning, but accepts
the submit when warnings only.
"""

from __future__ import annotations

import re
from typing import Iterable

# Hostname-ish — accepts "example.com", "sub.example.co.uk". Rejects schemes,
# trailing slashes, paths, spaces. Loose enough not to fight obscure TLDs.
_DOMAIN_RE = re.compile(r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$", re.IGNORECASE)
# App Store numeric ID — actual ITunes apps are 9-10 digit ints. Accept 7-12 for safety.
_APPSTORE_RE = re.compile(r"^\d{7,12}$")
_WINDOW_OPTIONS = {"URGENT", "SOON", "EVERGREEN", "COMMERCIAL INTENT"}


def _norm(name: str) -> str:
    return (name or "").strip().casefold()


def validate_competitor(
    *,
    name: str,
    seo_domain: str | None,
    appstore_id: str | None,
    meta_search_terms: Iterable[str],
    existing_names: Iterable[str] = (),
    skip_id: str | None = None,  # unused at validate-time, kept for symmetry
) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    nm = (name or "").strip()
    if not nm:
        errors.append("Name is required.")
    elif len(nm) < 2:
        errors.append("Name is too short.")

    norm_nm = _norm(nm)
    if norm_nm and any(_norm(x) == norm_nm for x in existing_names):
        errors.append(f"A competitor named '{nm}' already exists (case-insensitive).")

    dom = (seo_domain or "").strip()
    if dom:
        # Auto-strip common mistakes before flagging.
        cleaned = dom.lower()
        for prefix in ("http://", "https://"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        cleaned = cleaned.rstrip("/").split("/")[0]
        if cleaned != dom.lower():
            warnings.append(f"SEO domain will be saved as '{cleaned}' (stripped scheme/path).")
        if not _DOMAIN_RE.match(cleaned):
            errors.append(f"SEO domain '{dom}' does not look like a hostname (e.g. 'example.com').")

    app = (appstore_id or "").strip()
    if app and not _APPSTORE_RE.match(app):
        errors.append(f"App Store ID '{app}' must be 7–12 digits (numeric only).")

    terms = [t for t in (meta_search_terms or []) if t and t.strip()]
    if not terms:
        warnings.append("No meta search terms — scrapers will have nothing to search for this competitor.")
    elif len(terms) < 2:
        warnings.append("Only one search term — consider adding variants (e.g. brand + 'App').")

    return (len(errors) == 0, errors, warnings)


def clean_seo_domain(dom: str | None) -> str | None:
    if not dom:
        return None
    cleaned = dom.strip().lower()
    for prefix in ("http://", "https://"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    cleaned = cleaned.rstrip("/").split("/")[0]
    return cleaned or None


def validate_cluster(
    *,
    name: str,
    window_label: str | None,
    keywords: Iterable,
    existing_names: Iterable[str] = (),
) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    nm = (name or "").strip()
    if not nm:
        errors.append("Name is required.")

    if nm and any(_norm(x) == _norm(nm) for x in existing_names):
        warnings.append(f"A cluster named '{nm}' already exists — saving will create a duplicate.")

    if window_label not in _WINDOW_OPTIONS:
        errors.append(f"Window must be one of {sorted(_WINDOW_OPTIONS)}.")

    kw_list = list(keywords or [])
    if not kw_list:
        warnings.append("No keywords — this cluster will not target anything until you add some.")
    elif len(kw_list) < 3:
        warnings.append(f"Only {len(kw_list)} keyword(s) — clusters work best with 5+.")

    return (len(errors) == 0, errors, warnings)


def validate_tone(
    *,
    tone: str,
    keyword_list: Iterable[str],
    existing_tones: Iterable[str] = (),
) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    tn = (tone or "").strip()
    if not tn:
        errors.append("Tone is required.")
    elif any(_norm(x) == _norm(tn) for x in existing_tones):
        errors.append(f"Tone '{tn}' already exists.")

    kw = [k.strip() for k in (keyword_list or []) if k and k.strip()]
    if not kw:
        errors.append("At least one keyword is required.")
    elif len(kw) < 3:
        warnings.append(f"Only {len(kw)} keyword(s) — tone classification needs 3+ to be reliable.")

    return (len(errors) == 0, errors, warnings)
