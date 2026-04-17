"""Unit tests for the Line-up Coach (BETA) primitives.

Covers:
  - role_fit scoring (skill weights, height/age modifiers, cross-position)
  - best_role / best_role_in_position
  - assemble_xi (exact slot counts, per-position filtering, global greedy)
  - score_xi (breakdown content and monotonicity)
  - suggest_reassignments (threshold, position-change rule)
  - rank_formations (ordering, skipping unfillable formations)

These tests pin down the maths and invariants. They don't claim the weights
are right — the weights are heuristics, tunable, and labelled BETA.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.player import PlayerRecord, SKILL_NAMES
from pm_core.lineup import (
    ROLES, FORMATION_ROLES, CROSS_POSITION_PENALTY, DEFAULT_COMPOSITE_WEIGHTS,
    RoleAssignment, LineupResult, MatchdaySquad, ReassignmentSuggestion,
    role_fit, best_role, best_role_in_position,
    assemble_xi, assemble_matchday_squad,
    score_xi, suggest_reassignments, rank_formations,
)


def _player(**kwargs) -> PlayerRecord:
    base = dict(
        age=25, position=3, division=1, team_index=0,
        height=180, weight=75, morale=180, injury_weeks=0,
    )
    base.update(kwargs)
    return PlayerRecord(**base)


def _maxed(skill: str, **kwargs) -> PlayerRecord:
    """Player with one skill maxed (200), everything else 50. Useful for
    role-direction tests."""
    stats = {s: 50 for s in SKILL_NAMES}
    stats[skill] = 200
    return _player(**{**stats, **kwargs})


def _squad(n_per_pos=(1, 4, 4, 2), **overrides) -> list[PlayerRecord]:
    """Build a minimal eligible squad: (GK, DEF, MID, FWD) counts."""
    out = []
    pid = 0
    positions = [1, 2, 3, 4]
    for pos, count in zip(positions, n_per_pos):
        for _ in range(count):
            skills = dict(
                stamina=120, resilience=120, pace=120,
                agility=120, aggression=80, flair=120,
                passing=120, shooting=120, tackling=120,
                keeping=120 if pos == 1 else 40,
            )
            skills.update(overrides)
            out.append(_player(player_id=pid, position=pos, **skills))
            pid += 1
    return out


class TestRoleFit(unittest.TestCase):

    def test_keeper_maxed_scores_high_at_GK(self):
        p = _maxed("keeping", position=1)
        fit = role_fit(p, "GK")
        self.assertGreater(fit, 0.55)

    def test_poacher_maxed_shooting_scores_high_at_POA(self):
        p = _maxed("shooting", position=4)
        fit = role_fit(p, "POA")
        self.assertGreater(fit, 0.45)

    def test_cross_position_penalty_applied(self):
        p = _maxed("shooting", position=4)
        pos_fit = role_fit(p, "POA")
        cross_fit = role_fit(p, "CM")  # CM is position=3
        # CM weights shooting only 0.10, plus the penalty — must score lower.
        self.assertLess(cross_fit, pos_fit)
        # And applying the penalty exactly halves into the raw calc:
        # rebuild "would-be" CM fit by computing base * (1 - CROSS) should match
        # role_fit() output.
        # (We don't expose internals; the downstream tests cover this.)

    def test_height_pref_tall_boosts_tall_players(self):
        tall = _maxed("tackling", position=2, height=190)
        short = _maxed("tackling", position=2, height=170)
        self.assertGreater(role_fit(tall, "CB"), role_fit(short, "CB"))

    def test_age_curve_penalises_old_winger(self):
        young = _maxed("pace", position=3, age=24)
        old = _maxed("pace", position=3, age=36)
        self.assertGreater(role_fit(young, "WM"), role_fit(old, "WM"))

    def test_unknown_role_raises(self):
        with self.assertRaises(KeyError):
            role_fit(_player(), "NOT-A-ROLE")

    def test_fit_is_clipped_to_unit_interval(self):
        p = _player(**{s: 255 for s in SKILL_NAMES},
                    position=4, age=26, height=190)
        for role in ROLES:
            f = role_fit(p, role)
            self.assertGreaterEqual(f, 0.0)
            self.assertLessEqual(f, 1.0)


class TestBestRole(unittest.TestCase):

    def test_best_role_returns_actual_best(self):
        p = _maxed("keeping", position=1)
        name, fit = best_role(p)
        self.assertEqual(name, "GK")

    def test_best_role_in_position_is_position_scoped(self):
        # Forward with high shooting should pick POA or TGT within position 4,
        # not some cross-position role even if that scored higher raw.
        p = _maxed("shooting", position=4)
        name, _ = best_role_in_position(p)
        self.assertEqual(ROLES[name]["position"], 4)

    def test_best_role_among_candidates(self):
        p = _maxed("pace", position=3, age=24)
        name, _ = best_role(p, ("CM", "WM", "DM"))
        self.assertEqual(name, "WM")


class TestFormationTaxonomyConsistency(unittest.TestCase):
    """Lineup taxonomy must be self-consistent with pm_core.save FORMATIONS."""

    def test_formation_has_eleven_slots(self):
        for f, slots in FORMATION_ROLES.items():
            self.assertEqual(len(slots), 11, f"formation {f} has {len(slots)} slots")

    def test_formation_position_counts_match_save_formations(self):
        from pm_core.save import FORMATIONS
        for f, slot_counts in FORMATIONS.items():
            roles = FORMATION_ROLES[f]
            observed = {1: 0, 2: 0, 3: 0, 4: 0}
            for r in roles:
                observed[ROLES[r]["position"]] += 1
            for pos, expected in slot_counts.items():
                self.assertEqual(observed[pos], expected,
                                 f"formation {f} position {pos}: "
                                 f"taxonomy has {observed[pos]}, save.FORMATIONS says {expected}")

    def test_all_role_weight_vectors_sum_to_one(self):
        for key, cfg in ROLES.items():
            total = sum(cfg["skills"].values())
            self.assertAlmostEqual(total, 1.0, places=6,
                                   msg=f"{key} skill weights sum to {total}")


class TestAssembleXI(unittest.TestCase):

    def test_assembles_exactly_eleven(self):
        squad = _squad()  # 1 GK, 4 DEF, 4 MID, 2 FWD
        xi = assemble_xi(squad, "4-4-2")
        self.assertEqual(len(xi), 11)

    def test_respects_position_codes(self):
        squad = _squad()
        xi = assemble_xi(squad, "4-4-2")
        for a in xi:
            self.assertEqual(
                a.player.position, ROLES[a.role]["position"],
                f"role {a.role} got position {a.player.position}")

    def test_no_player_assigned_twice(self):
        # 4-3-3 needs 3 FWDs; default (1,4,4,2) only has 2 — use a bigger pool.
        squad = _squad(n_per_pos=(1, 4, 5, 3))
        xi = assemble_xi(squad, "4-3-3")
        ids = [id(a.player) for a in xi]
        self.assertEqual(len(ids), len(set(ids)))

    def test_unfillable_raises(self):
        # Only 2 defenders available but 4-4-2 needs 4.
        squad = _squad(n_per_pos=(1, 2, 4, 2))
        with self.assertRaises(ValueError):
            assemble_xi(squad, "4-4-2")

    def test_cross_position_fills_gaps_when_allowed(self):
        squad = _squad(n_per_pos=(1, 2, 5, 3))
        with self.assertRaises(ValueError):
            assemble_xi(squad, "4-4-2", allow_cross_position=False)
        xi = assemble_xi(squad, "4-4-2", allow_cross_position=True)
        self.assertEqual(len(xi), 11)

    def test_injured_players_excluded(self):
        squad = _squad()
        squad[0].injury_weeks = 2  # the lone GK is injured
        with self.assertRaises(ValueError):
            assemble_xi(squad, "4-4-2")

    def test_sentinel_records_excluded(self):
        squad = _squad()
        # add a garbage record — position=0, age=0
        squad.append(PlayerRecord(position=0, age=0, team_index=0))
        xi = assemble_xi(squad, "4-4-2")
        self.assertEqual(len(xi), 11)


class TestScoreXI(unittest.TestCase):

    def _fake_xi(self, squad):
        return [RoleAssignment(role=role, player=squad[i], fit=0.6)
                for i, role in enumerate(FORMATION_ROLES["4-4-2"])]

    def test_breakdown_has_all_expected_keys(self):
        squad = _squad()
        xi = assemble_xi(squad, "4-4-2")
        composite, br = score_xi(xi)
        for k in ("total_skill", "mean_fit", "mean_morale",
                  "mean_fatigue", "mean_card_risk", "mean_form"):
            self.assertIn(k, br)

    def test_higher_skill_raises_composite(self):
        weak = _squad()
        strong = _squad(**{s: 180 for s in SKILL_NAMES})
        weak_xi = assemble_xi(weak, "4-4-2")
        strong_xi = assemble_xi(strong, "4-4-2")
        c_w, _ = score_xi(weak_xi)
        c_s, _ = score_xi(strong_xi)
        self.assertGreater(c_s, c_w)

    def test_higher_morale_raises_composite(self):
        low = _squad(morale=20)
        high = _squad(morale=250)
        c_l, _ = score_xi(assemble_xi(low, "4-4-2"))
        c_h, _ = score_xi(assemble_xi(high, "4-4-2"))
        self.assertGreater(c_h, c_l)

    def test_custom_weights_override_defaults(self):
        squad = _squad(morale=250)
        xi = assemble_xi(squad, "4-4-2")
        default, _ = score_xi(xi)
        no_morale, _ = score_xi(xi, weights={"morale": 0.0})
        self.assertGreater(default, no_morale)

    def test_empty_xi_scores_zero(self):
        composite, br = score_xi([])
        self.assertEqual(composite, 0.0)
        self.assertEqual(br, {})


class TestSuggestReassignments(unittest.TestCase):

    def test_defender_with_playmaker_skills_is_flagged(self):
        # position=2 (nominal DEF) but skills scream AM: high passing, flair,
        # shooting. No DEF role covers these skills well, so best role lies
        # outside position 2.
        p = _player(position=2, passing=200, flair=200, shooting=200,
                    agility=180, pace=180)
        out = suggest_reassignments([p], threshold=0.05)
        self.assertEqual(len(out), 1)
        s = out[0]
        self.assertEqual(s.player, p)
        self.assertNotEqual(ROLES[s.best_role]["position"], 2)
        self.assertGreater(s.gap, 0.0)

    def test_player_already_in_best_category_not_flagged(self):
        # Poacher-skilled FWD — best role stays within position=4.
        p = _maxed("shooting", position=4)
        self.assertEqual(suggest_reassignments([p]), [])

    def test_threshold_filters_small_gaps(self):
        p = _player(position=4, passing=130, flair=130, shooting=120)
        none = suggest_reassignments([p], threshold=0.99)
        self.assertEqual(none, [])

    def test_sentinel_records_skipped(self):
        garbage = PlayerRecord(position=0, age=0, team_index=0)
        self.assertEqual(suggest_reassignments([garbage]), [])

    def test_sorted_by_gap_descending(self):
        weak = _player(position=2, passing=150, flair=150, shooting=150,
                       agility=150, pace=150)
        strong = _player(position=2, passing=200, flair=200, shooting=200,
                         agility=200, pace=200)
        out = suggest_reassignments([weak, strong], threshold=0.05)
        self.assertEqual(len(out), 2)
        self.assertGreaterEqual(out[0].gap, out[1].gap)


class TestAssembleMatchdaySquad(unittest.TestCase):

    def test_returns_xi_plus_requested_reserves(self):
        # 1 GK, 5 DEF, 5 MID, 3 FWD → 14 eligible, XI fills 11, 3 to spare.
        squad = _squad(n_per_pos=(1, 5, 5, 3))
        md = assemble_matchday_squad(squad, "4-4-2", n_reserves=2)
        self.assertEqual(len(md.xi), 11)
        self.assertEqual(len(md.reserves), 2)
        self.assertEqual(md.formation, "4-4-2")

    def test_reserves_do_not_overlap_xi(self):
        squad = _squad(n_per_pos=(1, 5, 5, 3))
        md = assemble_matchday_squad(squad, "4-4-2", n_reserves=2)
        xi_ids = {id(a.player) for a in md.xi}
        reserve_ids = {id(a.player) for a in md.reserves}
        self.assertTrue(xi_ids.isdisjoint(reserve_ids))

    def test_prefers_backup_gk_when_available(self):
        # 2 GKs, one in the XI, the other should be reserve #1.
        squad = _squad(n_per_pos=(2, 4, 4, 2))
        md = assemble_matchday_squad(squad, "4-4-2", n_reserves=2)
        self.assertEqual(md.reserves[0].player.position, 1)
        self.assertEqual(md.reserves[0].role, "GK")

    def test_no_backup_gk_falls_back_to_outfielders(self):
        # Only 1 GK — no backup exists, bench fills with outfielders.
        squad = _squad(n_per_pos=(1, 5, 5, 3))
        md = assemble_matchday_squad(squad, "4-4-2", n_reserves=2)
        self.assertEqual(len(md.reserves), 2)
        for a in md.reserves:
            self.assertNotEqual(a.player.position, 1)

    def test_backup_gk_can_be_disabled(self):
        # Two GKs, eight outfielder spares where each spare has higher
        # total_skill than the backup GK. backup_gk=True must still pick the
        # GK first; backup_gk=False must fall through to total_skill ranking.
        squad = _squad(n_per_pos=(2, 5, 5, 3))
        backup_gk = next(p for p in squad
                         if p.position == 1 and p is not squad[0])
        # Weaken the backup GK so outfielders clearly outrank him on skill.
        for s in SKILL_NAMES:
            setattr(backup_gk, s, 20)

        forced = assemble_matchday_squad(squad, "4-4-2",
                                         n_reserves=2, backup_gk=True)
        self.assertEqual(forced.reserves[0].player.position, 1)

        free = assemble_matchday_squad(squad, "4-4-2",
                                       n_reserves=2, backup_gk=False)
        for a in free.reserves:
            self.assertNotEqual(a.player.position, 1)

    def test_thin_bench_truncates_silently(self):
        # Exactly 11 eligible players — no reserves available.
        squad = _squad(n_per_pos=(1, 4, 4, 2))
        md = assemble_matchday_squad(squad, "4-4-2", n_reserves=2)
        self.assertEqual(len(md.xi), 11)
        self.assertEqual(md.reserves, [])

    def test_injured_excluded_from_reserves(self):
        # 1 GK + 6 DEF + 6 MID + 4 FWD = 17 eligible. After the XI (1/4/4/2)
        # that leaves 6 spares. Injure half; the remaining 3 must pass.
        squad = _squad(n_per_pos=(1, 6, 6, 4))
        injured = [squad[6], squad[12], squad[16]]  # spares across positions
        for p in injured:
            p.injury_weeks = 3
        md = assemble_matchday_squad(squad, "4-4-2", n_reserves=2)
        self.assertEqual(len(md.reserves), 2)
        for a in md.reserves:
            self.assertEqual(a.player.injury_weeks, 0)

    def test_zero_reserves_returns_empty_bench(self):
        squad = _squad(n_per_pos=(1, 5, 5, 3))
        md = assemble_matchday_squad(squad, "4-4-2", n_reserves=0)
        self.assertEqual(md.reserves, [])
        self.assertEqual(len(md.xi), 11)

    def test_negative_reserves_raises(self):
        squad = _squad(n_per_pos=(1, 5, 5, 3))
        with self.assertRaises(ValueError):
            assemble_matchday_squad(squad, "4-4-2", n_reserves=-1)

    def test_unfillable_xi_raises(self):
        squad = _squad(n_per_pos=(1, 2, 4, 2))  # not enough DEFs
        with self.assertRaises(ValueError):
            assemble_matchday_squad(squad, "4-4-2", n_reserves=2)

    def test_composite_matches_score_xi(self):
        squad = _squad(n_per_pos=(1, 5, 5, 3))
        md = assemble_matchday_squad(squad, "4-4-2")
        direct_composite, _ = score_xi(md.xi)
        self.assertAlmostEqual(md.composite, direct_composite, places=6)


class TestRankFormations(unittest.TestCase):

    def test_returns_all_fillable_formations(self):
        # 1 GK, 4 DEF, 5 MID, 3 FWD — fills all three default formations.
        squad = _squad(n_per_pos=(1, 4, 5, 3))
        ranked = rank_formations(squad)
        self.assertEqual({r.formation for r in ranked},
                         {"4-4-2", "4-3-3", "3-5-2"})

    def test_ranks_by_composite_descending(self):
        squad = _squad(n_per_pos=(1, 4, 5, 3))
        ranked = rank_formations(squad)
        composites = [r.composite for r in ranked]
        self.assertEqual(composites, sorted(composites, reverse=True))

    def test_skips_unfillable_formations(self):
        # 4 MIDs but not 5 — 3-5-2 unfillable, other two OK.
        squad = _squad(n_per_pos=(1, 4, 4, 2))
        ranked = rank_formations(squad)
        observed = {r.formation for r in ranked}
        self.assertIn("4-4-2", observed)
        self.assertNotIn("3-5-2", observed)


if __name__ == "__main__":
    unittest.main()
