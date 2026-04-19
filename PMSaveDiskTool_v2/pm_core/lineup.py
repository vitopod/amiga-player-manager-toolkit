"""Line-up Coach — BETA.

Heuristic lineup selector and role-fit scorer for Player Manager saves.

Status
------
**This module is BETA.** Its scoring is a modern football-management heuristic
built on top of the 10 skill fields PM happens to store. PM's actual match
engine weights are *not* reverse-engineered — the weights in :data:`ROLES`,
:data:`DEFAULT_COMPOSITE_WEIGHTS`, and :data:`CROSS_POSITION_PENALTY` are
starting points to be calibrated against emulator observation, not ground
truth. Ship output accordingly: **"suggested," not "optimal."**

What it produces
----------------
- A role-fit score in [0, 1] for each (player, role) pair.
- The best eligible starting XI for a given formation, with a composite score
  that layers role fit, morale, fatigue, card risk, and form on top of the
  existing total-skill baseline.
- Per-player reassignment flags: "this player's best fit is a different
  role than their nominal position."

All primitives are pure; no :class:`SaveSlot` dependency required beyond a
roster of :class:`~pm_core.player.PlayerRecord`.
"""

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from .player import PlayerRecord, SKILL_NAMES

__all__ = [
    "ROLES", "FORMATION_ROLES", "CROSS_POSITION_PENALTY",
    "DEFAULT_COMPOSITE_WEIGHTS",
    "RoleAssignment", "LineupResult", "MatchdaySquad",
    "ReassignmentSuggestion",
    "role_fit", "best_role", "best_role_in_position",
    "assemble_xi", "assemble_matchday_squad",
    "score_xi", "suggest_reassignments",
    "rank_formations",
]

# ────────────────────────────────────────────────────────────────────────
# Role taxonomy
# ────────────────────────────────────────────────────────────────────────
#
# PM stores only position 1..4 (GK/DEF/MID/FWD). The taxonomy below is our
# own layer on top: familiar football sub-roles with skill weight vectors.
# Weights are not calibrated against PM's engine — they're a plausible
# starting point inspired by how the same roles are modelled in modern
# football-management literature. Tune freely; lock values with tests.

# Each role:
#   position    — maps to PM's position byte (1..4)
#   skills      — weight per skill; should sum to 1.0 for scoring stability
#   height_pref — optional "tall" / "small" modifier
#   age_curve   — optional (early, peak_start, peak_end, late) — linear
#                  penalty outside the plateau for pace-heavy roles.

ROLES: dict[str, dict] = {
    # Goalkeeper
    "GK":  {"position": 1,
            "skills":   {"keeping": 0.50, "agility": 0.20, "resilience": 0.15,
                         "flair": 0.10, "passing": 0.05}},
    # Defenders
    "CB":  {"position": 2,
            "skills":   {"tackling": 0.30, "resilience": 0.20, "keeping": 0.10,
                         "aggression": 0.15, "stamina": 0.15, "passing": 0.10},
            "height_pref": "tall"},
    "FB":  {"position": 2,
            "skills":   {"pace": 0.25, "stamina": 0.25, "tackling": 0.20,
                         "passing": 0.15, "agility": 0.15},
            "age_curve": (18, 22, 30, 34)},
    "SW":  {"position": 2,
            "skills":   {"tackling": 0.25, "passing": 0.25, "flair": 0.15,
                         "keeping": 0.15, "resilience": 0.10, "stamina": 0.10}},
    # Midfielders
    "DM":  {"position": 3,
            "skills":   {"tackling": 0.25, "stamina": 0.25, "passing": 0.20,
                         "aggression": 0.15, "resilience": 0.15}},
    "CM":  {"position": 3,
            "skills":   {"stamina": 0.25, "passing": 0.25, "flair": 0.15,
                         "tackling": 0.15, "pace": 0.10, "shooting": 0.10}},
    "AM":  {"position": 3,
            "skills":   {"flair": 0.25, "passing": 0.25, "shooting": 0.20,
                         "agility": 0.15, "pace": 0.15}},
    "WM":  {"position": 3,
            "skills":   {"pace": 0.25, "stamina": 0.20, "passing": 0.20,
                         "flair": 0.15, "agility": 0.20},
            "age_curve": (18, 22, 30, 34)},
    # Forwards
    "POA": {"position": 4,
            "skills":   {"shooting": 0.35, "agility": 0.25, "pace": 0.20,
                         "flair": 0.15, "stamina": 0.05},
            "age_curve": (18, 22, 31, 35)},
    "TGT": {"position": 4,
            "skills":   {"shooting": 0.30, "resilience": 0.20, "aggression": 0.15,
                         "passing": 0.15, "agility": 0.10, "stamina": 0.10},
            "height_pref": "tall"},
    "WNG": {"position": 4,
            "skills":   {"pace": 0.30, "flair": 0.25, "agility": 0.20,
                         "passing": 0.15, "shooting": 0.10},
            "age_curve": (18, 22, 30, 34)},
    "DLF": {"position": 4,
            "skills":   {"passing": 0.30, "flair": 0.25, "shooting": 0.20,
                         "agility": 0.15, "stamina": 0.10}},
}

# Formation → ordered list of role keys. Length must equal 11 and the
# position-byte counts must match FORMATIONS in pm_core.save.
FORMATION_ROLES: dict[str, list[str]] = {
    "4-4-2": ["GK",
              "CB", "CB", "FB", "FB",
              "DM", "CM", "CM", "WM",
              "POA", "TGT"],
    "4-3-3": ["GK",
              "CB", "CB", "FB", "FB",
              "DM", "CM", "AM",
              "WNG", "POA", "WNG"],
    "3-5-2": ["GK",
              "CB", "CB", "SW",
              "DM", "CM", "CM", "WM", "WM",
              "POA", "TGT"],
}

# Soft penalty applied when a role's position byte ≠ the player's. PM's
# match engine effect for "out of position" play is unknown — this is a
# deliberately small, tunable knob, not a simulation of engine behaviour.
CROSS_POSITION_PENALTY = 0.15

# Default weights for the composite XI score. Skill is the dominant term
# so the coach doesn't do anything wild out of the box.
DEFAULT_COMPOSITE_WEIGHTS: dict[str, float] = {
    "skill":     1.0,   # × total_skill (absolute)
    "fit":       40.0,  # × mean role_fit (0..1)
    "morale":    20.0,  # × mean morale / 255
    "fatigue":   20.0,  # × mean fatigue index (0..1), subtracted
    "card_risk": 15.0,  # × mean card-risk (0..1), subtracted
    "form":      15.0,  # × mean form index for FWDs (0..~1), added
}


# ────────────────────────────────────────────────────────────────────────
# Result shapes
# ────────────────────────────────────────────────────────────────────────

@dataclass
class RoleAssignment:
    role: str                 # role key, e.g. "CB"
    player: PlayerRecord
    fit: float                # 0..1


@dataclass
class LineupResult:
    formation: str
    assignments: list[RoleAssignment]
    composite: float
    breakdown: dict[str, float]

    @property
    def total_skill(self) -> int:
        return sum(a.player.total_skill for a in self.assignments)


@dataclass
class MatchdaySquad:
    """Starting XI plus a short bench of reserves.

    ``xi`` is an XI in formation order (GK first, then DEF/MID/FWD). ``reserves``
    is an ordered list of bench players — typically 2 — each carrying the role
    they'd slot into if subbed in (``best_role_in_position`` for the player).
    The bench may be shorter than requested when the pool is thin.
    """
    formation: str
    xi: list[RoleAssignment]
    reserves: list[RoleAssignment]
    composite: float
    breakdown: dict[str, float]

    @property
    def total_skill(self) -> int:
        return sum(a.player.total_skill for a in self.xi)


@dataclass
class ReassignmentSuggestion:
    player: PlayerRecord
    nominal_role: str          # best role within the player's current position
    nominal_fit: float
    best_role: str             # best role across the whole taxonomy
    best_fit: float
    gap: float                 # best_fit - nominal_fit


# ────────────────────────────────────────────────────────────────────────
# Scoring primitives
# ────────────────────────────────────────────────────────────────────────

_MAX_SKILL = 200  # PM skills are nominally 0..200; clip above for safety.


def _norm_skill(v: int) -> float:
    return max(0.0, min(1.0, v / _MAX_SKILL))


def _height_modifier(pref: Optional[str], height: int) -> float:
    if not pref or not height:
        return 1.0
    if pref == "tall":
        if height >= 185:
            return 1.05
        if height < 175:
            return 0.92
    elif pref == "small":
        if height <= 170:
            return 1.03
        if height >= 185:
            return 0.95
    return 1.0


def _age_modifier(curve: Optional[tuple], age: int) -> float:
    """Linear-ish penalty outside the plateau for pace-reliant roles.

    curve = (early, peak_start, peak_end, late). Full score in [peak_start, peak_end];
    ramps linearly from 0.80 at or below `early`, to 1.0 at `peak_start`, and
    back down to 0.80 at or above `late`. Flat 1.0 inside the peak window.
    """
    if not curve or age <= 0:
        return 1.0
    early, ps, pe, late = curve
    if ps <= age <= pe:
        return 1.0
    if age < ps:
        if age <= early:
            return 0.80
        return 0.80 + 0.20 * (age - early) / max(1, ps - early)
    if age >= late:
        return 0.80
    return 1.0 - 0.20 * (age - pe) / max(1, late - pe)


def role_fit(player: PlayerRecord, role_key: str) -> float:
    """Return a 0..1 role-fit score for ``player`` in ``role_key``.

    Weighted sum of normalised skills per the role's weight vector, modulated
    by optional height and age modifiers, minus :data:`CROSS_POSITION_PENALTY`
    if the role's position byte doesn't match the player's nominal position.
    Clipped to [0, 1].
    """
    if role_key not in ROLES:
        raise KeyError(f"unknown role {role_key!r}")
    role = ROLES[role_key]
    base = 0.0
    for skill_name, w in role["skills"].items():
        base += _norm_skill(getattr(player, skill_name)) * w

    base *= _height_modifier(role.get("height_pref"), player.height)
    base *= _age_modifier(role.get("age_curve"), player.age)

    if player.position != role["position"]:
        base *= (1.0 - CROSS_POSITION_PENALTY)

    return max(0.0, min(1.0, base))


def _roles_for_position(pos: int) -> list[str]:
    return [r for r, cfg in ROLES.items() if cfg["position"] == pos]


def best_role(player: PlayerRecord,
              candidates: Optional[Iterable[str]] = None) -> tuple[str, float]:
    """Return the highest-fitting role for ``player`` (name, fit)."""
    keys = list(candidates) if candidates is not None else list(ROLES)
    if not keys:
        raise ValueError("no candidate roles supplied")
    scored = [(k, role_fit(player, k)) for k in keys]
    return max(scored, key=lambda kv: kv[1])


def best_role_in_position(player: PlayerRecord) -> tuple[str, float]:
    """Best-fit role restricted to the player's nominal position."""
    candidates = _roles_for_position(player.position)
    if not candidates:
        # Invalid / sentinel — fall back to the absolute best.
        return best_role(player)
    return best_role(player, candidates)


# ────────────────────────────────────────────────────────────────────────
# XI assembly
# ────────────────────────────────────────────────────────────────────────

def _is_eligible(p: PlayerRecord) -> bool:
    """Selection filter: real player with a valid position and age."""
    if p.position not in (1, 2, 3, 4):
        return False
    if p.age <= 0:
        return False
    return True


def assemble_xi(pool: Iterable[PlayerRecord],
                formation: str,
                *,
                allow_cross_position: bool = False,
                eligibility: Callable[[PlayerRecord], bool] = _is_eligible,
                ) -> list[RoleAssignment]:
    """Assemble the best XI for ``formation`` from ``pool``.

    Global-greedy assignment: score every (player, slot) pair, pick the highest
    fit, assign, remove both sides, repeat. Better than slot-order greedy for
    mixed-role formations. Returns exactly ``len(FORMATION_ROLES[formation])``
    assignments in formation order; raises ``ValueError`` if the pool can't
    fill the formation under the current eligibility rules.
    """
    if formation not in FORMATION_ROLES:
        raise ValueError(f"unknown formation {formation!r}; "
                         f"choices: {list(FORMATION_ROLES)}")
    slots = FORMATION_ROLES[formation]
    candidates = [p for p in pool if eligibility(p)]
    if not allow_cross_position:
        # Players can only fill a slot whose position byte matches theirs.
        # This is the safer default — PM's on-pitch behaviour for off-position
        # play is unknown.
        pass  # filtering happens in the scoring loop via the penalty+position check

    # Build (slot_index, player_index, fit) triples.
    pairs: list[tuple[int, int, float]] = []
    for si, role_key in enumerate(slots):
        role_pos = ROLES[role_key]["position"]
        for pi, p in enumerate(candidates):
            if not allow_cross_position and p.position != role_pos:
                continue
            pairs.append((si, pi, role_fit(p, role_key)))
    pairs.sort(key=lambda t: t[2], reverse=True)

    assigned_slot: dict[int, tuple[int, float]] = {}
    used_players: set[int] = set()
    for si, pi, fit in pairs:
        if si in assigned_slot or pi in used_players:
            continue
        assigned_slot[si] = (pi, fit)
        used_players.add(pi)
        if len(assigned_slot) == len(slots):
            break

    if len(assigned_slot) < len(slots):
        missing = [slots[i] for i in range(len(slots)) if i not in assigned_slot]
        raise ValueError(
            f"cannot fill formation {formation}: missing {missing}. "
            f"Pool size {len(candidates)}; try --allow-cross-position."
        )

    out: list[RoleAssignment] = []
    for si, role_key in enumerate(slots):
        pi, fit = assigned_slot[si]
        out.append(RoleAssignment(role=role_key, player=candidates[pi], fit=fit))
    return out


def assemble_matchday_squad(pool: Iterable[PlayerRecord],
                            formation: str,
                            *,
                            n_reserves: int = 2,
                            backup_gk: bool = True,
                            allow_cross_position: bool = False,
                            eligibility: Callable[[PlayerRecord], bool] = _is_eligible,
                            weights: Optional[dict[str, float]] = None,
                            ) -> MatchdaySquad:
    """Return the starting XI plus a bench of ``n_reserves`` players.

    When ``backup_gk`` is True (default) and the pool contains at least one
    eligible goalkeeper outside the XI, the first reserve is the best such
    GK. Remaining reserves are the eligible non-XI outfielders with the
    highest ``total_skill``; each carries the role returned by
    ``best_role_in_position`` so the GUI/CLI can label where they'd slot in.

    The bench is silently truncated when the pool has fewer spare players
    than ``n_reserves`` — the starting XI is the hard constraint.
    """
    if n_reserves < 0:
        raise ValueError(f"n_reserves must be ≥ 0, got {n_reserves}")

    pool_list = list(pool)
    xi = assemble_xi(pool_list, formation,
                     allow_cross_position=allow_cross_position,
                     eligibility=eligibility)
    composite, breakdown = score_xi(xi, weights=weights)

    xi_ids = {id(a.player) for a in xi}
    bench_pool = [p for p in pool_list
                  if eligibility(p) and id(p) not in xi_ids]

    reserves: list[RoleAssignment] = []
    picked: set[int] = set()

    if backup_gk and n_reserves > 0:
        gk_candidates = [p for p in bench_pool if p.position == 1]
        if gk_candidates:
            gk = max(gk_candidates, key=lambda p: role_fit(p, "GK"))
            reserves.append(RoleAssignment(
                role="GK", player=gk, fit=role_fit(gk, "GK"),
            ))
            picked.add(id(gk))

    remaining = [p for p in bench_pool if id(p) not in picked]
    remaining.sort(key=lambda p: p.total_skill, reverse=True)
    for p in remaining:
        if len(reserves) >= n_reserves:
            break
        role_key, fit = best_role_in_position(p)
        reserves.append(RoleAssignment(role=role_key, player=p, fit=fit))

    return MatchdaySquad(
        formation=formation, xi=xi, reserves=reserves,
        composite=composite, breakdown=breakdown,
    )


# ────────────────────────────────────────────────────────────────────────
# Composite XI scoring
# ────────────────────────────────────────────────────────────────────────

def _fatigue_index(p: PlayerRecord, squad_mean_matches: float) -> float:
    """0..1 fatigue indicator: over-played relative to squad mean.

    Blends recent match load and inverse stamina.
    """
    overload = 0.0
    if squad_mean_matches > 0:
        overload = max(0.0, (p.matches_this_year - squad_mean_matches)
                       / max(1.0, squad_mean_matches))
    stamina_gap = max(0.0, (_MAX_SKILL - p.stamina) / _MAX_SKILL)
    return min(1.0, 0.5 * overload + 0.5 * stamina_gap)


def _card_risk(p: PlayerRecord) -> float:
    """0..1 — blend of aggression and accumulated disciplinary points."""
    aggression = _norm_skill(p.aggression)
    dsp = min(1.0, p.dsp_pts_this_year / 20.0)  # arbitrary scale; tune later
    return min(1.0, 0.5 * aggression + 0.5 * dsp)


def _form_index(p: PlayerRecord) -> float:
    """Forwards: goals-per-match ratio this season, capped."""
    if p.position != 4 or p.matches_this_year <= 0:
        return 0.0
    return min(1.0, p.goals_this_year / max(1, p.matches_this_year))


def score_xi(assignments: list[RoleAssignment],
             *,
             weights: Optional[dict[str, float]] = None,
             ) -> tuple[float, dict[str, float]]:
    """Score a proposed XI with its component breakdown.

    Returns (composite, breakdown) where breakdown contains the raw and
    weight-contributing values for skill, fit, morale, fatigue, card_risk,
    form. All breakdown values are human-readable (not pre-multiplied).
    """
    if not assignments:
        return 0.0, {}
    w = dict(DEFAULT_COMPOSITE_WEIGHTS)
    if weights:
        w.update(weights)

    n = len(assignments)
    players = [a.player for a in assignments]
    mean_matches = sum(p.matches_this_year for p in players) / n

    total_skill = sum(p.total_skill for p in players)
    mean_fit = sum(a.fit for a in assignments) / n
    mean_morale = sum(p.morale for p in players) / (n * 255) if n else 0.0
    mean_fatigue = sum(_fatigue_index(p, mean_matches) for p in players) / n
    mean_card = sum(_card_risk(p) for p in players) / n
    mean_form = (sum(_form_index(p) for p in players
                     if p.position == 4) / max(1, sum(1 for p in players
                                                       if p.position == 4)))

    breakdown = {
        "total_skill": total_skill,
        "mean_fit":    mean_fit,
        "mean_morale": mean_morale,
        "mean_fatigue": mean_fatigue,
        "mean_card_risk": mean_card,
        "mean_form":   mean_form,
    }

    composite = (
        w["skill"]     * total_skill
      + w["fit"]       * mean_fit
      + w["morale"]    * mean_morale
      - w["fatigue"]   * mean_fatigue
      - w["card_risk"] * mean_card
      + w["form"]      * mean_form
    )
    return composite, breakdown


# ────────────────────────────────────────────────────────────────────────
# Reassignment suggestions
# ────────────────────────────────────────────────────────────────────────

def suggest_reassignments(pool: Iterable[PlayerRecord],
                          *,
                          threshold: float = 0.15,
                          ) -> list[ReassignmentSuggestion]:
    """Flag players whose best-fit role is outside their nominal position.

    A suggestion is emitted when ``best_fit - nominal_fit ≥ threshold`` AND
    the best role's position byte differs from the player's nominal position.
    Returns the list sorted by ``gap`` descending.
    """
    out: list[ReassignmentSuggestion] = []
    for p in pool:
        if p.position not in (1, 2, 3, 4) or p.age <= 0:
            continue
        nominal_name, nominal_fit = best_role_in_position(p)
        best_name, best_fit = best_role(p)
        if ROLES[best_name]["position"] == p.position:
            continue  # best role is already within nominal position
        gap = best_fit - nominal_fit
        if gap >= threshold:
            out.append(ReassignmentSuggestion(
                player=p,
                nominal_role=nominal_name, nominal_fit=nominal_fit,
                best_role=best_name, best_fit=best_fit,
                gap=gap,
            ))
    out.sort(key=lambda s: s.gap, reverse=True)
    return out


# ────────────────────────────────────────────────────────────────────────
# Formation ranking
# ────────────────────────────────────────────────────────────────────────

def rank_formations(pool: Iterable[PlayerRecord],
                    *,
                    formations: Optional[Iterable[str]] = None,
                    weights: Optional[dict[str, float]] = None,
                    allow_cross_position: bool = False,
                    ) -> list[LineupResult]:
    """Return the candidate formations ranked by composite XI score.

    Formations that can't be filled from ``pool`` are silently skipped.
    """
    keys = list(formations) if formations is not None else list(FORMATION_ROLES)
    pool_list = list(pool)
    results: list[LineupResult] = []
    for f in keys:
        try:
            xi = assemble_xi(pool_list, f, allow_cross_position=allow_cross_position)
        except ValueError:
            continue
        composite, breakdown = score_xi(xi, weights=weights)
        results.append(LineupResult(
            formation=f, assignments=xi,
            composite=composite, breakdown=breakdown,
        ))
    results.sort(key=lambda r: r.composite, reverse=True)
    return results
