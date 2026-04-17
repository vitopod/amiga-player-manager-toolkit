"""Unit tests for the update-check state logic."""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core import updates


class TestVersionTuple(unittest.TestCase):
    def test_plain_dotted(self):
        self.assertEqual(updates.version_tuple("2.2.1"), (2, 2, 1))

    def test_double_digit_component_orders_after_single(self):
        self.assertLess(updates.version_tuple("2.2.1"),
                        updates.version_tuple("2.2.10"))

    def test_strips_leading_v(self):
        self.assertEqual(updates.version_tuple("v2.3.0"), (2, 3, 0))

    def test_handles_pre_release_suffix(self):
        self.assertEqual(updates.version_tuple("2.2.1-rc1"), (2, 2, 1))

    def test_short_forms(self):
        self.assertEqual(updates.version_tuple("2.3"), (2, 3))
        self.assertEqual(updates.version_tuple("10"), (10,))


class TestIsNewer(unittest.TestCase):
    def test_true_for_patch_bump(self):
        self.assertTrue(updates.is_newer("2.2.2", "2.2.1"))

    def test_false_when_equal(self):
        self.assertFalse(updates.is_newer("2.2.2", "2.2.2"))

    def test_false_when_older(self):
        self.assertFalse(updates.is_newer("2.2.1", "2.2.2"))

    def test_tag_with_v_prefix(self):
        self.assertTrue(updates.is_newer("v2.3.0", "2.2.9"))


class TestShouldCheck(unittest.TestCase):
    def test_false_when_opted_out(self):
        s = updates.default_state()
        s["opted_in"] = False
        self.assertFalse(updates.should_check(s, now=1_000_000.0))

    def test_false_when_not_asked_yet(self):
        s = updates.default_state()  # opted_in = None
        self.assertFalse(updates.should_check(s, now=1_000_000.0))

    def test_true_when_opted_in_and_never_checked(self):
        s = updates.default_state()
        s["opted_in"] = True
        self.assertTrue(updates.should_check(s, now=1_000_000.0))

    def test_false_within_24h(self):
        s = updates.default_state()
        s["opted_in"] = True
        s["last_check_at"] = 1_000_000.0
        self.assertFalse(updates.should_check(
            s, now=1_000_000.0 + updates.CHECK_INTERVAL_SEC - 1))

    def test_true_after_24h(self):
        s = updates.default_state()
        s["opted_in"] = True
        s["last_check_at"] = 1_000_000.0
        self.assertTrue(updates.should_check(
            s, now=1_000_000.0 + updates.CHECK_INTERVAL_SEC + 1))


class TestStateLocation(unittest.TestCase):
    """The state file must live under the user's home directory so it
    survives reinstalling or updating the toolkit. If a future refactor
    moves it inside the source tree, this test stops it cold."""

    def test_state_dir_is_under_home(self):
        home = os.path.realpath(os.path.expanduser("~"))
        self.assertTrue(
            os.path.realpath(updates.STATE_DIR).startswith(home + os.sep),
            f"STATE_DIR must live under the home directory "
            f"(got {updates.STATE_DIR!r})",
        )

    def test_state_file_is_inside_state_dir(self):
        self.assertEqual(
            os.path.dirname(os.path.realpath(updates.STATE_FILE)),
            os.path.realpath(updates.STATE_DIR),
        )


class TestLoadSaveState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self._patch = mock.patch.multiple(
            updates,
            STATE_DIR=self.tmp.name,
            STATE_FILE=os.path.join(self.tmp.name, "update_check.json"),
        )
        self._patch.start()
        self.addCleanup(self._patch.stop)

    def test_missing_file_returns_defaults(self):
        self.assertEqual(updates.load_state(), updates.default_state())

    def test_roundtrip(self):
        s = updates.default_state()
        s["opted_in"] = True
        s["last_check_at"] = 123.0
        s["latest_version"] = "2.3.0"
        s["release_url"] = "https://example.test/r"
        updates.save_state(s)
        self.assertEqual(updates.load_state(), s)

    def test_malformed_file_returns_defaults(self):
        with open(updates.STATE_FILE, "w") as f:
            f.write("{{not json")
        self.assertEqual(updates.load_state(), updates.default_state())

    def test_partial_file_merges_with_defaults(self):
        with open(updates.STATE_FILE, "w") as f:
            f.write('{"opted_in": true}')
        s = updates.load_state()
        self.assertTrue(s["opted_in"])
        self.assertEqual(s["last_check_at"], 0.0)
        self.assertEqual(s["latest_version"], "")


class TestFetchLatest(unittest.TestCase):
    """Fetch is network-facing; only check error paths deterministically."""

    def test_returns_none_on_url_error(self):
        import urllib.error
        with mock.patch("urllib.request.urlopen",
                        side_effect=urllib.error.URLError("offline")):
            self.assertIsNone(updates.fetch_latest(timeout=0.1))

    def test_returns_none_on_timeout(self):
        with mock.patch("urllib.request.urlopen",
                        side_effect=TimeoutError("slow")):
            self.assertIsNone(updates.fetch_latest(timeout=0.1))

    def test_parses_tag_and_url(self):
        body = b'{"tag_name": "v2.3.0", "html_url": "https://example.test/r"}'
        resp = mock.MagicMock()
        resp.read.return_value = body
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        with mock.patch("urllib.request.urlopen", return_value=resp):
            got = updates.fetch_latest(timeout=0.1)
        self.assertEqual(got, ("2.3.0", "https://example.test/r"))

    def test_missing_tag_returns_none(self):
        body = b'{"html_url": "https://example.test/r"}'
        resp = mock.MagicMock()
        resp.read.return_value = body
        resp.__enter__.return_value = resp
        resp.__exit__.return_value = False
        with mock.patch("urllib.request.urlopen", return_value=resp):
            self.assertIsNone(updates.fetch_latest(timeout=0.1))


if __name__ == "__main__":
    unittest.main()
