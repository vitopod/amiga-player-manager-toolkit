"""Unit tests for the byte-level reverse-engineering workbench.

These tests only exercise the pure analysis primitives in pm_core.workbench —
they don't need a save disk.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.player import (
    PlayerRecord, RECORD_SIZE, FIELD_LAYOUT, field_at_offset, serialize_player,
)
from pm_core.workbench import (
    byte_histogram, bit_probability, diff_sets, query, BitDiff,
)


def _p(**kwargs) -> PlayerRecord:
    """Build a PlayerRecord with safe defaults plus overrides."""
    base = dict(age=25, position=3, division=1, team_index=0,
                height=180, weight=75)
    base.update(kwargs)
    return PlayerRecord(**base)


class TestFieldLayout(unittest.TestCase):
    def test_layout_spans_whole_record(self):
        covered = sum(size for _, size, _, _ in FIELD_LAYOUT)
        self.assertEqual(covered, RECORD_SIZE)

    def test_layout_has_no_gaps_or_overlaps(self):
        expected = 0
        for off, size, _, _ in FIELD_LAYOUT:
            self.assertEqual(off, expected,
                             f"gap or overlap at offset {off:#x}")
            expected += size

    def test_field_at_offset_finds_multi_byte_fields(self):
        name, sub, size = field_at_offset(0x00)
        self.assertEqual((name, sub, size), ("rng_seed", 0, 4))
        name, sub, size = field_at_offset(0x03)
        self.assertEqual((name, sub, size), ("rng_seed", 3, 4))

    def test_field_at_offset_finds_single_byte_fields(self):
        self.assertEqual(field_at_offset(0x1A)[0], "mystery3")
        self.assertEqual(field_at_offset(0x29)[0], "contract_years")

    def test_field_at_offset_rejects_out_of_range(self):
        with self.assertRaises(IndexError):
            field_at_offset(-1)
        with self.assertRaises(IndexError):
            field_at_offset(RECORD_SIZE)


class TestByteHistogram(unittest.TestCase):
    def test_counts_whole_byte_values(self):
        players = [_p(age=20), _p(age=20), _p(age=30)]
        hist = byte_histogram(players, offset=0x04)
        self.assertEqual(hist, {20: 2, 30: 1})

    def test_mask_isolates_single_bit(self):
        players = [
            _p(mystery3=0x80),
            _p(mystery3=0x81),
            _p(mystery3=0x00),
            _p(mystery3=0x7F),
        ]
        hist = byte_histogram(players, offset=0x1A, mask=0x80)
        self.assertEqual(hist, {0x80: 2, 0x00: 2})

    def test_empty_input_returns_empty_counter(self):
        self.assertEqual(dict(byte_histogram([], offset=0)), {})

    def test_rejects_invalid_offset(self):
        with self.assertRaises(ValueError):
            byte_histogram([], offset=-1)
        with self.assertRaises(ValueError):
            byte_histogram([], offset=RECORD_SIZE)

    def test_rejects_invalid_mask(self):
        with self.assertRaises(ValueError):
            byte_histogram([], offset=0, mask=0x100)


class TestBitProbability(unittest.TestCase):
    def test_all_bits_set(self):
        players = [_p(mystery3=0x80) for _ in range(5)]
        self.assertEqual(bit_probability(players, 0x1A, 0x80), 1.0)

    def test_no_bits_set(self):
        players = [_p(mystery3=0x00) for _ in range(5)]
        self.assertEqual(bit_probability(players, 0x1A, 0x80), 0.0)

    def test_half_and_half(self):
        players = [_p(mystery3=0x80), _p(mystery3=0x00)]
        self.assertEqual(bit_probability(players, 0x1A, 0x80), 0.5)

    def test_empty_returns_zero(self):
        self.assertEqual(bit_probability([], 0x1A, 0x80), 0.0)

    def test_rejects_non_single_bit_mask(self):
        with self.assertRaises(ValueError):
            bit_probability([_p()], 0x1A, 0xFF)  # multi-bit
        with self.assertRaises(ValueError):
            bit_probability([_p()], 0x1A, 0x00)  # no bit
        with self.assertRaises(ValueError):
            bit_probability([_p()], 0x1A, 0x100)  # out of range


class TestDiffSets(unittest.TestCase):
    def test_recovers_known_transfer_list_bit(self):
        """Set A: all have mystery3 bit 0x80 set. Set B: none do."""
        set_a = [_p(mystery3=0x80) for _ in range(10)]
        set_b = [_p(mystery3=0x00) for _ in range(10)]
        diffs = diff_sets(set_a, set_b, top_n=5)
        self.assertTrue(diffs, "expected at least one discriminative bit")
        top = diffs[0]
        self.assertEqual(top.offset, 0x1A)
        self.assertEqual(top.bit, 0x80)
        self.assertEqual(top.bit_index, 7)
        self.assertEqual(top.field_name, "mystery3")
        self.assertEqual(top.delta, 1.0)

    def test_ignores_constant_bits(self):
        """If both sets have the same bit pattern, no diff should appear."""
        same = [_p(age=25, mystery3=0x40) for _ in range(5)]
        diffs = diff_sets(same, [_p(age=25, mystery3=0x40) for _ in range(5)])
        self.assertEqual(diffs, [])

    def test_empty_set_returns_empty(self):
        self.assertEqual(diff_sets([], [_p()]), [])
        self.assertEqual(diff_sets([_p()], []), [])

    def test_top_n_bounds_result(self):
        set_a = [_p(age=20, position=4, mystery3=0x80)]
        set_b = [_p(age=30, position=1, mystery3=0x00)]
        diffs = diff_sets(set_a, set_b, top_n=3)
        self.assertLessEqual(len(diffs), 3)

    def test_bit_label_is_readable(self):
        d = BitDiff(offset=0x1A, bit=0x80, bit_index=7,
                    p_a=1.0, p_b=0.0, delta=1.0,
                    field_name="mystery3", field_byte=0)
        self.assertEqual(d.bit_label, "mystery3 bit 7 (0x80)")


class TestQuery(unittest.TestCase):
    def test_filters_by_exact_byte(self):
        players = [_p(age=20), _p(age=25), _p(age=30)]
        hit = query(players, offset=0x04, value=25)
        self.assertEqual([p.age for p in hit], [25])

    def test_filters_by_bit_mask(self):
        players = [
            _p(mystery3=0x80),
            _p(mystery3=0x81),
            _p(mystery3=0x00),
            _p(mystery3=0x7F),
        ]
        hit = query(players, offset=0x1A, mask=0x80, value=0x80)
        self.assertEqual(len(hit), 2)

    def test_comparison_ops(self):
        players = [_p(age=a) for a in (18, 22, 30, 35)]
        self.assertEqual(len(query(players, 0x04, 25, op=">")), 2)
        self.assertEqual(len(query(players, 0x04, 25, op="<=")), 2)

    def test_rejects_unknown_op(self):
        with self.assertRaises(ValueError):
            query([_p()], offset=0, value=0, op="~=")

    def test_rejects_out_of_range_value(self):
        with self.assertRaises(ValueError):
            query([_p()], offset=0, value=256)


class TestRawBytesConsistency(unittest.TestCase):
    def test_raw_bytes_matches_serialize(self):
        from pm_core.workbench import raw_bytes
        p = _p(age=27, mystery3=0x80, contract_years=3)
        self.assertEqual(raw_bytes(p), serialize_player(p))


if __name__ == "__main__":
    unittest.main()
