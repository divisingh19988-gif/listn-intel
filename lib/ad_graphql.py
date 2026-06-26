"""
Parse Meta Ad Library GraphQL/async responses for ad video URLs.

The Ad Library renders ad media from a GraphQL payload whose snapshot objects
carry ``video_hd_url`` / ``video_sd_url`` next to the ad's ``ad_archive_id``.
Those URLs are present in the JSON even when the browser refuses to render the
<video> element - which is exactly what happens from CI / datacenter IPs, where
Meta serves a "trouble playing this video" placeholder. Capturing them from the
network response is therefore far more reliable than scraping the DOM.

``harvest_video_urls(text)`` returns ``{ad_archive_id: best_video_url}``. It is
deliberately shape-tolerant: it deep-walks parsed JSON, and if parsing fails
(chunked / streamed responses) it falls back to a position-based regex pairing.
HD is preferred over SD. Never raises.
"""

from __future__ import annotations

import json
import re

_FOR_LOOP_PREFIX = "for (;;);"


def _deep_find_video(node):
    """First non-empty video url in this subtree; HD preferred over SD."""
    hd = None
    sd = None
    stack = [node]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(v, str) and v.startswith("http"):
                    if k == "video_hd_url" and hd is None:
                        hd = v
                    elif k == "video_sd_url" and sd is None:
                        sd = v
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(n, list):
            stack.extend(n)
    return hd or sd


def _harvest_json(obj, out):
    """Walk every object; when one declares an ad_archive_id, bind the first
    video url found in that same subtree to it."""
    stack = [obj]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            ad_id = n.get("ad_archive_id")
            if ad_id:
                vurl = _deep_find_video(n)
                if vurl:
                    out.setdefault(str(ad_id), vurl)
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)


def _iter_chunks(text):
    t = text.strip()
    if t.startswith(_FOR_LOOP_PREFIX):
        t = t[len(_FOR_LOOP_PREFIX):]
    try:
        yield json.loads(t)
        return
    except Exception:
        pass
    # Streamed/batched responses: one JSON object per line.
    for line in t.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue


_RE_ID = re.compile(r'"ad_archive_id"\s*:\s*"?(\d+)"?')
_RE_VID = re.compile(r'"video_(?:hd|sd)_url"\s*:\s*"(https:[^"]+)"')


def _harvest_regex(text, out):
    """Shape-agnostic fallback: attribute each video url to the nearest
    preceding ad_archive_id by character position."""
    ids = [(m.start(), m.group(1)) for m in _RE_ID.finditer(text)]
    if not ids:
        return
    for vm in _RE_VID.finditer(text):
        pos = vm.start()
        chosen = None
        for ipos, idv in ids:
            if ipos < pos:
                chosen = idv
            else:
                break
        if chosen:
            url = vm.group(1).replace("\\/", "/").replace("\\u0025", "%")
            out.setdefault(str(chosen), url)


def harvest_video_urls(text):
    """Return ``{ad_archive_id: video_url}`` found in a network response body."""
    out = {}
    if not text or ("video_hd_url" not in text and "video_sd_url" not in text):
        return out
    try:
        for obj in _iter_chunks(text):
            _harvest_json(obj, out)
    except Exception:
        pass
    if not out:
        try:
            _harvest_regex(text, out)
        except Exception:
            pass
    return out
