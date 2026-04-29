"""In-memory git operations log.

Records every user-initiated git mutation (save-draft / commit / push /
auto-PR / manual-PR / discard / unstage) into a per-user ring-buffer so the
frontend Debug panel can render "what just happened" without users having
to grep server logs.

Process-local: a multi-worker deployment will see different slices of the
log per worker. That's acceptable for a debug aid; a real audit log lives
in the model layer instead.
"""

from __future__ import annotations

from collections import deque
from threading import Lock
from time import time
from typing import Any, Deque, Dict, List, Optional


_MAX_ENTRIES_PER_USER = 200

_log: Dict[int, Deque[Dict[str, Any]]] = {}
_lock = Lock()


def record(
    user_id: int,
    *,
    kind: str,
    status: str,
    message: str = '',
    space_slug: str = '',
    branch_name: str = '',
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one event to the user's ring-buffer.

    `kind` — short verb-ish identifier (e.g. "draft.save", "commit",
            "commit.push", "pr.create.auto", "pr.create.manual",
            "draft.discard", "branch.unstage").
    `status` — "ok" | "error" | "skip".
    `message` — short human-readable description / error text.
    `payload` — optional dict with extra structured context (commit_sha,
                pr_id, file_path, etc).  Passed through to the response as-is
                so the frontend can show whatever fields make sense.
    """
    entry: Dict[str, Any] = {
        'ts': time(),
        'kind': kind,
        'status': status,
        'message': message,
        'space_slug': space_slug,
        'branch_name': branch_name,
        'payload': payload or {},
    }
    with _lock:
        bucket = _log.get(user_id)
        if bucket is None:
            bucket = deque(maxlen=_MAX_ENTRIES_PER_USER)
            _log[user_id] = bucket
        bucket.append(entry)


def fetch(user_id: int, since: float = 0.0, limit: int = 100) -> List[Dict[str, Any]]:
    """Return up to `limit` newest entries for `user_id`, optionally only those
    with `ts > since`. Newest-first.
    """
    with _lock:
        items = list(_log.get(user_id, ()))
    if since > 0:
        items = [e for e in items if e.get('ts', 0) > since]
    items.reverse()
    return items[:limit]


def clear(user_id: int) -> int:
    """Drop the user's entire log. Returns how many entries were dropped.

    Mostly useful in tests; the Debug panel exposes it as a "Clear" button.
    """
    with _lock:
        bucket = _log.pop(user_id, None)
    return len(bucket) if bucket else 0
