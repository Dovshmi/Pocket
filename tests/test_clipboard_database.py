"""Pocket v1.37 local Clipboard history and privacy regressions."""
from datetime import datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from PIL import Image

from pocket import clipboard_database as clipdb, clipboard_images, clipboard_gallery
from pocket import hotkey_settings
import runpy

APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                     run_name="clipboard_database_tests")
Desk = APP["PocketDesk"]


class ClipboardDatabaseTests(unittest.TestCase):
    def test_defaults_are_ram_mark_enabled_one_day(self):
        normalized = APP["normalize_settings"]({})
        self.assertEqual(normalized["clipboard_storage"], "ram")
        self.assertEqual(normalized["clipboard_days"], 1)
        self.assertEqual(normalized["convert_mode"], "mark")
        self.assertTrue(normalized["convert_enabled"])
        for invalid in (0, 6, "5", True, False, None, -3):
            self.assertEqual(clipdb.normalize_days(invalid), 1)
        self.assertEqual(clipdb.normalize_days(5), 5)
        self.assertEqual(APP["normalize_settings"]({
            "clipboard_storage": "DATABASE"})["clipboard_storage"], "ram")

    def test_daily_text_file_has_creation_time_and_expiry_and_unicode(self):
        with tempfile.TemporaryDirectory() as folder:
            db = clipdb.ClipboardDatabase(folder)
            self.assertFalse(db.root.exists())
            now = datetime(2026, 11, 17, 23, 31, 42)
            item = {"id": "a" * 32, "text": "שלום\nהמשך", "pinned": True,
                    "time": "23:31:42"}
            db.save_text("2026-11-17", [item], days=2, on=now)
            self.assertEqual(
                [x.name for x in db.text_dir.iterdir()],
                ["2026-11-17_23-31-42_to_2026-11-19.txt"])
            self.assertEqual(db.load_text("2026-11-17"), [item])
            self.assertEqual(db.days("text", days=2, on="2026-11-18"),
                             ["2026-11-17"])
            raw = next(db.text_dir.iterdir()).read_text(encoding="utf-8")
            self.assertIn("שלום", raw)
            self.assertIn('"pinned":true', raw)
            self.assertEqual(json.loads(raw)["text"], "שלום\nהמשך")

    def test_same_day_edits_replace_original_file_and_recalculate_expiry(self):
        with tempfile.TemporaryDirectory() as folder:
            db = clipdb.ClipboardDatabase(folder)
            now = datetime(2026, 11, 17, 1, 2, 3)
            row = {"id": "a" * 32, "text": "one", "pinned": False, "time": "01:02:03"}
            db.save_text("2026-11-17", [row], days=1, on=now)
            row["pinned"] = True
            later = {"id": "b" * 32, "text": "two", "pinned": False, "time": "12:00:00"}
            db.save_text("2026-11-17", [later, row], days=5, on=now)
            self.assertEqual(len(list(db.text_dir.iterdir())), 1)
            self.assertEqual(next(db.text_dir.iterdir()).name,
                             "2026-11-17_01-02-03_to_2026-11-22.txt")
            self.assertEqual(db.load_text("2026-11-17"), [later, row])
            db.save_text("2026-11-17", [], days=5, on=now)
            self.assertEqual(db.load_text("2026-11-17"), [])

    def test_screenshots_stored_by_day_without_ram_capacity_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            db = clipdb.ClipboardDatabase(folder)
            for i in range(33):
                history = []
                self.assertTrue(clipboard_images.add_image(
                    history, Image.new("RGB", (14, 15), (i, 60, 22))))
                db.save_image("2026-11-17", history[0])
            self.assertEqual(len(db.load_images("2026-11-17")), 33)
            self.assertEqual(len(list((db.image_dir / "2026-11-17").glob("*.png"))), 33)
            self.assertEqual(db.days("images", days=1, on="2026-11-17"),
                             ["2026-11-17"])
            self.assertEqual(db.load_images("2026-11-16"), [])
            item = db.load_images("2026-11-17")[0]
            db.delete_image("2026-11-17", item)
            self.assertEqual(len(db.load_images("2026-11-17")), 32)
            db.clear_images("2026-11-17")
            self.assertEqual(db.load_images("2026-11-17"), [])

    def test_retention_is_calendar_days_and_does_not_delete_unrelated_files(self):
        with tempfile.TemporaryDirectory() as folder:
            db = clipdb.ClipboardDatabase(folder)
            for day in ("2026-11-13", "2026-11-14", "2026-11-15",
                        "2026-11-16", "2026-11-17"):
                db.save_text(day, [{"id": "a" * 32, "text": day,
                                    "time": "12:00:00"}], days=5,
                             on=datetime.fromisoformat(day + "T12:00:00"))
                one = []
                clipboard_images.add_image(one, Image.new("RGB", (2, 3)))
                db.save_image(day, one[0])
            outside = db.text_dir / "keep-me.txt"
            outside.write_text("Do not delete", encoding="utf-8")
            other = db.image_dir / "2026-11-13" / "keep-me.txt"
            other.write_text("Keep", encoding="utf-8")
            db.prune(2, on="2026-11-17")
            self.assertEqual(db.days("text", days=2, on="2026-11-17"),
                             ["2026-11-17", "2026-11-16"])
            self.assertEqual(db.days("images", days=2, on="2026-11-17"),
                             ["2026-11-17", "2026-11-16"])
            self.assertTrue(outside.is_file())
            self.assertEqual(other.read_text(encoding="utf-8"), "Keep")
            self.assertFalse(list((db.image_dir / "2026-11-15").glob("*.png")))

    def test_bad_days_or_names_do_not_escape_profile_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            db = clipdb.ClipboardDatabase(folder)
            for day in ("../../test", "2026-02-30", "2026-1-1", "", "A"):
                with self.assertRaises(ValueError):
                    db.save_text(day, [])
                with self.assertRaises(ValueError):
                    db.save_image(day, {"id": "a"*32, "time": "12:00:00", "data": b""})
            with self.assertRaises(ValueError):
                db.delete_image("2026-11-17", {"file_name": "../../private"})
            self.assertFalse(db.root.exists())


class ClipboardIntegrationTests(unittest.TestCase):
    def _desk(self, directory):
        settings = APP["normalize_settings"]({
            "clipboard_storage": "ram", "clipboard_days": 2,
            "convert_mode": "mark"})
        events = []
        app = SimpleNamespace(
            path=Path(directory) / "data.json", settings=settings,
            clipboard_database=clipdb.ClipboardDatabase(directory),
            clipboard_items=[], clipboard_images=[],
            _ram_text_items=[], _ram_images=[],
            _clipboard_selected_image_id=None,
            _clipboard_capture_day=clipdb.today(),
            _clipboard_view_days={"text": clipdb.today(), "images": clipdb.today()},
            _clipboard_last=None, _clipboard_sequence=None,
            current_tab="away", clipboard_page="text",
            schedule_save=lambda: events.append("save"),
            _clipboard_report_io_error=lambda error: events.append(type(error).__name__),
            show_tab=lambda page: events.append("show:"+page),
            _refresh_clipboard=lambda: events.append("refresh"))
        app.clipboard_items = app._ram_text_items
        app.clipboard_images = app._ram_images
        app._clipboard_store_is_disk = lambda: Desk._clipboard_store_is_disk(app)
        app._clipboard_load_day = lambda page, day=None: Desk._clipboard_load_day(app, page, day)
        app._clipboard_on_new_text = lambda value: Desk._clipboard_on_new_text(app, value)
        app._clipboard_on_new_image = lambda image: Desk._clipboard_on_new_image(app, image)
        app._clipboard_write_text_view = lambda items: Desk._clipboard_write_text_view(app, items)
        return app, events

    def test_ram_never_creates_database_and_switch_roundtrip_preserves_ram(self):
        with tempfile.TemporaryDirectory() as folder:
            app, events = self._desk(folder)
            app._clipboard_on_new_text("RAM entry")
            self.assertFalse(app.clipboard_database.root.exists())
            with patch.object(clipboard_images, "sequence_number", return_value=42):
                Desk._clipboard_use_storage(app, "database")
                self.assertEqual(app.clipboard_items, [])
                self.assertEqual(app.settings["clipboard_storage"], "database")
                app._clipboard_on_new_text("Persisted entry")
                self.assertTrue(app.clipboard_database.text_dir.exists())
                Desk._clipboard_use_storage(app, "ram")
            self.assertEqual([x["text"] for x in app.clipboard_items], ["RAM entry"])
            self.assertEqual(app.clipboard_database.load_text(clipdb.today())[0]["text"],
                             "Persisted entry")
            self.assertNotIn("Persisted entry", [x["text"] for x in app._ram_text_items])

    def test_historical_selection_snaps_today_only_on_next_new_capture(self):
        with tempfile.TemporaryDirectory() as folder:
            app, _ = self._desk(folder)
            today = clipdb.today()
            old = (datetime.fromisoformat(today) -
                   __import__("datetime").timedelta(days=1)).date().isoformat()
            db = app.clipboard_database
            db.save_text(old, [{"id":"c"*32, "text":"old text", "time":"01:02:03"}],
                         days=2)
            Desk._clipboard_use_storage(app, "database")
            Desk._clipboard_choose_day(app, old)
            self.assertEqual(app._clipboard_view_days["text"], old)
            self.assertEqual(app.clipboard_items[0]["text"], "old text")
            app._clipboard_on_new_text("a new capture")
            self.assertEqual(app._clipboard_view_days["text"], today)
            self.assertEqual(app.clipboard_items[0]["text"], "a new capture")
            self.assertEqual(db.load_text(old)[0]["text"], "old text")

    def test_translate_off_prevents_hotkey_handling(self):
        with tempfile.TemporaryDirectory() as folder:
            app, events = self._desk(folder)
            app.tray = SimpleNamespace(error=None, set_convert_enabled=Mock())
            app._set_convert_enabled = lambda enabled: Desk._set_convert_enabled(app, enabled)
            app.settings["convert_enabled"] = True
            app._set_convert_enabled(False)
            app.tray.set_convert_enabled.assert_called_once_with(False)
            self.assertFalse(app.settings["convert_enabled"])
            self.assertEqual(events, ["save"])

    def test_only_db_changes_image_capacity_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            app, _ = self._desk(folder)
            app._ram_images[:] = [{"id": str(x)} for x in range(23)]
            Desk._set_clipboard_image_limit(app, 10)
            self.assertEqual(len(app._ram_images), 10)
            Desk._clipboard_use_storage(app, "database")
            app.clipboard_images[:] = [{"id": str(x)} for x in range(30)]
            Desk._set_clipboard_image_limit(app, 15)
            self.assertEqual(len(app.clipboard_images), 30)


if __name__ == "__main__":
    unittest.main()
