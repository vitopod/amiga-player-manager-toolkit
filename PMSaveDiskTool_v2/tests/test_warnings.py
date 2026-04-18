"""Tests for the position-based skill-threshold warnings module."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core.player import PlayerRecord
from pm_core.warnings import (
    DEFAULT_THRESHOLD,
    POSITION_REQUIRED_SKILLS,
    describe_weaknesses,
    has_weakness,
    weak_skills,
)


def _mk(position: int, **overrides) -> PlayerRecord:
    """Build a PlayerRecord with reasonable defaults, overridden selectively."""
    p = PlayerRecord()
    p.position = position
    # Bump every skill above the default threshold unless overridden.
    base = DEFAULT_THRESHOLD + 50  # 150
    for skill in ("stamina", "resilience", "pace", "agility", "aggression",
                  "flair", "passing", "shooting", "tackling", "keeping"):
        setattr(p, skill, overrides.get(skill, base))
    return p


class TestRequiredSkillsTable:
    def test_covers_four_on_field_positions(self):
        assert set(POSITION_REQUIRED_SKILLS) == {1, 2, 3, 4}

    def test_gk_needs_keeping(self):
        assert "keeping" in POSITION_REQUIRED_SKILLS[1]

    def test_def_needs_tackling(self):
        assert "tackling" in POSITION_REQUIRED_SKILLS[2]

    def test_mid_needs_passing(self):
        assert "passing" in POSITION_REQUIRED_SKILLS[3]

    def test_fwd_needs_shooting(self):
        assert "shooting" in POSITION_REQUIRED_SKILLS[4]


class TestWeakSkills:
    def test_no_weakness_when_all_above_threshold(self):
        p = _mk(position=4)
        assert weak_skills(p) == []
        assert has_weakness(p) is False

    def test_flags_single_below_threshold(self):
        p = _mk(position=4, pace=80)
        weak = weak_skills(p)
        assert weak == [("pace", 80)]
        assert has_weakness(p) is True

    def test_flags_multiple_below_threshold(self):
        p = _mk(position=2, tackling=50, pace=90)
        # Returned in POSITION_REQUIRED_SKILLS order: tackling, stamina, pace.
        assert weak_skills(p) == [("tackling", 50), ("pace", 90)]

    def test_threshold_is_exclusive(self):
        # Exactly at the threshold is "OK".
        p = _mk(position=1, keeping=DEFAULT_THRESHOLD)
        assert weak_skills(p) == []

    def test_garbage_position_has_no_required_skills(self):
        p = _mk(position=0)
        assert weak_skills(p) == []
        assert has_weakness(p) is False

    def test_custom_threshold(self):
        p = _mk(position=3, passing=120)
        assert weak_skills(p, threshold=100) == []
        assert weak_skills(p, threshold=150) == [("passing", 120)]


class TestDescribeWeaknesses:
    def test_empty_when_none(self):
        assert describe_weaknesses(_mk(position=4)) == ""

    def test_formats_comma_separated(self):
        p = _mk(position=4, pace=80, shooting=70)
        # POSITION_REQUIRED_SKILLS[4] = ("shooting", "pace", "flair")
        assert describe_weaknesses(p) == "shooting 70, pace 80"
