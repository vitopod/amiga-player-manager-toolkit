"""Unit tests for the help-text search helper."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pm_core import help_text


class TestHelpSearch(unittest.TestCase):
    def test_empty_query_returns_empty(self):
        self.assertEqual(help_text.search(""), [])
        self.assertEqual(help_text.search("   "), [])

    def test_case_insensitive(self):
        lower = help_text.search("market")
        upper = help_text.search("MARKET")
        self.assertEqual(lower, upper)
        self.assertGreater(len(lower), 0)

    def test_hit_fields(self):
        hits = help_text.search("save disk")
        self.assertGreater(len(hits), 0)
        hit = hits[0]
        self.assertIn(hit.topic, help_text.HELP)
        self.assertEqual(hit.title, help_text.HELP[hit.topic]["title"])
        self.assertIn("save disk", hit.line.lower())
        self.assertGreaterEqual(hit.line_no, 1)

    def test_markup_stripped_from_line(self):
        hits = help_text.search("What this window does")
        self.assertGreater(len(hits), 0)
        self.assertFalse(hits[0].line.startswith("#"))
        self.assertFalse(hits[0].line.startswith("-"))

    def test_no_hits_for_nonsense(self):
        self.assertEqual(help_text.search("xyzzy_definitely_not_in_help"), [])

    def test_hits_ordered_by_topic_then_line(self):
        hits = help_text.search("the")
        if len(hits) < 2:
            self.skipTest("not enough hits to verify order")
        prev_topic_idx = -1
        prev_line_no = -1
        topics = list(help_text.HELP.keys())
        for hit in hits:
            topic_idx = topics.index(hit.topic)
            if topic_idx > prev_topic_idx:
                prev_topic_idx = topic_idx
                prev_line_no = hit.line_no
            else:
                self.assertEqual(topic_idx, prev_topic_idx)
                self.assertGreater(hit.line_no, prev_line_no)
                prev_line_no = hit.line_no

    def test_per_topic_cap(self):
        all_hits = help_text.search("the", max_hits_per_topic=1000)
        capped = help_text.search("the", max_hits_per_topic=1)
        self.assertLessEqual(len(capped), len(help_text.HELP))
        self.assertLessEqual(len(capped), len(all_hits))


if __name__ == "__main__":
    unittest.main()
