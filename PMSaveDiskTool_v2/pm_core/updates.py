"""Update-check state and GitHub Releases fetcher.

Pure logic for Help → Check for Updates and the automatic background
check. No tkinter; the GUI module wires the thread and the UI around this.

Persistent state lives at ``~/.pmsavedisktool/update_check.json`` with the
schema documented in ``default_state``. The state file is written only
after the user has answered the first-launch opt-in dialog, so its mere
existence signals "user has seen the prompt".
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

RELEASES_API_URL = (
    "https://api.github.com/repos/vitopod/"
    "amiga-player-manager-toolkit/releases/latest"
)
RELEASES_PAGE_URL = (
    "https://github.com/vitopod/amiga-player-manager-toolkit/releases"
)

STATE_DIR = os.path.expanduser("~/.pmsavedisktool")
STATE_FILE = os.path.join(STATE_DIR, "update_check.json")

INTERVAL_DAILY     = 24 * 60 * 60        # 1 day
INTERVAL_WEEKLY    = 7 * 24 * 60 * 60   # 7 days
CHECK_INTERVAL_SEC = INTERVAL_DAILY      # legacy alias used by existing tests
FETCH_TIMEOUT_SEC = 5


def default_state() -> dict:
    """Return the state dict used when no file exists yet.

    ``opted_in`` is tri-state: ``None`` means the user hasn't been asked,
    ``True`` means they agreed to daily background checks, ``False`` means
    they declined. Declining leaves the manual Help → Check for Updates
    menu item working — this flag only gates the automatic check.
    """
    return {
        "opted_in": None,
        "last_check_at": 0.0,
        "latest_version": "",
        "release_url": "",
    }


def load_state() -> dict:
    """Read the state file, returning defaults if missing or malformed."""
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default_state()
    state = default_state()
    if isinstance(data, dict):
        for k in state:
            if k in data:
                state[k] = data[k]
    return state


def save_state(state: dict) -> None:
    """Persist state, creating the directory on first write."""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def should_check(
    state: dict,
    now: float | None = None,
    interval: int = INTERVAL_WEEKLY,
) -> bool:
    """True if the opt-in is on and we're past the check-interval window."""
    if not state.get("opted_in"):
        return False
    now = now if now is not None else time.time()
    last = float(state.get("last_check_at") or 0.0)
    return (now - last) >= interval


def version_tuple(v: str) -> tuple[int, ...]:
    """Parse a dotted version into an int tuple for ordering.

    Stops at the first non-digit in each component, so ``"2.2.1-rc1"``
    compares as ``(2, 2, 1)``. Matches the behaviour callers expect for
    the project's release tag scheme (``v2.2.2``, ``v2.3.0``, ...).
    """
    parts: list[int] = []
    for chunk in v.strip().lstrip("v").split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def is_newer(latest: str, current: str) -> bool:
    """True when ``latest`` sorts strictly after ``current``."""
    return version_tuple(latest) > version_tuple(current)


def fetch_latest(timeout: float = FETCH_TIMEOUT_SEC
                 ) -> tuple[str, str] | None:
    """Return ``(latest_version, html_url)`` or ``None`` on any failure.

    The version string has any leading ``v`` stripped so callers can feed
    it straight to :func:`is_newer`. Errors are swallowed on purpose —
    the background path stays silent; the manual path presents its own
    dialog when it needs to surface a problem.
    """
    req = urllib.request.Request(
        RELEASES_API_URL,
        headers={"Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    tag = str(data.get("tag_name", "")).lstrip("v").strip()
    if not tag:
        return None
    url = str(data.get("html_url") or RELEASES_PAGE_URL)
    return tag, url
