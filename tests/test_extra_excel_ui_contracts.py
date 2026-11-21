"""Regressions for Pocket Extra Mini's compact controls and Settings DB link."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pocket import extra_excel_ui, settings_ui


class ExtraMiniLayoutTests(unittest.TestCase):
    def test_one_right_aligned_keyboard_accessible_switch(self):
        source = Path(extra_excel_ui.__file__).read_text(encoding="utf-8")
        self.assertIn('mode_choices.pack(side="right"', source)
        self.assertIn('mode_switch = tk.Canvas(', source)
        self.assertIn('mode_switch.bind("<Button-1>", toggle_mode)', source)
        self.assertIn('mode_switch.bind("<space>", toggle_mode)', source)
        self.assertIn('mode_switch.bind("<Return>", toggle_mode)', source)
        self.assertIn('MODE: Live / Offline', source)
        self.assertIn('local_caption, "local"', source)
        self.assertIn('database_caption, "database"', source)
        self.assertNotIn('mode_buttons = {}', source)

    def test_quiet_excel_hint_and_split_database_actions(self):
        source = Path(extra_excel_ui.__file__).read_text(encoding="utf-8")
        self.assertIn('Excel file · e.g. Extranet_2026.xlsx', source)
        self.assertIn('sync_button.pack(side="left"', source)
        self.assertIn('import_button.pack(side="right"', source)
        self.assertIn('delete_button.pack(side="right"', source)
        self.assertIn('if not compact:', source)

    def test_settings_does_not_show_missing_database(self):
        # No Tk root needed: missing files should not create a Settings section.
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "extra_excel_index.sqlite3"
            with patch.object(settings_ui.extra_db, "database_path",
                              return_value=missing), patch.object(
                                  settings_ui, "_section",
                                  side_effect=AssertionError("unexpected DB panel")):
                self.assertIsNone(settings_ui._extra_database_file(
                    None, None, {}, compact=True))
            self.assertFalse(missing.exists())

    def test_settings_shows_actual_active_file_not_workbook_path(self):
        source = Path(settings_ui.__file__).read_text(encoding="utf-8")
        self.assertIn('if not path.is_file():', source)
        self.assertIn('str(path)', source)
        self.assertIn('Copy path', source)
        self.assertIn('_extra_database_file(right, app, c,', source)


if __name__ == "__main__":
    unittest.main()
