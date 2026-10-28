"""Small, display-independent tests for Pocket clipboard privacy and preferences."""
import unittest
from pathlib import Path
import tempfile
import importlib.util

SPEC = importlib.util.spec_from_file_location("pocket_app", Path(__file__).with_name("app.pyw"))
# SourceFileLoader explicitly supports the Windows .pyw extension.
from importlib.machinery import SourceFileLoader
SPEC.loader = SourceFileLoader("pocket_app", str(Path(__file__).with_name("app.pyw")))
app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(app)


class ClipboardSettingsTests(unittest.TestCase):
    def test_capture_off_by_default(self):
        self.assertIn("clipboard", app.normalize_settings(None)["visible_tabs"])

    def test_bad_preferences_are_sanitized(self):
        prefs = app.normalize_settings({
                                        "visible_tabs": ["clipboard", "fake", "clipboard"]})
        self.assertEqual(prefs["visible_tabs"], ["clipboard"])

    def test_note_reminder_due_once(self):
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        note = app.new_note("Test")
        note["reminder_enabled"] = True
        note["reminder_at"] = (now - timedelta(minutes=2)).isoformat()
        self.assertTrue(app.reminder_is_due(note, now))
        note["reminder_sent_at"] = now.isoformat()
        self.assertFalse(app.reminder_is_due(note, now))

    def test_note_reminder_migration(self):
        old = app.new_note()
        old.pop("reminder_at")
        old.pop("reminder_enabled")
        app.normalize_note_reminder(old)
        self.assertFalse(old["reminder_enabled"])
        self.assertEqual(old["reminder_at"], "")

    def test_clipboard_dedupe_and_limit(self):
        history = []
        app.clipboard_add(history, "hello", maximum=2)
        app.clipboard_add(history, "hello", maximum=2)
        app.clipboard_add(history, "world", maximum=2)
        app.clipboard_add(history, "third", maximum=2)
        self.assertEqual([item["text"] for item in history], ["third", "world"])
        self.assertIsNone(app.sanitize_clipboard(" "))

    def test_clipboard_not_in_persisted_data(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "data.json"
            data = app.default_data()
            app.save_data(path, data)
            self.assertNotIn("clipboard_items", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
