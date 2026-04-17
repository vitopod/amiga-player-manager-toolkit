#!/usr/bin/env python3
"""Tests verifying PMSaveDiskToolkit against the real Save1_PM.adf file.

Run: python -m pytest tests/ -v   (from PMSaveDiskTool_v2 directory)
  or: python tests/test_read_save.py
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.adf import ADF
from pm_core.save import SaveSlot, FORMATIONS
from pm_core.player import parse_player, serialize_player, RECORD_SIZE

# Path to the test ADF file
TEST_ADF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "PMSaveDiskTool_v1.2", "Save1_PM.adf"
)

# Optional English/BETA paths — tests gated on their existence.
_EN_SAVE_ADF = os.environ.get("PM_EN_SAVE_ADF",
                              "/Users/simone/Downloads/20101112.adf")
_EN_GAME_ADF = os.environ.get(
    "PM_EN_GAME_ADF",
    "/Users/simone/Downloads/Player Manager (1990)(Anco)[cr OCL] EN.adf",
)


class TestADF(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)

    def test_adf_size(self):
        self.assertEqual(len(self.adf._data), 901120)

    def test_file_table_count(self):
        files = self.adf.list_files()
        self.assertEqual(len(files), 18)

    def test_file_table_names(self):
        names = [f.name for f in self.adf.list_files()]
        self.assertIn("data.disk", names)
        self.assertIn("PM1.nam", names)
        self.assertIn("start.dat", names)
        self.assertIn("pm1.sav", names)
        self.assertIn("pm7.sav", names)

    def test_data_disk_marker(self):
        data = self.adf.read_file("data.disk")
        self.assertEqual(len(data), 10)
        self.assertTrue(data.startswith(b"data.disk\x00"))

    def test_save_files_size(self):
        for save in self.adf.list_saves():
            self.assertEqual(save.size, 4408, f"{save.name} size mismatch")

    def test_list_saves(self):
        saves = self.adf.list_saves()
        save_names = [s.name for s in saves]
        self.assertEqual(len(saves), 7)
        for i in range(1, 8):
            self.assertIn(f"pm{i}.sav", save_names)

    def test_find_file_case_insensitive(self):
        entry = self.adf.find_file("PM1.NAM")
        self.assertEqual(entry.name, "PM1.nam")

    def test_find_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.adf.find_file("nonexistent.xyz")


class TestSaveSlot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)
        cls.slot = SaveSlot(cls.adf, "pm1.sav")

    def test_team_names(self):
        self.assertEqual(len(self.slot.team_names), 44)
        self.assertEqual(self.slot.team_names[0], "MILAN")
        self.assertEqual(self.slot.team_names[1], "SAMPDORIA")
        self.assertEqual(self.slot.team_names[4], "NAPOLI")
        self.assertEqual(self.slot.team_names[43], "OLBIA")

    def test_player_count(self):
        self.assertEqual(len(self.slot.players), 1536)

    def test_player_0(self):
        p = self.slot.get_player(0)
        self.assertEqual(p.age, 25)
        self.assertEqual(p.position, 2)  # DEF
        self.assertEqual(p.position_name, "DEF")
        self.assertEqual(p.division, 1)
        self.assertEqual(p.team_index, 0)
        self.assertEqual(p.height, 164)
        self.assertEqual(p.weight, 64)

    def test_player_1(self):
        p = self.slot.get_player(1)
        self.assertEqual(p.age, 19)
        self.assertEqual(p.position, 3)  # MID
        self.assertEqual(p.position_name, "MID")
        self.assertEqual(p.team_index, 0)

    def test_player_skills_range(self):
        for p in self.slot.players:
            if p.age == 0:
                continue
            for skill_name in ["stamina", "resilience", "pace", "agility",
                               "aggression", "flair", "passing", "shooting",
                               "tackling", "keeping"]:
                val = getattr(p, skill_name)
                self.assertGreaterEqual(val, 0,
                    f"Player {p.player_id} {skill_name}={val} < 0")
                self.assertLessEqual(val, 255,
                    f"Player {p.player_id} {skill_name}={val} > 255")

    def test_team_filtering(self):
        team0_players = self.slot.get_players_by_team(0)
        self.assertGreater(len(team0_players), 0)
        for p in team0_players:
            self.assertEqual(p.team_index, 0)

    def test_free_agents(self):
        free = self.slot.get_free_agents()
        for p in free:
            self.assertEqual(p.team_index, 0xFF)

    def test_team_name_lookup(self):
        self.assertEqual(self.slot.get_team_name(0), "MILAN")
        self.assertEqual(self.slot.get_team_name(0xFF), "Free Agent")

    def test_team_names_from_save_is_true_when_pm1_nam_present(self):
        # The Italian save has PM1.nam; flag must reflect that so the
        # game-disk fallback stays a no-op.
        self.assertTrue(self.slot.team_names_from_save)

    def test_apply_team_name_fallback_is_noop_when_save_has_names(self):
        before = list(self.slot.team_names)
        changed = self.slot.apply_team_name_fallback(
            ["OVERRIDE"] * 44
        )
        self.assertFalse(changed)
        self.assertEqual(self.slot.team_names, before)

    def test_db_header(self):
        self.assertIn(self.slot.db_header, [1, 2, 3, 4])


class TestTeamNameStandingsShift(unittest.TestCase):
    """player.team_index is 1-based against the save's own standings
    records: team_index N references save record[N-1]. Across the season
    teams promote/relegate and records re-sort, so PM1.nam (which is the
    initial/static order) goes stale for saves past pm1. HURGADA is at
    record[19] in pm1 (team_index 20), but at record[6] in pm6/pm7
    (team_index 7). The lookup must follow the save's current layout.
    """

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)

    def _find_team_index(self, slot, name):
        return next((i for i, n in enumerate(slot.team_names) if n == name),
                    None)

    def test_hurgada_moves_between_saves(self):
        # All seven saves were manager-played on the same season, so HURGADA
        # should still exist but at a different team_index in each save.
        slots = {n: SaveSlot(self.adf, n)
                 for n in [f"pm{i}.sav" for i in range(1, 8)]}
        indices = {name: self._find_team_index(s, "HURGADA")
                   for name, s in slots.items()}
        for name, idx in indices.items():
            self.assertIsNotNone(idx, f"{name}: HURGADA not found")
        # pm1 keeps the initial PM1.nam position; later saves differ.
        self.assertEqual(indices["pm1.sav"], 20)
        self.assertNotEqual(indices["pm6.sav"], 20)
        self.assertNotEqual(indices["pm7.sav"], 20)

    def test_team_index_0_is_user_team_placeholder(self):
        slot = SaveSlot(self.adf, "pm6.sav")
        # Italian save keeps PM1.nam for the user's team label.
        self.assertEqual(slot.team_names[0], "MILAN")


@unittest.skipUnless(os.path.isfile(_EN_SAVE_ADF) and os.path.isfile(_EN_GAME_ADF),
                     "English save or game ADF not available")
class TestEnglishSaveTeamNames(unittest.TestCase):
    """English/BETA saves lack PM1.nam but still carry team names inside
    each save's 44 × 100-byte team records (same layout as Italian saves).
    Names are populated straight from those records."""

    @classmethod
    def setUpClass(cls):
        from pm_core.names import GameDisk
        cls.adf = ADF.load(_EN_SAVE_ADF)
        save_name = cls.adf.list_saves()[0].name
        cls.slot = SaveSlot(cls.adf, save_name)
        cls.gd = GameDisk.load(_EN_GAME_ADF)

    def test_names_sourced_from_save_records(self):
        self.assertTrue(self.slot.team_names_from_save)
        # team_names[0] is the user's team (no save record); fall back to
        # placeholder since the English save has no PM1.nam.
        self.assertEqual(self.slot.team_names[0], "Team 0")
        # team_names[i>=1] = save record[i-1]. Two known English clubs
        # confirmed from the first save on this disk.
        self.assertIn("LIVERPOOL", self.slot.team_names[1:])
        self.assertIn("CHELSEA", self.slot.team_names[1:])

    def test_fallback_is_noop_when_records_populated(self):
        before = list(self.slot.team_names)
        changed = self.slot.apply_team_name_fallback(self.gd.team_names)
        self.assertFalse(changed)
        self.assertEqual(self.slot.team_names, before)


class TestBestXI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)
        cls.slot = SaveSlot(cls.adf, "pm1.sav")

    def test_best_xi_442_counts(self):
        xi = self.slot.best_xi("4-4-2")
        self.assertEqual(len(xi), 11)
        counts = {pos: sum(1 for p in xi if p.position == pos) for pos in (1, 2, 3, 4)}
        self.assertEqual(counts, {1: 1, 2: 4, 3: 4, 4: 2})

    def test_best_xi_433_counts(self):
        xi = self.slot.best_xi("4-3-3")
        counts = {pos: sum(1 for p in xi if p.position == pos) for pos in (1, 2, 3, 4)}
        self.assertEqual(counts, {1: 1, 2: 4, 3: 3, 4: 3})

    def test_best_xi_ordered_by_position(self):
        xi = self.slot.best_xi("4-4-2")
        positions = [p.position for p in xi]
        self.assertEqual(positions, sorted(positions))

    def test_best_xi_sorted_within_position(self):
        xi = self.slot.best_xi("4-4-2")
        for pos in (1, 2, 3, 4):
            group = [p.total_skill for p in xi if p.position == pos]
            self.assertEqual(group, sorted(group, reverse=True),
                             f"position {pos} not sorted desc")

    def test_best_xi_excludes_garbage(self):
        xi = self.slot.best_xi("4-4-2")
        for p in xi:
            self.assertTrue(SaveSlot._is_real_player(p),
                            f"player {p.player_id} failed real-player check")

    def test_best_xi_young_filter(self):
        xi = self.slot.best_xi("4-4-2", filter_fn=lambda p: p.age <= 21)
        self.assertEqual(len(xi), 11)
        for p in xi:
            self.assertLessEqual(p.age, 21)

    def test_best_xi_max_per_team_cap(self):
        cap = 1
        xi = self.slot.best_xi("4-4-2", max_per_team=cap)
        team_counts = {}
        for p in xi:
            if p.team_index == 0xFF:
                continue
            team_counts[p.team_index] = team_counts.get(p.team_index, 0) + 1
        for team, n in team_counts.items():
            self.assertLessEqual(n, cap, f"team {team} has {n} players (cap {cap})")

    def test_best_xi_unknown_formation_raises(self):
        with self.assertRaises(ValueError):
            self.slot.best_xi("bogus")


class TestTransferListFlag(unittest.TestCase):
    """Verify mystery3 & 0x80 flags the in-game LISTA TRASFERIMENTI.

    Nine player IDs confirmed visually in the in-game transfer-list screen
    for Save1 pm1.sav. If the save-disk contents change, these IDs may need
    to be refreshed.
    """
    KNOWN_LISTED_IDS = [125, 96, 327, 806, 22, 907, 884, 680, 465]

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)
        cls.slot = SaveSlot(cls.adf, "pm1.sav")

    def test_known_listed_players_have_flag(self):
        for pid in self.KNOWN_LISTED_IDS:
            p = self.slot.get_player(pid)
            self.assertTrue(p.is_transfer_listed,
                            f"player {pid} missing transfer-list flag "
                            f"(mystery3=0x{p.mystery3:02x})")

    def test_market_available_covers_free_agents_and_listed(self):
        for pid in self.KNOWN_LISTED_IDS:
            self.assertTrue(self.slot.get_player(pid).is_market_available)
        for p in self.slot.get_free_agents():
            self.assertTrue(p.is_market_available)


class TestUnknownFieldObservations(unittest.TestCase):
    """Regression tests for empirically-observed invariants in the unknown
    bytes (see player.py docstrings for details). If a real counterexample
    ever shows up, these tests will fire and the interpretation can be
    refined.
    """

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)
        cls.slot = SaveSlot(cls.adf, "pm1.sav")
        cls.real = [p for p in cls.slot.players if SaveSlot._is_real_player(p)]

    def test_reserved_byte_is_always_zero(self):
        for p in self.real:
            self.assertEqual(p.reserved, 0,
                             f"player {p.player_id}: reserved != 0")

    def test_mystery3_bit5_never_set(self):
        for p in self.real:
            self.assertEqual(p.mystery3 & 0x20, 0,
                             f"player {p.player_id}: mystery3 bit 5 set "
                             f"(0x{p.mystery3:02x})")

    def test_last_byte_in_expected_range(self):
        for p in self.real:
            self.assertIn(p.last_byte, (1, 2, 3, 4, 5),
                          f"player {p.player_id}: last_byte={p.last_byte} "
                          "outside observed 1..5 range")


class TestSquadSummary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)
        cls.slot = SaveSlot(cls.adf, "pm1.sav")

    def test_squad_summary_shape(self):
        s = self.slot.squad_summary(0)
        for key in ("team_index", "team_name", "size", "by_position",
                    "avg_age", "avg_skill", "min_age", "max_age",
                    "youngest", "oldest", "best", "on_market"):
            self.assertIn(key, s)
        self.assertEqual(s["team_index"], 0)
        self.assertEqual(s["team_name"], "MILAN")

    def test_squad_summary_counts_match_roster(self):
        s = self.slot.squad_summary(0)
        roster = [p for p in self.slot.get_players_by_team(0)
                  if SaveSlot._is_real_player(p)]
        self.assertEqual(s["size"], len(roster))
        total_by_pos = sum(s["by_position"].values())
        self.assertEqual(total_by_pos, s["size"])

    def test_squad_summary_extremes_are_consistent(self):
        s = self.slot.squad_summary(0)
        self.assertEqual(s["youngest"].age, s["min_age"])
        self.assertEqual(s["oldest"].age, s["max_age"])
        # best has the highest total_skill in the roster
        roster = [p for p in self.slot.get_players_by_team(0)
                  if SaveSlot._is_real_player(p)]
        self.assertEqual(s["best"].total_skill,
                         max(p.total_skill for p in roster))

    def test_squad_summary_averages_in_range(self):
        s = self.slot.squad_summary(0)
        self.assertGreaterEqual(s["avg_age"], s["min_age"])
        self.assertLessEqual(s["avg_age"], s["max_age"])

    def test_squad_summary_empty_team(self):
        # Team index 43 ("OLBIA") exists; pick a definitely-empty-ish case
        # by using a non-existent team index within the valid range.
        # Instead, synthetically ask for a team with no members by choosing
        # a team index that has zero real players. If none exists, skip.
        empty_idx = None
        for i in range(44):
            roster = [p for p in self.slot.get_players_by_team(i)
                      if SaveSlot._is_real_player(p)]
            if not roster:
                empty_idx = i
                break
        if empty_idx is None:
            self.skipTest("no empty teams in pm1.sav")
        s = self.slot.squad_summary(empty_idx)
        self.assertEqual(s["size"], 0)
        self.assertIsNone(s["youngest"])
        self.assertIsNone(s["oldest"])
        self.assertIsNone(s["best"])
        self.assertEqual(s["avg_age"], 0.0)
        self.assertEqual(s["avg_skill"], 0.0)

    def test_all_squad_summaries_skip_empty_teams(self):
        summaries = self.slot.all_squad_summaries()
        self.assertGreater(len(summaries), 0)
        for s in summaries:
            self.assertGreater(s["size"], 0)


class TestDiffPlayers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)
        cls.slot1 = SaveSlot(cls.adf, "pm1.sav")
        cls.slot2 = SaveSlot(cls.adf, "pm2.sav")

    def test_self_diff_is_empty(self):
        self.assertEqual(self.slot1.diff_players(self.slot1), [])

    def test_diff_shape(self):
        diffs = self.slot1.diff_players(self.slot2)
        if not diffs:
            self.skipTest("pm1.sav and pm2.sav are byte-identical")
        d = diffs[0]
        for key in ("player_id", "changed", "skill_delta", "age_delta",
                    "team_changed", "old", "new"):
            self.assertIn(key, d)
        self.assertIsInstance(d["changed"], dict)
        self.assertGreater(len(d["changed"]), 0)

    def test_diff_deltas_match_records(self):
        diffs = self.slot1.diff_players(self.slot2)
        if not diffs:
            self.skipTest("pm1.sav and pm2.sav are byte-identical")
        for d in diffs:
            self.assertEqual(d["skill_delta"],
                             d["new"].total_skill - d["old"].total_skill)
            self.assertEqual(d["age_delta"], d["new"].age - d["old"].age)
            self.assertEqual(d["team_changed"],
                             d["old"].team_index != d["new"].team_index)

    def test_diff_player_id_is_monotonic(self):
        diffs = self.slot1.diff_players(self.slot2)
        ids = [d["player_id"] for d in diffs]
        self.assertEqual(ids, sorted(ids))


class TestPlayerSerialization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists(TEST_ADF):
            raise unittest.SkipTest(f"Test ADF not found: {TEST_ADF}")
        cls.adf = ADF.load(TEST_ADF)
        cls.slot = SaveSlot(cls.adf, "pm1.sav")

    def test_roundtrip_all_players(self):
        """Verify that parse -> serialize produces identical bytes for every player."""
        entry = self.adf.find_file("pm1.sav")
        db_off = entry.byte_offset + entry.size + 2  # skip 2-byte header
        for i in range(1536):
            original = self.adf.read_at(db_off + i * RECORD_SIZE, RECORD_SIZE)
            player = parse_player(original, player_id=i)
            reserialized = serialize_player(player)
            self.assertEqual(original, reserialized,
                f"Round-trip mismatch for player {i}: "
                f"{original.hex()} != {reserialized.hex()}")

    def test_roundtrip_full_adf(self):
        """Verify that loading and saving an ADF produces identical bytes."""
        original_data = bytes(self.adf._data)
        with tempfile.NamedTemporaryFile(suffix=".adf", delete=False) as f:
            tmp_path = f.name
        try:
            self.adf.save(tmp_path)
            with open(tmp_path, "rb") as f:
                saved_data = f.read()
            self.assertEqual(original_data, saved_data)
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
