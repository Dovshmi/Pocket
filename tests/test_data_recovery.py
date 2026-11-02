"""Recovery handling must preserve notes and never silently discard originals."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pocket import data_recovery
import runpy

ROOT = Path(__file__).resolve().parents[1]
app = runpy.run_path(str(ROOT / "app.pyw"), run_name="recovery_test")


class DataRecoveryTests(unittest.TestCase):
    def test_previous_data_is_recoverable_after_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            first = app["default_data"]()
            first["notes"][0]["body"] = "Important עברית content"
            app["save_data"](path, first)
            second = app["default_data"]()
            second["notes"][0]["body"] = "A later edit"
            app["save_data"](path, second)
            self.assertEqual(json.loads(data_recovery.snapshot_path(path).read_text())["notes"][0]["body"],
                             "Important עברית content")
            path.write_text("{invalid", encoding="utf-8")
            recovered = []
            restored = app["load_data"](path, on_recovery=lambda *info: recovered.append(info))
            self.assertEqual(restored["notes"][0]["body"], "Important עברית content")
            self.assertEqual(len(recovered), 1)
            damaged, snapshot, _error = recovered[0]
            self.assertTrue(damaged.is_file())
            self.assertEqual(damaged.read_text(encoding="utf-8"), "{invalid")
            self.assertEqual(snapshot, data_recovery.snapshot_path(path))
            self.assertFalse(path.exists())
            app["save_data"](path, restored)
            self.assertEqual(app["load_data"](path)["notes"][0]["body"], "Important עברית content")

    def test_without_snapshot_preserves_corruption_and_reports_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text("invalid", encoding="utf-8")
            details = []
            default = app["load_data"](path, on_recovery=lambda *info: details.append(info))
            self.assertTrue(default["notes"])
            self.assertFalse(path.exists())
            self.assertIsNone(details[0][1])
            self.assertEqual(len(list(Path(folder).glob("data-corrupt-*.json"))), 1)

    def test_reject_malformed_in_memory_data_without_damaging_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            original = app["default_data"]()
            app["save_data"](path, original)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                app["save_data"](path, {"notes": [{"body": "x"}], "links": []})
            self.assertEqual(path.read_bytes(), before)

    def test_failure_while_quarantining_does_not_overwrite_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text("{broken", encoding="utf-8")
            with patch.object(data_recovery, "quarantine", side_effect=OSError("readonly")):
                with self.assertRaises(OSError):
                    app["load_data"](path)
            self.assertEqual(path.read_text(encoding="utf-8"), "{broken")

    def test_corrupted_snapshot_is_preserved_for_manual_inspection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text("{broken", encoding="utf-8")
            snapshot = data_recovery.snapshot_path(path)
            snapshot.write_text("{also broken", encoding="utf-8")
            info = []
            app["load_data"](path, on_recovery=lambda *details: info.append(details))
            self.assertIsNone(info[0][1])
            self.assertEqual(snapshot.read_text(encoding="utf-8"), "{also broken")


if __name__ == "__main__":
    unittest.main()
