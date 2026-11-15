"""Clipboard history rows must not add a fake indent."""
import unittest

from pocket.clipboard_gallery import text_row_label


class ClipboardAlignmentTests(unittest.TestCase):
    def test_unpinned_rows_start_with_actual_content(self):
        item = {"text": "Go to file Dovshmi release", "pinned": False}
        self.assertEqual(text_row_label(item), item["text"])
        self.assertFalse(text_row_label(item).startswith(" "))

    def test_pinned_rows_keep_visible_star_not_blank_prefix(self):
        item = {"text": "show ip interface brief", "pinned": True}
        self.assertEqual(text_row_label(item), "★ show ip interface brief")

    def test_whitespace_normalization_and_preview_limit_unchanged(self):
        item = {"text": "alpha  \n beta  \t gamma", "pinned": False}
        self.assertEqual(text_row_label(item), "alpha beta gamma")
        long = {"text": "x" * 100, "pinned": False}
        self.assertEqual(text_row_label(long), "x" * 65)

    def test_formatting_does_not_mutate_or_store_clipboard_text(self):
        item = {"text": "   copied text", "pinned": False}
        before = dict(item)
        self.assertEqual(text_row_label(item), "copied text")
        self.assertEqual(item, before)


if __name__ == "__main__":
    unittest.main()
