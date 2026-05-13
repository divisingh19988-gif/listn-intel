"""
Claude-backed helpers for the admin page.

Every public function returns a dict with at minimum:
  { "ok": bool, "error": str | None, ... }

so the UI can render failures (missing API key, JSON parse error, timeout)
without crashing.

Model defaults to claude-sonnet-4-6 — fast enough for sub-3-second admin UX,
smart enough to reason about competitor fit. Override with ANTHROPIC_MODEL.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

try:
    from anthropic import Anthropic  # type: ignore
except ImportError:
    Anthropic = None  # type: ignore


DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
PRODUCT_CONTEXT = (
    "Listn is a voice-first memory-preservation app for older adults — users "
    "record stories, family interviews, and life memories that get transcribed "
    "and turned into legacy books / audio collections. Listn's space includes "
    "competitors like Remento, Meminto, StoryWorth, Storykeeper, Tellmel, "
    "Keepsake, HereAfter AI, and No Story Lost."
)


def _client():
    if Anthropic is None:
        return None
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        # Streamlit secrets fallback (mirrors lib/supabase_client.py pattern)
        try:
            import streamlit as st  # type: ignore
            if "ANTHROPIC_API_KEY" in st.secrets:
                key = st.secrets["ANTHROPIC_API_KEY"]
        except Exception:
            pass
    if not key:
        return None
    try:
        return Anthropic(api_key=key)
    except Exception:
        return None


def is_configured() -> bool:
    return _client() is not None


def _extract_json(text: str) -> Any:
    """Pull a JSON object/array out of a Claude response, tolerating fences."""
    if not text:
        return None
    # Strip ```json fences
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if m:
        text = m.group(1)
    text = text.strip()
    # Try direct parse, then bracket-scan as a fallback
    try:
        return json.loads(text)
    except Exception:
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end + 1])
                except Exception:
                    continue
    return None


def _call(prompt: str, *, max_tokens: int = 1024, system: str | None = None) -> dict:
    client = _client()
    if client is None:
        return {"ok": False, "error": "ANTHROPIC_API_KEY not configured (or anthropic SDK missing)."}
    try:
        msg = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=max_tokens,
            system=system or PRODUCT_CONTEXT,
            messages=[{"role": "user", "content": prompt}],
        )
        # Concat all text blocks
        text = "".join(getattr(b, "text", "") for b in msg.content if getattr(b, "type", "") == "text")
        return {"ok": True, "text": text, "model": DEFAULT_MODEL}
    except Exception as e:
        return {"ok": False, "error": f"Claude call failed: {e}"}


# ── Public helpers ────────────────────────────────────────────────────────────
def enrich_competitor(name: str) -> dict:
    """
    Given just a name, ask Claude to return:
      confidence (0..1), seo_domain, appstore_id (best-effort),
      meta_search_terms (list[str]), notes (one line), is_competitor (bool).
    """
    if not name or not name.strip():
        return {"ok": False, "error": "Name is empty."}
    prompt = (
        f"You are helping curate the competitor list for Listn.\n\n"
        f"{PRODUCT_CONTEXT}\n\n"
        f"The user is considering adding this competitor: '{name.strip()}'.\n\n"
        f"Answer in strict JSON with these keys:\n"
        f"  is_competitor (bool) — does this brand actually compete with Listn?\n"
        f"  confidence (float 0..1) — how sure you are\n"
        f"  seo_domain (string|null) — primary marketing domain, no scheme, no path\n"
        f"  appstore_id (string|null) — numeric iOS App Store ID if known, else null (do NOT guess)\n"
        f"  meta_search_terms (list[string]) — 2-5 variants to search the Meta Ad Library by\n"
        f"  notes (string) — one short sentence on why they matter (or why they don't)\n\n"
        f"Return ONLY the JSON object — no prose."
    )
    res = _call(prompt, max_tokens=600)
    if not res.get("ok"):
        return res
    parsed = _extract_json(res["text"])
    if not isinstance(parsed, dict):
        return {"ok": False, "error": "Could not parse Claude's response as JSON.", "raw": res["text"]}
    return {"ok": True, **parsed}


def suggest_cluster_keywords(cluster_name: str, existing: list[str] | None = None, n: int = 15) -> dict:
    """
    For a cluster like 'Mother's Day', return a list of keyword candidates
    each with: phrase, intent (informational | commercial | navigational),
    estimated_competition (low | medium | high), rationale (one phrase).
    """
    if not cluster_name or not cluster_name.strip():
        return {"ok": False, "error": "Cluster name is empty."}
    existing = existing or []
    prompt = (
        f"{PRODUCT_CONTEXT}\n\n"
        f"Generate {n} SEO keyword candidates for the content cluster '{cluster_name.strip()}'.\n"
        f"Focus on phrases real Listn buyers (adult children of older parents) would search.\n"
        + (f"Already in the cluster (avoid duplicates): {', '.join(existing)}\n" if existing else "")
        + "\nReturn strict JSON: a list of objects with keys:\n"
          "  phrase (string)\n"
          "  intent (one of: informational, commercial, navigational)\n"
          "  estimated_competition (one of: low, medium, high)\n"
          "  rationale (short phrase, < 12 words)\n\n"
          "Return ONLY the JSON array."
    )
    res = _call(prompt, max_tokens=1500)
    if not res.get("ok"):
        return res
    parsed = _extract_json(res["text"])
    if not isinstance(parsed, list):
        return {"ok": False, "error": "Could not parse keyword suggestions.", "raw": res["text"]}
    # Defensive shape-check
    keywords = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        phrase = (item.get("phrase") or "").strip()
        if not phrase:
            continue
        keywords.append({
            "phrase": phrase,
            "intent": (item.get("intent") or "informational").strip().lower(),
            "estimated_competition": (item.get("estimated_competition") or "medium").strip().lower(),
            "rationale": (item.get("rationale") or "").strip(),
        })
    return {"ok": True, "keywords": keywords}


def expand_tone_keywords(
    tone: str,
    existing: list[str] | None = None,
    ad_copy_corpus: list[str] | None = None,
    n: int = 10,
) -> dict:
    """
    Suggest new keywords for an existing tone, grounded in recent ad copy
    if any is supplied. Returns each as {phrase, frequency_estimate, example}.
    """
    if not tone or not tone.strip():
        return {"ok": False, "error": "Tone is empty."}
    existing = existing or []
    corpus = [c for c in (ad_copy_corpus or []) if c and isinstance(c, str)]
    corpus_block = ""
    if corpus:
        # Cap to ~6000 chars to stay cheap and fast
        joined = "\n---\n".join(corpus)[:6000]
        corpus_block = (
            f"\nHere is a sample of recent competitor ad copy. Ground your "
            f"suggestions in language that actually appears here:\n\n{joined}\n"
        )
    prompt = (
        f"{PRODUCT_CONTEXT}\n\n"
        f"We classify competitor ad copy by tone. Suggest {n} new keywords / "
        f"short phrases for the '{tone.strip()}' tone.\n"
        + (f"Already in the list: {', '.join(existing)}\n" if existing else "")
        + corpus_block
        + "\nReturn strict JSON: list of objects with keys:\n"
          "  phrase (string, lowercase, 1-3 words)\n"
          "  grounded (bool — true if you saw it in the supplied corpus)\n"
          "  example (string, optional — short ad snippet showing the tone)\n\n"
          "Return ONLY the JSON array."
    )
    res = _call(prompt, max_tokens=1200)
    if not res.get("ok"):
        return res
    parsed = _extract_json(res["text"])
    if not isinstance(parsed, list):
        return {"ok": False, "error": "Could not parse tone expansions.", "raw": res["text"]}
    out = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        phrase = (item.get("phrase") or "").strip().lower()
        if not phrase:
            continue
        out.append({
            "phrase": phrase,
            "grounded": bool(item.get("grounded")),
            "example": (item.get("example") or "").strip(),
        })
    return {"ok": True, "phrases": out}


def discover_competitor_candidates(
    *,
    current_competitors: list[str],
    n: int = 8,
) -> dict:
    """
    Ask Claude to propose new competitor candidates we haven't tracked yet,
    based on the Listn product context and the list we already track.
    Each result: {name, seo_domain, suggested_terms, signal_strength,
    reason, sample_evidence}.
    """
    prompt = (
        f"{PRODUCT_CONTEXT}\n\n"
        f"We already track these competitors: {', '.join(current_competitors)}.\n\n"
        f"Propose up to {n} ADDITIONAL competitors we should consider tracking. "
        f"Prioritise brands that are actively running ads or producing content "
        f"in the family-history / legacy-book / voice-journal space. Avoid "
        f"hardware (no smart speakers / recorders) and avoid generic note apps.\n\n"
        f"Return strict JSON: a list of objects with keys:\n"
        f"  name (string)\n"
        f"  seo_domain (string|null) — no scheme, no path\n"
        f"  suggested_terms (list[string]) — 2-4 Meta Ad Library search variants\n"
        f"  signal_strength (float 0..1) — your confidence they belong on the list\n"
        f"  reason (string) — one sentence on overlap with Listn\n"
        f"  sample_evidence (string) — known positioning line or recent angle\n\n"
        f"Return ONLY the JSON array."
    )
    res = _call(prompt, max_tokens=2000)
    if not res.get("ok"):
        return res
    parsed = _extract_json(res["text"])
    if not isinstance(parsed, list):
        return {"ok": False, "error": "Could not parse discovery output.", "raw": res["text"]}

    existing_norm = {c.strip().casefold() for c in current_competitors}
    candidates = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        if name.casefold() in existing_norm:
            continue  # already tracked
        candidates.append({
            "name": name,
            "seo_domain": (item.get("seo_domain") or None),
            "suggested_terms": item.get("suggested_terms") or [],
            "signal_strength": float(item.get("signal_strength") or 0.5),
            "reason": (item.get("reason") or "").strip(),
            "sample_evidence": (item.get("sample_evidence") or "").strip(),
        })
    return {"ok": True, "candidates": candidates}
