"""Pocket v1.38: text selection status and history display settings."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import runpy
import tempfile
import unittest

from pocket import clipboard_database as database
from pocket import clipboard_images

ROOT = Path(__file__).resolve().parents[1]
APP = runpy.run_path(str(ROOT / "app.pyw"), run_name="test_clipboard_v138")
Desk = APP["PocketDesk"]


class ClipboardV138Tests(unittest.TestCase):
    def test_ram_image_choices_and_legacy_upgrade(self):
        self.assertEqual(clipboard_images.IMAGE_LIMIT_CHOICES,
                         (10, 15, 20, 25, 30))
        for option in clipboard_images.IMAGE_LIMIT_CHOICES:
            self.assertEqual(clipboard_images.normalize_limit(option), option)
        self.assertEqual(clipboard_images.normalize_limit(40), 30)
        self.assertEqual(clipboard_images.normalize_limit(100), 30)
        self.assertEqual(clipboard_images.normalize_limit(None), 20)
        self.assertEqual(APP["default_data"]()["settings"]["clipboard_image_limit"], 20)

    def test_text_choices_default_and_legacy_preferences(self):
        self.assertEqual(database.TEXT_DISPLAY_CHOICES,
                         (100, 300, 500, 800, 1000, 1200, 1500))
        self.assertEqual(APP["default_data"]()["settings"]["clipboard_text_display_limit"],
                         100)
        settings = APP["normalize_settings"]
        self.assertEqual(settings({})["clipboard_text_display_limit"], 100)
        for old in (10, 20, 30, 50, 90, 100):
            self.assertEqual(settings({"clipboard_text_display_limit": old})[
                "clipboard_text_display_limit"], 100)
        self.assertEqual(settings({"clipboard_text_display_limit": 200})[
            "clipboard_text_display_limit"], 300)
        for allowed in database.TEXT_DISPLAY_CHOICES:
            self.assertEqual(settings({"clipboard_text_display_limit": allowed})[
                "clipboard_text_display_limit"], allowed)
        for invalid in (True, False, "1500", None, -1, 0):
            self.assertEqual(settings({"clipboard_text_display_limit": invalid})[
                "clipboard_text_display_limit"], 100)
        # The screenshot database retains the independent 10–100 increments.
        self.assertEqual(settings({"clipboard_db_image_display_limit": 40})[
            "clipboard_db_image_display_limit"], 40)

    def test_1500_text_entries_available_in_one_batch_without_data_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            db = database.ClipboardDatabase(folder)
            day = "2026-11-17"
            items = [
                {"id": f"{index:032x}", "text": f"Text #{index}",
                 "time": "12:00:00", "pinned": False}
                for index in range(1512)
            ]
            db.save_text(day, items)
            first = db.load_text(day, limit=1500)
            self.assertEqual(len(first), 1500)
            self.assertEqual(first[0]["text"], "Text #0")
            self.assertEqual(first[-1]["text"], "Text #1499")
            second = db.load_text(day, limit=1500, offset=1500)
            self.assertEqual([row["text"] for row in second],
                             ["Text #1500", "Text #1501", "Text #1502",
                              "Text #1503", "Text #1504", "Text #1505",
                              "Text #1506", "Text #1507", "Text #1508",
                              "Text #1509", "Text #1510", "Text #1511"])
            self.assertEqual(len(db.load_text(day)), 1512)
            with self.assertRaises(ValueError):
                db.load_text(day, limit=1501)

    def test_text_count_uses_same_existing_status_label(self):
        status = Mock()
        status.winfo_exists.return_value = True
        listbox = Mock()
        listbox.curselection.return_value = (1,)
        fake = SimpleNamespace(
            clipboard_status=status, clipboard_list=listbox,
            _clipboard_filtered=[{"id": str(i)} for i in range(3)],
            settings={"clipboard_storage": "database",
                      "visible_tabs": ["clipboard"],
                      "clipboard_paused": False},
            display_mode="mini",
            _clipboard_view_days={"text": "2026-11-17"})
        fake._clipboard_store_is_disk = lambda: True
        Desk._update_clipboard_text_status(fake)
        message = status.config.call_args.kwargs["text"]
        self.assertIn("2 / 3 selected · 3 entries", message)
        self.assertIn("capture ON", message)
        self.assertNotIn("2026-11-17", message)
        listbox.curselection.return_value = ()
        Desk._update_clipboard_text_status(fake)
        self.assertIn("0 / 3 selected · 3 entries",
                      status.config.call_args.kwargs["text"])
        fake.settings["clipboard_paused"] = True
        Desk._update_clipboard_text_status(fake)
        self.assertIn("capture PAUSED", status.config.call_args.kwargs["text"])
        # No operations that alter widget position or geometry are called.
        status.pack.assert_not_called()
        status.grid.assert_not_called()
        status.place.assert_not_called()


if __name__ == "__main__":
    unittest.main()
