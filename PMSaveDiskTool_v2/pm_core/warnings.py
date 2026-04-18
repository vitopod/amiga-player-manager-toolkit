"""Per-position skill-threshold warnings.

A lightweight, tactic-agnostic sanity check: every position has a small
set of skills it cannot really do its job without (a GK with no
keeping, a FWD with no pace, …). If any of a player's *essential*
skills for its on-disk position is below :data:`DEFAULT_THRESHOLD`, we
surface a warning.

This is deliberately simpler than :mod:`pm_core.lineup` role-fit
scoring. No role inference, no weights, no tactic awareness — just a
per-position lookup that flags clearly underpowered players so the
user can spot squad holes at a glance. The thresholded list is meant
to *warn*, not to judge: PM's match engine does not work in terms of
roles, and a player below threshold is not necessarily unusable.

Layered on top of this in the future (blocked on .sav shirt→player
reversal): tactic-specific warnings that check each shirt against the
inferred demands of its tactic zone.
"""

from __future__ import annotations

from .player import PlayerRecord, POSITION_NAMES

__all__ = [
    "POSITION_REQUIRED_SKILLS",
    "DEFAULT_THRESHOLD",
    "weak_skills",
    "has_weakness",
    "describe_weaknesses",
]

# Essential skills per on-disk position byte (1=GK 2=DEF 3=MID 4=FWD).
# These are the skills a player of that position should have at a
# usable minimum; they are *not* an exhaustive "what makes a good
# player" list, just the must-haves.
POSITION_REQUIRED_SKILLS: dict[int, tuple[str, ...]] = {
    1: ("keeping", "agility", "resilience"),
    2: ("tackling", "stamina", "pace"),
    3: ("passing", "stamina", "flair"),
    4: ("shooting", "pace", "flair"),
}

# Player Manager skills run 0..255. A value of 100 sits just under
# "league average" for most skills in observed save disks and was the
# threshold the user asked for.
DEFAULT_THRESHOLD: int = 100


def weak_skills(
    p: PlayerRecord,
    threshold: int = DEFAULT_THRESHOLD,
) -> list[tuple[str, int]]:
    """Return the player's essential skills that fall below *threshold*.

    Returns an empty list if the player's position has no defined
    essentials (e.g. position byte 0 — garbage records) or if none of
    the essential skills are below threshold.
    """
    required = POSITION_REQUIRED_SKILLS.get(p.position, ())
    return [(s, getattr(p, s)) for s in required if getattr(p, s) < threshold]


def has_weakness(p: PlayerRecord, threshold: int = DEFAULT_THRESHOLD) -> bool:
    """Fast boolean: True if *any* essential skill is below threshold."""
    return bool(weak_skills(p, threshold))


def describe_weaknesses(
    p: PlayerRecord,
    threshold: int = DEFAULT_THRESHOLD,
) -> str:
    """Human-readable summary, e.g. ``"pace 85, stamina 92"``.

    Empty string when the player has no weaknesses at this threshold.
    """
    weak = weak_skills(p, threshold)
    if not weak:
        return ""
    return ", ".join(f"{name} {val}" for name, val in weak)
