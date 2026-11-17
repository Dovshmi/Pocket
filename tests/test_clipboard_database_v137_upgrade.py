"""Final v1.37 regressions: append-only text, flat image migration and opt-in deletion."""
from datetime import date, datetime, timedelta
from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from PIL import Image

from pocket import clipboard_database as dbm, clipboard_images


class DailyArchiveUpgradeTests(unittest.TestCase):
    def test_default_is_no_deletion_and_days_7_through_30_are_valid(self):
        self.assertEqual(dbm.normalize_autodelete_days(None), 0)
        self.assertEqual(dbm.normalize_autodelete_days(0), 0)
        for n in range(7, 31):
            self.assertEqual(dbm.normalize_autodelete_days(n), n)
        for bad in (1, 5, 6, 31, "7", True, -1):
            self.assertEqual(dbm.normalize_autodelete_days(bad), 0)

    def test_text_appends_without_rewriting_entire_file_and_only_loads_page(self):
        with tempfile.TemporaryDirectory() as directory:
            db = dbm.ClipboardDatabase(directory)
            day = "2026-11-17"
            for number in range(110):
                db.append_text(day, {
                    "id": f"{number:032x}", "text": f"message {number}",
                    "time": "14:01:22", "pinned": False}, days=0)
            path = next(db.text_dir.glob("*.txt"))
            self.assertEqual(path.name.endswith("_to_saved.txt"), True)
            self.assertEqual(sum(1 for _ in path.open(encoding="utf-8")), 110)
            page1 = db.load_text(day, limit=10)
            page2 = db.load_text(day, limit=10, offset=10)
            self.assertEqual([x["text"] for x in page1],
                             [f"message {n}" for n in range(109, 99, -1)])
            self.assertEqual(page2[0]["text"], "message 99")
            self.assertEqual(db.last_text(day)["text"], "message 109")
            db.prune(days=0, on="2027-01-17")
            self.assertTrue(path.exists())
            self.assertEqual(len(db.load_text(day)), 110)

    def test_legacy_daily_text_migrates_once_when_appending_new_line(self):
        with tempfile.TemporaryDirectory() as folder:
            db = dbm.ClipboardDatabase(folder)
            db.ensure_folders()
            day = "2026-11-17"
            file = db.text_dir / f"{day}_08-00-00_to_2026-11-18.txt"
            old = [
                {"id": "b"*32, "text": "recent", "time": "09:00:00", "pinned": True},
                {"id": "a"*32, "text": "older", "time": "08:00:00", "pinned": False}
            ]
            file.write_text("".join(json.dumps(row) + "\n" for row in old),
                            encoding="utf-8")
            self.assertEqual([i["text"] for i in db.load_text(day)],
                             ["recent", "older"])
            db.append_text(day, {"id": "c"*32, "text": "new",
                                 "time": "10:00:00"}, days=0)
            self.assertEqual([i["text"] for i in db.load_text(day)],
                             ["new", "recent", "older"])
            self.assertEqual(len(list(db.text_dir.glob("*.txt"))), 1)
            records = [json.loads(line) for line in
                       next(db.text_dir.glob("*.txt")).read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(row.get("v") == 2 for row in records))

    def test_flat_screenshot_storage_with_memory_bounded_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            db = dbm.ClipboardDatabase(folder)
            day = "2026-11-17"
            for n in range(56):
                result = []
                clipboard_images.add_image(result, Image.new(
                    "RGB", (60, 45), (n, 40, 60)))
                db.save_image(day, result[0])
            self.assertEqual(len(list(db.image_dir.glob("*.png"))), 56)
            self.assertTrue(all(p.is_file() for p in db.image_dir.iterdir()))
            self.assertEqual(len(db.load_images(day, limit=30, metadata_only=True)), 30)
            second = db.load_images(day, limit=30, offset=30, metadata_only=True)
            self.assertEqual(len(second), 26)
            self.assertTrue(all("data" not in row for row in second))
            payload = db.image_data(second[0])
            self.assertTrue(payload.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(len(list(db.image_dir.glob("*.png"))), 56)
            self.assertEqual(db.days("images", on=day), [day])

    def test_same_second_screenshots_sort_by_microseconds(self):
        with tempfile.TemporaryDirectory() as folder:
            db = dbm.ClipboardDatabase(folder)
            day = "2026-11-17"
            first = []
            second = []
            clipboard_images.add_image(first, Image.new("RGB", (12, 12), (10, 20, 30)))
            clipboard_images.add_image(second, Image.new("RGB", (12, 12), (20, 30, 40)))
            first[0]["time"] = "14:12:22"
            second[0]["time"] = "14:12:22"
            class Clock:
                count = 0
                @classmethod
                def now(cls):
                    cls.count += 1
                    return SimpleNamespace(microsecond=cls.count)
            with patch.object(dbm, "datetime", Clock):
                db.save_image(day, first[0])
                db.save_image(day, second[0])
            displayed = db.load_images(day, limit=2, metadata_only=True)
            self.assertEqual([record["id"] for record in displayed],
                             [second[0]["id"], first[0]["id"]])
            self.assertTrue(all("data" not in item for item in displayed))

    def test_legacy_daily_png_folders_migrate_safely_without_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            db = dbm.ClipboardDatabase(folder)
            db.ensure_folders()
            old = db.image_dir / "2026-11-16"
            old.mkdir()
            result = []
            clipboard_images.add_image(result, Image.new("RGB", (12, 12)))
            image = result[0]
            source = old / f"11-23-04_{image['id']}.png"
            source.write_bytes(image["data"])
            unrelated = old / "readme.txt"
            unrelated.write_text("keep", encoding="utf-8")
            moved = db.migrate_screenshots()
            self.assertEqual(moved, 1)
            target = db.image_dir / f"2026-11-16_{source.name}"
            self.assertEqual(target.read_bytes(), image["data"])
            self.assertFalse(source.exists())
            self.assertTrue(unrelated.exists())
            self.assertEqual(db.migrate_screenshots(), 0)
            self.assertEqual(db.days("images", on="2026-11-17"), ["2026-11-16"])
            self.assertEqual(len(db.load_images("2026-11-16", metadata_only=True)), 1)

    def test_migration_collision_never_overwrites_or_removes_old_file(self):
        with tempfile.TemporaryDirectory() as folder:
            db = dbm.ClipboardDatabase(folder)
            db.ensure_folders()
            sub = db.image_dir / "2026-11-16"
            sub.mkdir()
            name = "11-23-04_" + "a"*32 + ".png"
            (sub / name).write_bytes(b"old")
            (db.image_dir / f"2026-11-16_{name}").write_bytes(b"different")
            self.assertEqual(db.migrate_screenshots(), 0)
            self.assertEqual((sub / name).read_bytes(), b"old")
            self.assertEqual((db.image_dir / f"2026-11-16_{name}").read_bytes(),
                             b"different")

    def test_optional_cleanup_deletes_only_expired_pocket_files(self):
        with tempfile.TemporaryDirectory() as folder:
            db = dbm.ClipboardDatabase(folder)
            today = date(2026, 11, 17)
            for ago in (0, 6, 7, 29, 30, 45):
                day = (today - timedelta(days=ago)).isoformat()
                db.save_text(day, [{
                    "id": f"{ago:032x}", "text": day, "time": "12:00:00"}],
                    days=0, on=datetime.fromisoformat(day + "T12:00:00"))
                result = []
                clipboard_images.add_image(result, Image.new(
                    "RGB", (8, 8), (ago, 7, 9)))
                db.save_image(day, result[0])
            unrelated = db.image_dir / "unrelated.png"
            unrelated.write_bytes(b"user data")
            db.update_retention(0, on=today.isoformat())
            self.assertEqual(len(db.days("text", on=today.isoformat())), 6)
            self.assertEqual(len(db.days("images", on=today.isoformat())), 6)
            db.update_retention(30, on=today.isoformat())
            expected = [(today - timedelta(days=x)).isoformat()
                        for x in (0, 6, 7, 29)]
            self.assertEqual(db.days("text", on=today.isoformat()), expected)
            self.assertEqual(db.days("images", on=today.isoformat()), expected)
            self.assertTrue(unrelated.exists())
            db.update_retention(7, on=today.isoformat())
            self.assertEqual(len(db.days("text", on=today.isoformat())), 2)
            self.assertEqual(len(db.days("images", on=today.isoformat())), 2)
            db.update_retention(0, on=today.isoformat())
            self.assertTrue(all("to_saved.txt" in p.name for p in db.text_dir.glob("*.txt")))

    def test_saved_text_edits_keep_unseen_rows(self):
        with tempfile.TemporaryDirectory() as folder:
            db = dbm.ClipboardDatabase(folder)
            day = "2026-11-17"
            for i in range(55):
                db.append_text(day, {
                    "id": f"{i:032x}", "text": f"text {i}",
                    "pinned": False, "time": "12:00:00"})
            page = db.load_text(day, limit=10)
            self.assertEqual(len(page), 10)
            all_rows = db.load_text(day)
            all_rows[0]["pinned"] = True
            db.save_text(day, all_rows, days=0)
            self.assertEqual(len(db.load_text(day)), 55)
            self.assertTrue(db.load_text(day, limit=1)[0]["pinned"])


if __name__ == "__main__":
    unittest.main()
