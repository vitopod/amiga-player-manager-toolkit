#!/usr/bin/env python3
"""Tests verifying PMSaveDiskTool v2 against the real Save1_PM.adf file.

Run: python -m pytest tests/ -v   (from PMSaveDiskTool_v2 directory)
  or: python tests/test_read_save.py
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.adf import ADF
from pm_core.save import SaveSlot
from pm_core.player import parse_player, serialize_player, RECORD_SIZE

# Path to the test ADF file
TEST_ADF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "PMSaveDiskTool_v1.2", "Save1_PM.adf"
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

    def test_db_header(self):
        self.assertIn(self.slot.db_header, [1, 2, 3, 4])


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
