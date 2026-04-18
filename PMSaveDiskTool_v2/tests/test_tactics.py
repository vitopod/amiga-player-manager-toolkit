"""Unit tests for the `.tac` parser/serializer.

Covers round-trip on every `.tac` file present on Save1_PM.adf (both 928-
and 980-byte shapes), shape invariants, description extraction for PM's
928-byte variant, and validation of malformed inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.adf import ADF
from pm_core.tactics import (
    NUM_PLAYERS, NUM_ZONES, POSITIONS_SIZE, SHIRT_NUMBERS, ZONE_NAMES,
    Tactic, parse_tac, serialize_tac, tactic_to_json, tactic_from_json,
)

# Same convention as the other test modules.
TEST_ADF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "PMSaveDiskTool_v1.2", "Save1_PM.adf",
)
_ALT_ADF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ADFs", "Save1_PM.adf",
)


def _load_tac_files() -> list[tuple[str, bytes]]:
    """Return (name, bytes) for every .tac file on the test ADF, or []."""
    for path in (TEST_ADF, _ALT_ADF):
        if os.path.exists(path):
            adf = ADF.load(path)
            return [
                (e.name, bytes(adf._data[e.byte_offset:e.byte_offset + e.size]))
                for e in adf.list_files()
                if e.name.lower().endswith(".tac")
            ]
    return []


class TestConstants(unittest.TestCase):
    def test_shape(self):
        self.assertEqual(NUM_PLAYERS, 10)
        self.assertEqual(NUM_ZONES, 20)
        self.assertEqual(len(ZONE_NAMES), NUM_ZONES)
        self.assertEqual(len(SHIRT_NUMBERS), NUM_PLAYERS)
        self.assertEqual(POSITIONS_SIZE, 800)

    def test_shirt_numbers_are_2_through_11(self):
        self.assertEqual(SHIRT_NUMBERS, tuple(range(2, 12)))

    def test_zone_names_unique(self):
        self.assertEqual(len(set(ZONE_NAMES)), NUM_ZONES)


class TestParseValidation(unittest.TestCase):
    def test_rejects_short_buffer(self):
        with self.assertRaises(ValueError):
            parse_tac(b"\x00" * 799)

    def test_accepts_exactly_800_bytes(self):
        t = parse_tac(b"\x00" * 800)
        self.assertEqual(t.total_size, 800)
        self.assertEqual(t.trailer, b"")

    def test_serialize_rejects_missing_zone(self):
        t = parse_tac(b"\x00" * 800)
        del t.positions["area1"]
        with self.assertRaises(ValueError):
            serialize_tac(t)

    def test_serialize_rejects_missing_shirt(self):
        t = parse_tac(b"\x00" * 800)
        del t.positions["area1"][5]
        with self.assertRaises(ValueError):
            serialize_tac(t)

    def test_serialize_rejects_out_of_range(self):
        t = parse_tac(b"\x00" * 800)
        t.positions["area1"][2] = (0x10000, 0)
        with self.assertRaises(ValueError):
            serialize_tac(t)


class TestShapeInvariants(unittest.TestCase):
    def test_all_zones_and_shirts_populated(self):
        # Parsing zeros still yields the full grid.
        t = parse_tac(b"\x00" * 800)
        self.assertEqual(set(t.positions.keys()), set(ZONE_NAMES))
        for zone in ZONE_NAMES:
            self.assertEqual(set(t.positions[zone].keys()), set(SHIRT_NUMBERS))
            for shirt in SHIRT_NUMBERS:
                self.assertEqual(t.positions[zone][shirt], (0, 0))


class TestRealDisk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tacs = _load_tac_files()
        if not cls.tacs:
            raise unittest.SkipTest(f"No test ADF with .tac files found")

    def test_at_least_one_928_byte_tac_present(self):
        sizes = {len(buf) for _, buf in self.tacs}
        self.assertIn(928, sizes, f"expected a 928-byte PM tactic, got sizes={sizes}")

    def test_roundtrip_every_tac_on_disk(self):
        for name, buf in self.tacs:
            with self.subTest(tac=name, size=len(buf)):
                t = parse_tac(buf)
                self.assertEqual(t.total_size, len(buf))
                self.assertEqual(serialize_tac(t), buf)

    def test_coordinates_in_reasonable_pitch_range(self):
        # Every parsed coord should fit in u16; for real tactics most land in
        # world space [0, ~2048]. Assert a loose sanity bound per file.
        for name, buf in self.tacs:
            with self.subTest(tac=name):
                t = parse_tac(buf)
                xs = [x for zone in t.positions.values() for x, _ in zone.values()]
                ys = [y for zone in t.positions.values() for _, y in zone.values()]
                self.assertTrue(max(xs) < 2048, f"{name}: x out of pitch bounds")
                self.assertTrue(max(ys) < 2048, f"{name}: y out of pitch bounds")

    def test_928_byte_tactic_has_description(self):
        for name, buf in self.tacs:
            if len(buf) == 928:
                t = parse_tac(buf)
                desc = t.description
                # PM fills this with a formation blurb; printable ASCII ≥ 10 chars.
                self.assertGreater(len(desc), 10,
                    f"{name}: expected ASCII description, got {desc!r}")
                self.assertTrue(desc.isprintable(),
                    f"{name}: non-printable in description {desc!r}")
                return
        self.skipTest("no 928-byte tactic on disk to describe-test")

    def test_980_byte_tactic_has_no_description(self):
        for name, buf in self.tacs:
            if len(buf) == 980:
                t = parse_tac(buf)
                self.assertEqual(t.description, "",
                    f"{name}: 980-byte templates should have no description")
                return
        self.skipTest("no 980-byte tactic on disk")


class TestJsonRoundtrip(unittest.TestCase):
    def test_empty_tactic_roundtrip(self):
        t = parse_tac(b"\x00" * 800)
        self.assertEqual(serialize_tac(tactic_from_json(tactic_to_json(t))),
                         serialize_tac(t))

    def test_real_disk_json_roundtrip(self):
        for name, buf in _load_tac_files():
            with self.subTest(tac=name):
                t = parse_tac(buf)
                t2 = tactic_from_json(tactic_to_json(t))
                self.assertEqual(serialize_tac(t2), buf)

    def test_json_rejects_missing_zone(self):
        t = parse_tac(b"\x00" * 800)
        doc = tactic_to_json(t)
        del doc["zones"]["area1"]
        with self.assertRaises(ValueError):
            tactic_from_json(doc)

    def test_json_rejects_bad_shirt(self):
        t = parse_tac(b"\x00" * 800)
        doc = tactic_to_json(t)
        doc["zones"]["area1"]["1"] = [0, 0]  # GK is never stored
        del doc["zones"]["area1"]["2"]
        with self.assertRaises(ValueError):
            tactic_from_json(doc)


if __name__ == "__main__":
    unittest.main()
