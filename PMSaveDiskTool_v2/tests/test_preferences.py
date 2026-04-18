"""Unit tests for ``pm_core.preferences``.

Every test redirects the module's ``STATE_DIR`` and ``STATE_FILE`` to
a ``tmp_path`` so the real ``~/.pmsavedisktool/preferences.json`` is
never touched.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core import preferences


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    """Redirect preferences.STATE_DIR / STATE_FILE into ``tmp_path``."""
    state_dir = tmp_path / "pmsavedisktool"
    state_file = state_dir / "preferences.json"
    monkeypatch.setattr(preferences, "STATE_DIR", str(state_dir))
    monkeypatch.setattr(preferences, "STATE_FILE", str(state_file))
    return state_dir, state_file


class TestDefaultState:
    def test_has_all_documented_keys(self):
        state = preferences.default_state()
        assert set(state) == {
            "show_splash",
            "show_welcome",
            "auto_open_last_save",
            "auto_open_last_game",
            "last_save_adf",
            "last_game_adf",
            "default_view",
            "default_formation",
            "use_system_font",
            "theme",
        }

    def test_splash_defaults_on(self):
        assert preferences.default_state()["show_splash"] is True

    def test_welcome_defaults_on(self):
        assert preferences.default_state()["show_welcome"] is True

    def test_auto_opens_default_off(self):
        state = preferences.default_state()
        assert state["auto_open_last_save"] is False
        assert state["auto_open_last_game"] is False

    def test_last_paths_default_empty(self):
        state = preferences.default_state()
        assert state["last_save_adf"] == ""
        assert state["last_game_adf"] == ""

    def test_default_view_default_empty(self):
        assert preferences.default_state()["default_view"] == ""

    def test_default_formation_default_442(self):
        assert preferences.default_state()["default_formation"] == "4-4-2"

    def test_system_font_defaults_off(self):
        assert preferences.default_state()["use_system_font"] is False

    def test_theme_default_retro(self):
        assert preferences.default_state()["theme"] == "retro"


class TestLoad:
    def test_missing_file_returns_defaults(self, tmp_state):
        assert preferences.load() == preferences.default_state()

    def test_malformed_json_returns_defaults(self, tmp_state):
        state_dir, state_file = tmp_state
        state_dir.mkdir(parents=True)
        state_file.write_text("not json {{", encoding="utf-8")
        assert preferences.load() == preferences.default_state()

    def test_non_dict_root_returns_defaults(self, tmp_state):
        state_dir, state_file = tmp_state
        state_dir.mkdir(parents=True)
        state_file.write_text("[1, 2, 3]", encoding="utf-8")
        assert preferences.load() == preferences.default_state()

    def test_partial_file_fills_missing_keys_with_defaults(self, tmp_state):
        state_dir, state_file = tmp_state
        state_dir.mkdir(parents=True)
        state_file.write_text(json.dumps({"show_splash": False}),
                              encoding="utf-8")
        loaded = preferences.load()
        assert loaded["show_splash"] is False
        assert loaded["auto_open_last_save"] is False  # default
        assert loaded["last_save_adf"] == ""           # default

    def test_wrong_type_values_fall_back_to_defaults(self, tmp_state):
        state_dir, state_file = tmp_state
        state_dir.mkdir(parents=True)
        state_file.write_text(json.dumps({
            "show_splash":         "yes",     # wrong: should be bool
            "auto_open_last_save": 1,         # wrong: should be bool
            "last_save_adf":       ["/foo"],  # wrong: should be str
        }), encoding="utf-8")
        loaded = preferences.load()
        assert loaded["show_splash"] is True      # default
        assert loaded["auto_open_last_save"] is False  # default
        assert loaded["last_save_adf"] == ""      # default

    def test_unknown_keys_are_ignored(self, tmp_state):
        state_dir, state_file = tmp_state
        state_dir.mkdir(parents=True)
        state_file.write_text(json.dumps({
            "show_splash": False,
            "garbage_key": 42,
        }), encoding="utf-8")
        loaded = preferences.load()
        assert "garbage_key" not in loaded
        assert loaded["show_splash"] is False


class TestSave:
    def test_round_trip(self, tmp_state):
        original = preferences.default_state()
        original["show_splash"] = False
        original["auto_open_last_save"] = True
        original["last_save_adf"] = "/tmp/demo.adf"
        preferences.save(original)
        assert preferences.load() == original

    def test_creates_state_directory_if_missing(self, tmp_state):
        state_dir, _ = tmp_state
        assert not state_dir.exists()
        preferences.save(preferences.default_state())
        assert state_dir.exists()

    def test_drops_unknown_keys(self, tmp_state):
        state_dir, state_file = tmp_state
        preferences.save({**preferences.default_state(), "garbage": 99})
        raw = json.loads(state_file.read_text(encoding="utf-8"))
        assert "garbage" not in raw

    def test_wrong_type_values_replaced_with_defaults_on_save(self, tmp_state):
        preferences.save({
            "show_splash": "yes",         # wrong
            "last_game_adf": "/tmp/g.adf",
        })
        loaded = preferences.load()
        assert loaded["show_splash"] is True        # default
        assert loaded["last_game_adf"] == "/tmp/g.adf"

    def test_no_tmp_artefacts_after_successful_save(self, tmp_state):
        state_dir, _ = tmp_state
        preferences.save(preferences.default_state())
        leftovers = [p for p in os.listdir(state_dir) if p.startswith("pref-")]
        assert leftovers == []

    def test_save_is_atomic_final_file_is_valid_json(self, tmp_state):
        state_dir, state_file = tmp_state
        preferences.save(preferences.default_state())
        # File must parse as JSON on its own — if a partial write had
        # happened, ``json.load`` would raise.
        with open(state_file, encoding="utf-8") as f:
            assert isinstance(json.load(f), dict)
