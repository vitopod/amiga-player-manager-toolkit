"""Tests for pm_core/names.py — hash algorithm, DEFAJAM decompressor, and
GameDisk integration. The hash and RLE tests are ADF-independent. The full
GameDisk integration test uses PlayerManagerITA.adf if present.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.names import (
    GameDisk,
    _DEFAJAMDecompressor,
    _hash_round,
    _name_from_seed,
)


_GAME_ADF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "PlayerManagerITA.adf",
)

# English game disk (BETA). Optional — tests gated on existence.
_EN_GAME_ADF = os.environ.get(
    "PM_EN_GAME_ADF",
    "/Users/simone/Downloads/Player Manager (1990)(Anco)[cr OCL] EN.adf",
)


class TestHashRound(unittest.TestCase):
    """The hash round is a pure 6-byte buffer permutation. Properties we can
    verify independently of the overall algorithm:
      - Applied to the zero buffer it remains zero (no carry in, no bit set).
      - It is deterministic (calling twice on copies gives same result).
      - It diffuses: changing a single bit in the input changes the output.
    """

    def test_zero_buffer_stays_zero(self):
        buf = bytearray(6)
        _hash_round(buf)
        self.assertEqual(bytes(buf), b"\x00" * 6)

    def test_deterministic(self):
        buf1 = bytearray([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC])
        buf2 = bytearray(buf1)
        _hash_round(buf1)
        _hash_round(buf2)
        self.assertEqual(bytes(buf1), bytes(buf2))

    def test_diffuses_single_bit_change(self):
        a = bytearray([0, 0, 0, 0, 0, 1])
        b = bytearray([0, 0, 0, 0, 0, 0])
        _hash_round(a)
        _hash_round(b)
        self.assertNotEqual(bytes(a), bytes(b))


class TestNameFromSeedSynthetic(unittest.TestCase):
    """_name_from_seed with a tiny surname list — does not require the game ADF.
    Validates format, determinism, and that different seeds can produce different
    outputs.
    """

    SURNAMES = ["Rossi", "Bianchi", "Verdi", "Neri", "Gialli"]

    def test_name_format(self):
        name = _name_from_seed(0x12345678, self.SURNAMES)
        # Format: at least one initial+dot, space, surname from the list
        self.assertIn(" ", name)
        initials, surname = name.split(" ", 1)
        self.assertTrue(initials.endswith("."))
        self.assertIn(surname, self.SURNAMES)

    def test_deterministic(self):
        a = _name_from_seed(0xDEADBEEF, self.SURNAMES)
        b = _name_from_seed(0xDEADBEEF, self.SURNAMES)
        self.assertEqual(a, b)

    def test_different_seeds_can_differ(self):
        names = {_name_from_seed(s, self.SURNAMES)
                 for s in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07)}
        self.assertGreater(len(names), 1, "seeds should not all collapse to one name")

    def test_initial_count_in_range(self):
        for seed in (0x0, 0x1, 0xABCDEF00, 0xFFFFFFFF):
            name = _name_from_seed(seed, self.SURNAMES)
            initials = name.split(" ", 1)[0]
            # Each initial contributes 2 chars: "X."
            n = len(initials) // 2
            self.assertIn(n, (1, 2, 3), f"seed {seed:#x}: got {n} initials ({name!r})")


class TestDefajamRLE(unittest.TestCase):
    """Phase-2 RLE decoder is pure and easy to test with hand-built vectors."""

    def test_no_marker_is_passthrough(self):
        data = b"hello world"
        self.assertEqual(_DEFAJAMDecompressor._phase2_rle(data), data)

    def test_marker_zero_emits_literal_marker(self):
        data = b"\x9b\x00"
        self.assertEqual(_DEFAJAMDecompressor._phase2_rle(data), b"\x9b")

    def test_marker_run(self):
        # 0x9B count=2 val=ord('A') -> emit 'A' * (2+3) = 5 As
        data = b"X\x9b\x02AY"
        self.assertEqual(_DEFAJAMDecompressor._phase2_rle(data), b"XAAAAAY")

    def test_trailing_marker_with_no_count(self):
        # If marker is the last byte there is nothing to read — it should be
        # emitted as a literal rather than crash.
        data = b"abc\x9b"
        out = _DEFAJAMDecompressor._phase2_rle(data)
        self.assertEqual(out, b"abc\x9b")


@unittest.skipUnless(os.path.isfile(_GAME_ADF),
                     f"{_GAME_ADF} not available")
class TestGameDiskIntegration(unittest.TestCase):
    """End-to-end: load the real game ADF, check known surname-count and a set
    of canonical seed -> name mappings captured from the reference implementation.
    """

    @classmethod
    def setUpClass(cls):
        cls.gd = GameDisk.load(_GAME_ADF)

    def test_surname_count(self):
        self.assertEqual(self.gd.surname_count, 245)

    def test_known_edges_of_surname_table(self):
        self.assertEqual(self.gd.surnames[0], "Amato")
        self.assertIn("Pioli", self.gd.surnames)

    def test_known_seeds(self):
        # Captured from current implementation; locks the hash+surname output.
        expected = {
            0x47264FA5: "J. Padovano",
            0x0DD5131B: "M.J. Manzo",
            0x12345678: "E.R. Pasqualetto",
            0x00000000: "A. Amato",
            0xFFFFFFFF: "R. Alboni",
        }
        for seed, name in expected.items():
            self.assertEqual(self.gd.player_full_name(seed), name,
                             f"seed {seed:#x}")

    def test_player_surname_helper(self):
        full = self.gd.player_full_name(0x12345678)
        surname = self.gd.player_surname(0x12345678)
        self.assertTrue(full.endswith(" " + surname))


@unittest.skipUnless(os.path.isfile(_EN_GAME_ADF),
                     f"{_EN_GAME_ADF} not available")
class TestEnglishGameDiskBeta(unittest.TestCase):
    """English BETA path: anchor-scan on a PM custom-file-table disk.

    Verification state (2026-04-17): surname table and initials charsets
    cross-checked against a real in-game roster screenshot; full seed→name
    mapping not yet locked against a known seed. These tests guard the
    extraction and API surface only.
    """

    @classmethod
    def setUpClass(cls):
        cls.gd = GameDisk.load(_EN_GAME_ADF)

    def test_build_detected_as_english(self):
        self.assertEqual(self.gd.build, "english")

    def test_flagged_as_beta(self):
        self.assertTrue(self.gd.is_beta)
        self.assertTrue(self.gd.names_available)

    def test_surname_count_183(self):
        # The Windows PMSaveDiskTool PE32 also has exactly 183 English names;
        # this count is expected to be stable.
        self.assertEqual(self.gd.surname_count, 183)

    def test_known_edges_of_surname_table(self):
        # Adams..Young, straddling the anchor and terminator.
        self.assertEqual(self.gd.surnames[0], "Adams")
        self.assertEqual(self.gd.surnames[-1], "Young")

    def test_anchor_surnames_in_order(self):
        # These are the five surnames used as the anchor pattern — if the
        # anchor scan drifts, this is the first thing that breaks.
        self.assertEqual(self.gd.surnames[:5],
                         ["Adams", "Adcock", "Addison", "Aldridge", "Alexander"])

    def test_no_ui_strings_leaked_into_table(self):
        # The surname region is adjacent to menu/UI strings. Everything we
        # return must be alphabetic and capitalised.
        for s in self.gd.surnames:
            self.assertTrue(s.isalpha(), f"non-alpha surname: {s!r}")
            self.assertTrue(s[0].isupper(), f"surname not capitalised: {s!r}")
            self.assertGreaterEqual(len(s), 2)

    def test_player_full_name_shapes(self):
        # For a spread of seeds, output must have the "I. Surname" shape
        # (1–3 dot-separated initials, space, surname from our table).
        import re
        pattern = re.compile(r"^([A-Z]\.){1,3} [A-Z][a-z]+$")
        surname_set = set(self.gd.surnames)
        for seed in (0x00000000, 0xFFFFFFFF, 0x12345678, 0xdeadbeef, 0x47264fa5):
            full = self.gd.player_full_name(seed)
            self.assertRegex(full, pattern, f"bad shape for seed {seed:#x}: {full!r}")
            self.assertIn(full.split(" ", 1)[1], surname_set)

    def test_initials_stay_within_charsets(self):
        # The Italian charsets (reused for English) are ADJR / CEGMS /
        # BFHILNTW / O. Every initial produced must be one of those.
        allowed = set("ADJR") | set("CEGMS") | set("BFHILNTW") | set("O")
        for seed in range(0, 0x100000, 0x2711):  # 63 pseudo-random seeds
            full = self.gd.player_full_name(seed)
            for c in full.split(" ", 1)[0]:
                if c.isalpha():
                    self.assertIn(c, allowed,
                                  f"initial {c!r} from seed {seed:#x} ({full!r}) "
                                  "outside allowed charsets")


if __name__ == "__main__":
    unittest.main(verbosity=2)
