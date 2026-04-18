"""End-to-end smoke tests for pm_cli.py subcommands.

Uses subprocess.run against Save1_PM.adf. Skips if the ADF is not present.
Each test asserts exit code 0 and some expected marker in the output so a
regression in argument parsing, dispatch, or default formatting is caught.
"""

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_CLI = os.path.join(os.path.dirname(_HERE), "pm_cli.py")
_ADF = os.path.join(_ROOT, "PMSaveDiskTool_v1.2", "Save1_PM.adf")


def _run(*args, input_bytes=None):
    return subprocess.run(
        [sys.executable, _CLI, *args],
        capture_output=True, text=True, check=False, input=input_bytes,
    )


@unittest.skipUnless(os.path.isfile(_ADF), f"{_ADF} not available")
class TestCLISmoke(unittest.TestCase):

    def assertSuccess(self, result):
        self.assertEqual(result.returncode, 0,
                         f"stderr: {result.stderr}\nstdout: {result.stdout}")

    def test_version(self):
        r = _run("--version")
        self.assertSuccess(r)
        self.assertIn("PMSaveDiskTool", r.stdout)

    def test_list_saves(self):
        r = _run("list-saves", _ADF)
        self.assertSuccess(r)
        self.assertIn("pm1.sav", r.stdout)

    def test_list_players_team(self):
        r = _run("list-players", _ADF, "--save", "pm1.sav", "--team", "0")
        self.assertSuccess(r)
        self.assertIn("MILAN", r.stdout)

    def test_list_players_free_agents(self):
        r = _run("list-players", _ADF, "--save", "pm1.sav", "--free-agents")
        self.assertSuccess(r)
        self.assertIn("Free Agents", r.stdout)

    def test_show_player(self):
        r = _run("show-player", _ADF, "--save", "pm1.sav", "--id", "0")
        self.assertSuccess(r)
        self.assertIn("Player #0", r.stdout)
        self.assertIn("Skills:", r.stdout)

    def test_young_talents(self):
        r = _run("young-talents", _ADF, "--save", "pm1.sav")
        self.assertSuccess(r)
        self.assertIn("Young Talents", r.stdout)

    def test_highlights(self):
        r = _run("highlights", _ADF, "--save", "pm1.sav")
        self.assertSuccess(r)
        self.assertIn("Championship Highlights", r.stdout)

    def test_best_xi_default(self):
        r = _run("best-xi", _ADF, "--save", "pm1.sav")
        self.assertSuccess(r)
        self.assertIn("Best XI (4-4-2)", r.stdout)
        self.assertIn("Goalkeeper", r.stdout)

    def test_best_xi_with_filter_and_cap(self):
        r = _run("best-xi", _ADF, "--save", "pm1.sav",
                 "--formation", "4-3-3", "--filter", "young", "--max-per-team", "2")
        self.assertSuccess(r)
        self.assertIn("Best XI (4-3-3)", r.stdout)

    def test_best_xi_market_only(self):
        r = _run("best-xi", _ADF, "--save", "pm1.sav", "--market-only")
        self.assertSuccess(r)
        # Every listed player should be market-available (★ in the right column)
        self.assertIn("Best XI", r.stdout)

    def test_export_players_csv_stdout(self):
        r = _run("export-players", _ADF, "--save", "pm1.sav",
                 "--team", "0", "--format", "csv")
        self.assertSuccess(r)
        reader = csv.DictReader(io.StringIO(r.stdout))
        rows = list(reader)
        self.assertGreater(len(rows), 0)
        self.assertIn("player_id", reader.fieldnames)
        self.assertIn("total_skill", reader.fieldnames)

    def test_export_players_json_file(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "players.json")
            r = _run("export-players", _ADF, "--save", "pm1.sav",
                     "--team", "0", "--format", "json", "--output", out)
            self.assertSuccess(r)
            with open(out) as f:
                rows = json.load(f)
            self.assertGreater(len(rows), 0)
            self.assertIn("player_id", rows[0])

    def test_edit_player_noop_writes_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as td:
            adf_copy = os.path.join(td, "save.adf")
            shutil.copy(_ADF, adf_copy)
            original = open(adf_copy, "rb").read()
            r = _run("edit-player", adf_copy, "--save", "pm1.sav",
                     "--id", "0", "--age", "25")
            self.assertSuccess(r)
            self.assertTrue(os.path.isfile(adf_copy + ".bak"))
            bak = open(adf_copy + ".bak", "rb").read()
            self.assertEqual(original, bak,
                             "backup must preserve the pre-edit bytes")

    def test_squad_analyst_all_teams(self):
        r = _run("squad-analyst", _ADF, "--save", "pm1.sav")
        self.assertSuccess(r)
        self.assertIn("MILAN", r.stdout)
        self.assertIn("Size", r.stdout.replace("Sz", "Size"))

    def test_squad_analyst_single_team(self):
        r = _run("squad-analyst", _ADF, "--save", "pm1.sav", "--team", "0")
        self.assertSuccess(r)
        self.assertIn("MILAN", r.stdout)
        self.assertIn("Youngest", r.stdout)
        self.assertIn("Best", r.stdout)

    def test_career_tracker_default(self):
        r = _run("career-tracker", _ADF,
                 "--save-a", "pm1.sav", "--save-b", "pm2.sav", "--limit", "3")
        self.assertSuccess(r)
        self.assertIn("Comparing A=pm1.sav -> B=pm2.sav", r.stdout)

    def test_career_tracker_team_changes_only(self):
        r = _run("career-tracker", _ADF,
                 "--save-a", "pm1.sav", "--save-b", "pm2.sav",
                 "--team-changes-only", "--limit", "5")
        self.assertSuccess(r)

    def test_career_tracker_same_slot_has_no_changes(self):
        r = _run("career-tracker", _ADF,
                 "--save-a", "pm1.sav", "--save-b", "pm1.sav")
        self.assertSuccess(r)
        # comparing a slot to itself should yield 0 changed players
        self.assertIn("(0 players changed)", r.stdout)

    def test_byte_stats_reserved_is_zero(self):
        r = _run("byte-stats", _ADF, "--save", "pm1.sav",
                 "--offset", "0x14", "--filter", "real")
        self.assertSuccess(r)
        self.assertIn("reserved", r.stdout)
        self.assertIn("100.0%", r.stdout)  # all 1031 players have byte=0

    def test_byte_stats_transfer_list_bit_counts(self):
        r = _run("byte-stats", _ADF, "--save", "pm1.sav",
                 "--offset", "0x1A", "--mask", "0x80", "--filter", "real")
        self.assertSuccess(r)
        self.assertIn("mystery3", r.stdout)
        self.assertIn("255", r.stdout)  # known transfer-listed count

    def test_byte_diff_surfaces_transfer_list_bit(self):
        r = _run("byte-diff", _ADF, "--save", "pm1.sav",
                 "--set-a", "transfer-listed",
                 "--set-b", "not-transfer-listed",
                 "--top", "3")
        self.assertSuccess(r)
        self.assertIn("mystery3", r.stdout)
        self.assertIn("0x80", r.stdout)
        self.assertIn("100.0%", r.stdout)  # delta should be 100%

    def test_byte_diff_rejects_unknown_filter(self):
        r = _run("byte-diff", _ADF, "--save", "pm1.sav",
                 "--set-a", "bogus", "--set-b", "all")
        self.assertNotEqual(r.returncode, 0)

    def test_unknown_subcommand_fails(self):
        r = _run("not-a-command")
        self.assertNotEqual(r.returncode, 0)

    # --- Line-up Coach (BETA) ------------------------------------------------

    def test_suggest_xi_championship(self):
        r = _run("suggest-xi", _ADF, "--save", "pm1.sav")
        self.assertSuccess(r)
        self.assertIn("[BETA]", r.stdout)
        self.assertIn("Recommended XI", r.stdout)
        self.assertIn("Formation ranking", r.stdout)

    def test_suggest_xi_team_needs_include_injured(self):
        # MILAN in Save1 has too many injuries to field a default XI.
        r = _run("suggest-xi", _ADF, "--save", "pm1.sav", "--team", "0")
        self.assertEqual(r.returncode, 0)
        self.assertIn("No formation could be filled", r.stdout)

    def test_suggest_xi_with_include_injured(self):
        r = _run("suggest-xi", _ADF, "--save", "pm1.sav",
                 "--team", "0", "--include-injured")
        self.assertSuccess(r)
        self.assertIn("MILAN", r.stdout)
        self.assertIn("Recommended XI", r.stdout)

    def test_suggest_xi_explicit_formation(self):
        r = _run("suggest-xi", _ADF, "--save", "pm1.sav",
                 "--formation", "3-5-2")
        self.assertSuccess(r)
        self.assertIn("3-5-2", r.stdout)
        # With a forced formation there's no ranking block.
        self.assertNotIn("Formation ranking", r.stdout)

    def test_suggest_xi_weights_override(self):
        r = _run("suggest-xi", _ADF, "--save", "pm1.sav",
                 "--weights", "morale=0", "fatigue=0")
        self.assertSuccess(r)

    def test_suggest_xi_invalid_weight_rejected(self):
        r = _run("suggest-xi", _ADF, "--save", "pm1.sav",
                 "--weights", "bogus-no-equals")
        self.assertNotEqual(r.returncode, 0)

    def test_edit_tactics_dump_is_valid_json(self):
        r = _run("edit-tactics", _ADF, "--file", "4-2-4.tac", "--dump")
        self.assertSuccess(r)
        doc = json.loads(r.stdout)
        self.assertIn("zones", doc)
        self.assertIn("trailer_hex", doc)
        self.assertEqual(len(doc["zones"]), 20)

    def test_edit_tactics_import_roundtrip_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            adf_copy = os.path.join(td, "save.adf")
            shutil.copy(_ADF, adf_copy)
            original = open(adf_copy, "rb").read()

            dump = _run("edit-tactics", adf_copy, "--file", "4-2-4.tac", "--dump")
            self.assertSuccess(dump)
            json_path = os.path.join(td, "tac.json")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(dump.stdout)

            r = _run("edit-tactics", adf_copy, "--file", "4-2-4.tac",
                     "--import", json_path)
            self.assertSuccess(r)
            self.assertTrue(os.path.isfile(adf_copy + ".bak"))

            after = open(adf_copy, "rb").read()
            self.assertEqual(original, after,
                             "noop import must be byte-identical to input")

    def test_edit_tactics_rejects_non_tac_file(self):
        r = _run("edit-tactics", _ADF, "--file", "pm1.sav", "--dump")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
