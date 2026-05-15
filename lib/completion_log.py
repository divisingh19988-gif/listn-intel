"""
Completion tracking + post-event sweep for time-bound dashboard items.

Each item has a deadline. While the deadline is in the future, items render
normally on the active dashboard with their existing urgency badges (URGENT,
SOON, overdue, etc.) — those signals are the whole point of seeing the item.

Once the deadline passes, the sweep moves the item into a history list with
a final status:
  - "Completed" if the user marked it complete via the dashboard UI before
    the deadline (recorded in `completions`).
  - "Incomplete" otherwise.

Storage lives in data/completion_log.json — tracked in git so the audit log
survives across machines and deploys. Read-modify-write is the only access
pattern, and the file is small (KB), so atomic rename + no locking is fine
for the single-process Streamlit dashboard.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Optional

LOG_PATH = Path(__file__).parent.parent / "data" / "completion_log.json"
SWEPT_HISTORY_LIMIT = 100


def _load() -> dict:
    if LOG_PATH.exists():
        try:
            data = json.loads(LOG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}
    data.setdefault("completions", {})
    data.setdefault("swept", [])
    return data


def _save(data: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = LOG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(LOG_PATH)


def _key(kind: str, item_id: str) -> str:
    return f"{kind}:{item_id}"


def is_completed(kind: str, item_id: str) -> bool:
    return _key(kind, item_id) in _load().get("completions", {})


def mark_complete(kind: str, item_id: str, note: Optional[str] = None) -> None:
    data = _load()
    data["completions"][_key(kind, item_id)] = {
        "completed_at": datetime.now().isoformat(timespec="seconds"),
        "note": note,
    }
    _save(data)


def unmark_complete(kind: str, item_id: str) -> None:
    data = _load()
    data["completions"].pop(_key(kind, item_id), None)
    _save(data)


def sweep(items: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    """Run the post-deadline sweep.

    Each item must have: 'kind', 'id', 'name', 'deadline' (date | None).
    Items with no deadline OR deadline >= today stay active. Items past
    deadline and not already archived get appended to the swept list with
    their final status (Completed if user marked, else Incomplete).

    Returns (active_items, items_swept_this_call). The second list is empty
    on the common path (everything already archived); use it when you want
    to surface a one-time notification "X just swept to history".
    """
    data = _load()
    already_swept = {(e["kind"], e["id"]) for e in data.get("swept", [])}
    active: list[dict] = []
    swept_now: list[dict] = []
    for item in items:
        deadline = item.get("deadline")
        if deadline is None or deadline >= today:
            active.append(item)
            continue
        key = (item["kind"], item["id"])
        if key in already_swept:
            continue
        completion = data["completions"].get(_key(item["kind"], item["id"]))
        entry = {
            "kind": item["kind"],
            "id": item["id"],
            "name": item["name"],
            "deadline": deadline.isoformat(),
            "swept_at": datetime.now().date().isoformat(),
            "status": "Completed" if completion else "Incomplete",
            "completed_at": completion["completed_at"] if completion else None,
        }
        swept_now.append(entry)
        data["swept"].append(entry)
    if swept_now:
        data["swept"] = data["swept"][-SWEPT_HISTORY_LIMIT:]
        _save(data)
    return active, swept_now


def get_history(kind: Optional[str] = None, limit: int = 20) -> list[dict]:
    data = _load()
    items = data.get("swept", [])
    if kind is not None:
        items = [i for i in items if i["kind"] == kind]
    return list(reversed(items))[:limit]
