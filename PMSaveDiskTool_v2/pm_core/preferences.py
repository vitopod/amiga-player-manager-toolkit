"""Persistent user preferences.

State file: ``~/.pmsavedisktool/preferences.json``. Pure-Python, no
tkinter — the GUI calls ``load()`` at startup and ``save()`` from the
Preferences dialog and from file-open / game-disk-open handlers (to
record last-used paths).

Schema keys with defaults — see ``default_state()``:

- ``show_splash`` (bool) — show the Amiga-style splash at launch.
- ``show_welcome`` (bool) — show the first-run welcome screen at launch.
  Defaults to ``True`` so brand-new installs see the quick tour.
- ``auto_open_last_save`` (bool) — re-open ``last_save_adf`` at launch.
- ``auto_open_last_game`` (bool) — re-load ``last_game_adf`` at launch.
- ``last_save_adf`` (str) — absolute path of the most recently opened
  save ADF. Written after any successful open, regardless of the
  auto-open toggle, so the file-open dialog can seed ``initialdir``.
- ``last_game_adf`` (str) — same idea for game disks.
- ``default_view`` (str) — View label to select in the main window's
  View combo after a save disk loads (e.g. ``"— Young Talents (≤21)"``,
  ``"All Players"``, ``"— Top 11 (4-3-3)"``). Empty string (default)
  means "first team in the save" — the pre-2.2.12 behaviour.
- ``default_formation`` (str) — preferred formation label used as the
  initial selection in the Line-up Coach window. One of ``"4-4-2"``,
  ``"4-3-3"``, ``"3-5-2"``. Defaults to ``"4-4-2"``.
- ``use_system_font`` (bool) — when True, the GUI uses a plain system
  font (Courier New) instead of the bundled Topaz pixel font. Takes
  effect on next launch. Defaults to False.
- ``theme`` (str) — GUI colour theme. ``"retro"`` (default) is the
  Amiga navy / amber / cyan look. ``"light"`` is a high-contrast
  accessible light theme (off-white background, dark text, muted blue
  accents). Takes effect on next launch. Splash / welcome dialogs are
  unaffected — they always render in the PM-title palette.
- ``skill_warnings`` (bool) — surface a ⚠ flag on players whose
  position-essential skills fall below the threshold (see
  :mod:`pm_core.warnings`). Defaults to ``True``. Applies live — the
  next player-list refresh picks up the new value.

The loader silently replaces missing / wrong-type values with
``default_state()`` entries so an older file (or a hand-edited one)
does not crash the GUI. The saver writes atomically through a
temp-file + ``os.replace`` so a partial write cannot corrupt the file.
"""

from __future__ import annotations

import json
import os
import tempfile


STATE_DIR = os.path.expanduser("~/.pmsavedisktool")
STATE_FILE = os.path.join(STATE_DIR, "preferences.json")


def default_state() -> dict:
    """Return a fresh preferences dict populated with defaults."""
    return {
        "show_splash":          True,
        "show_welcome":         True,
        "auto_open_last_save":  False,
        "auto_open_last_game":  False,
        "last_save_adf":        "",
        "last_game_adf":        "",
        "default_view":         "",
        "default_formation":    "4-4-2",
        "use_system_font":      False,
        "theme":                "retro",
        "skill_warnings":       True,
    }


def load() -> dict:
    """Read the preferences file, merging into defaults.

    Missing file, unreadable file, or malformed JSON all yield defaults.
    Within a well-formed file, any key that is missing or has the wrong
    type falls back to its default value.
    """
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return default_state()
    state = default_state()
    if isinstance(data, dict):
        for key, default_value in state.items():
            value = data.get(key)
            if isinstance(value, type(default_value)):
                state[key] = value
    return state


def save(state: dict) -> None:
    """Atomically write ``state`` to the preferences file.

    Unknown keys are dropped — only keys in ``default_state()`` survive
    the round trip. Errors are swallowed so a read-only filesystem
    never crashes the GUI; the next ``load()`` will just see defaults.
    """
    merged = default_state()
    for key in merged:
        if key in state and isinstance(state[key], type(merged[key])):
            merged[key] = state[key]
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix="pref-", suffix=".tmp", dir=STATE_DIR
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(merged, f, indent=2)
            os.replace(tmp_path, STATE_FILE)
        except OSError:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except OSError:
        pass  # best-effort — preferences are non-critical
