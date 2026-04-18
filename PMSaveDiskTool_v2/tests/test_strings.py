"""Unit tests for pm_core.strings internationalisation layer."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core import strings


@pytest.fixture(autouse=True)
def reset_language():
    """Restore the default language after every test."""
    yield
    strings.set_language("en")


class TestSetLanguage:
    def test_default_is_english(self):
        assert strings._lang == "en"

    def test_set_valid_language(self):
        strings.set_language("it")
        assert strings._lang == "it"

    def test_set_unknown_language_is_ignored(self):
        strings.set_language("fr")
        assert strings._lang == "en"

    def test_reset_to_english(self):
        strings.set_language("it")
        strings.set_language("en")
        assert strings._lang == "en"


class TestTranslate:
    def test_english_key_returns_string(self):
        strings.set_language("en")
        assert strings.t("col.skill") == "Skill"

    def test_italian_key_returns_italian(self):
        strings.set_language("it")
        assert strings.t("col.skill") == "Abil."

    def test_fallback_to_english_when_key_missing_in_it(self):
        # Verify fallback: a key present in EN but absent in IT returns EN value.
        # We inject a temporary key to test without relying on prod data.
        strings._STRINGS["en"]["_test_only"] = "test-en"
        strings.set_language("it")
        result = strings.t("_test_only")
        del strings._STRINGS["en"]["_test_only"]
        assert result == "test-en"

    def test_missing_key_returns_key_itself(self):
        assert strings.t("no.such.key.xyz") == "no.such.key.xyz"

    def test_all_english_keys_present_in_italian(self):
        en_keys = set(strings._STRINGS["en"])
        it_keys = set(strings._STRINGS["it"])
        missing = en_keys - it_keys
        # Warn about missing keys — a few may be intentionally inherited via fallback
        assert not missing, f"Italian is missing EN keys: {missing}"


class TestSkillKeys:
    SKILL_NAMES = [
        "stamina", "resilience", "pace", "agility", "aggression",
        "flair", "passing", "shooting", "tackling", "keeping",
    ]

    def test_all_skill_keys_defined_in_english(self):
        strings.set_language("en")
        for s in self.SKILL_NAMES:
            val = strings.t(f"skill.{s}")
            assert val != f"skill.{s}", f"Missing EN key: skill.{s}"

    def test_all_skill_keys_defined_in_italian(self):
        strings.set_language("it")
        for s in self.SKILL_NAMES:
            val = strings.t(f"skill.{s}")
            assert val != f"skill.{s}", f"Missing IT key: skill.{s}"


class TestPositionKeys:
    def test_positions_in_english(self):
        strings.set_language("en")
        assert strings.t("pos.gk")  == "GK"
        assert strings.t("pos.def") == "DEF"
        assert strings.t("pos.mid") == "MID"
        assert strings.t("pos.fwd") == "FWD"

    def test_positions_in_italian(self):
        strings.set_language("it")
        assert strings.t("pos.gk")  == "Port."
        assert strings.t("pos.def") == "Dif."
        assert strings.t("pos.mid") == "Cen."
        assert strings.t("pos.fwd") == "Att."


class TestViewKeys:
    def test_view_all_differs_between_languages(self):
        strings.set_language("en")
        en_val = strings.t("view.all")
        strings.set_language("it")
        it_val = strings.t("view.all")
        assert en_val != it_val

    def test_view_xi_keys_exist_in_both_languages(self):
        for lang in ("en", "it"):
            strings.set_language(lang)
            for key in ("view.top11_442", "view.top11_433",
                        "view.young_xi", "view.fa_xi"):
                val = strings.t(key)
                assert val != key, f"Missing key {key!r} in {lang!r}"
