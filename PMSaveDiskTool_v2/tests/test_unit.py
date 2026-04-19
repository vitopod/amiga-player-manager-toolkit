"""ADF-independent unit tests. Safe to run in CI without a real save disk."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.player import (
    PlayerRecord, parse_player, serialize_player,
    RECORD_SIZE, SKILL_NAMES,
)
from pm_core.save import SaveSlot, FORMATIONS


class TestPlayerRecordProperties(unittest.TestCase):
    def test_is_free_agent(self):
        self.assertTrue(PlayerRecord(team_index=0xFF).is_free_agent)
        self.assertFalse(PlayerRecord(team_index=0).is_free_agent)
        self.assertFalse(PlayerRecord(team_index=43).is_free_agent)

    def test_is_transfer_listed_bit(self):
        self.assertFalse(PlayerRecord(mystery3=0x00).is_transfer_listed)
        self.assertFalse(PlayerRecord(mystery3=0x7F).is_transfer_listed)
        self.assertTrue(PlayerRecord(mystery3=0x80).is_transfer_listed)
        self.assertTrue(PlayerRecord(mystery3=0xFF).is_transfer_listed)

    def test_is_market_available_union(self):
        self.assertTrue(PlayerRecord(team_index=0xFF, mystery3=0x00).is_market_available)
        self.assertTrue(PlayerRecord(team_index=0, mystery3=0x80).is_market_available)
        self.assertTrue(PlayerRecord(team_index=0xFF, mystery3=0x80).is_market_available)
        self.assertFalse(PlayerRecord(team_index=0, mystery3=0x00).is_market_available)

    def test_total_skill_sums_ten_skills(self):
        p = PlayerRecord(**{name: 10 for name in SKILL_NAMES})
        self.assertEqual(p.total_skill, 100)

    def test_position_name(self):
        self.assertEqual(PlayerRecord(position=1).position_name, "GK")
        self.assertEqual(PlayerRecord(position=4).position_name, "FWD")
        self.assertEqual(PlayerRecord(position=0).position_name, "???")


class TestParseSerializeRoundTrip(unittest.TestCase):
    def test_zero_record(self):
        data = bytes(RECORD_SIZE)
        p = parse_player(data, player_id=7)
        self.assertEqual(p.player_id, 7)
        self.assertEqual(serialize_player(p), data)

    def test_full_record(self):
        data = bytes(range(RECORD_SIZE))
        p = parse_player(data)
        self.assertEqual(serialize_player(p), data)

    def test_all_byte_values(self):
        data = bytes([(i * 7 + 3) & 0xFF for i in range(RECORD_SIZE)])
        p = parse_player(data)
        self.assertEqual(serialize_player(p), data)

    def test_parse_too_short_raises(self):
        with self.assertRaises(ValueError):
            parse_player(bytes(RECORD_SIZE - 1))


class TestRealPlayerFilter(unittest.TestCase):
    def _base(self, **kwargs):
        defaults = dict(age=25, position=3, team_index=0, height=180, weight=75)
        defaults.update(kwargs)
        return PlayerRecord(**defaults)

    def test_accepts_regular_player(self):
        self.assertTrue(SaveSlot._is_real_player(self._base()))

    def test_accepts_free_agent(self):
        self.assertTrue(SaveSlot._is_real_player(self._base(team_index=0xFF)))

    def test_rejects_zero_age(self):
        self.assertFalse(SaveSlot._is_real_player(self._base(age=0)))

    def test_rejects_invalid_position(self):
        self.assertFalse(SaveSlot._is_real_player(self._base(position=0)))
        self.assertFalse(SaveSlot._is_real_player(self._base(position=5)))

    def test_rejects_invalid_team_index(self):
        self.assertFalse(SaveSlot._is_real_player(self._base(team_index=44)))
        self.assertFalse(SaveSlot._is_real_player(self._base(team_index=100)))

    def test_rejects_uninitialised_physicals(self):
        self.assertFalse(SaveSlot._is_real_player(self._base(height=50)))
        self.assertFalse(SaveSlot._is_real_player(self._base(weight=0)))


class TestFormations(unittest.TestCase):
    def test_each_formation_sums_to_eleven(self):
        for name, slots in FORMATIONS.items():
            self.assertEqual(sum(slots.values()), 11, f"{name} doesn't total 11")

    def test_every_formation_has_one_goalkeeper(self):
        for name, slots in FORMATIONS.items():
            self.assertEqual(slots.get(1), 1, f"{name} needs exactly 1 GK")

    def test_expected_formations_present(self):
        for f in ("4-4-2", "4-3-3", "3-5-2"):
            self.assertIn(f, FORMATIONS)


class TestTopNPerPosition(unittest.TestCase):
    """Tests for the _top_n_per_position helper in pm_gui."""

    def _make_player(self, position: int, total_skill_val: int,
                     team_index: int = 0) -> PlayerRecord:
        """Build a minimal PlayerRecord with the given position and skill sum."""
        # Distribute total_skill_val evenly across the 10 skill fields.
        # If not divisible by 10, put the remainder in keeping.
        base = total_skill_val // 10
        extra = total_skill_val % 10
        return PlayerRecord(
            position=position,
            team_index=team_index,
            keeping=base + extra,
            tackling=base,
            passing=base,
            shooting=base,
            stamina=base,
            pace=base,
            agility=base,
            flair=base,
            resilience=base,
            aggression=base,
        )

    def _top_n(self, players, n=3):
        """Inline copy of the helper — replaced by import once Task 3 is done."""
        groups: dict[int, list] = {1: [], 2: [], 3: [], 4: []}
        for p in players:
            if p.position in groups:
                groups[p.position].append(p)
        result = []
        for pos in (1, 2, 3, 4):
            result.extend(
                sorted(groups[pos], key=lambda p: p.total_skill, reverse=True)[:n]
            )
        return result

    def test_keeps_top_n_per_position(self):
        """Top 3 per position are returned in skill order."""
        players = [
            self._make_player(1, 100),  # GK best
            self._make_player(1, 80),
            self._make_player(1, 60),
            self._make_player(1, 40),   # GK 4th — should be excluded
            self._make_player(2, 90),   # DEF
            self._make_player(2, 70),
        ]
        result = self._top_n(players, n=3)
        gks = [p for p in result if p.position == 1]
        defs = [p for p in result if p.position == 2]
        self.assertEqual(len(gks), 3)
        self.assertEqual(gks[0].total_skill, 100)
        self.assertEqual(gks[2].total_skill, 60)
        self.assertEqual(len(defs), 2)  # only 2 DEF available

    def test_position_order(self):
        """Result is GK → DEF → MID → FWD."""
        players = [
            self._make_player(4, 50),
            self._make_player(3, 50),
            self._make_player(2, 50),
            self._make_player(1, 50),
        ]
        result = self._top_n(players)
        positions = [p.position for p in result]
        self.assertEqual(positions, [1, 2, 3, 4])

    def test_fewer_than_n_in_position(self):
        """If a position has fewer than n players, returns all of them."""
        players = [self._make_player(1, 100)]  # only 1 GK
        result = self._top_n(players, n=3)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].total_skill, 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
