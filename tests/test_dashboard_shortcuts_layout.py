"""Dashboard Shortcuts uses a compact, responsive view without changing Mini/Normal."""
from pathlib import Path
import unittest

from pocket import dashboard_shortcuts_ui as wide

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.pyw").read_text(encoding="utf-8")
UI = (ROOT / "pocket" / "dashboard_shortcuts_ui.py").read_text(encoding="utf-8")


class DashboardShortcutsTests(unittest.TestCase):
    def test_responsive_columns(self):
        self.assertEqual(wide.column_count(350), 1)
        self.assertEqual(wide.column_count(540), 2)
        self.assertEqual(wide.column_count(780), 2)
        self.assertEqual(wide.column_count(850), 3)

    def test_metadata_and_truncation(self):
        self.assertEqual(wide.preview_target({"kind": "url",
                         "url": "https://example.org/path"}), "example.org")
        self.assertEqual(wide.preview_target({"kind": "file",
                         "url": r"C:\\Work\\memo.txt"}), r"C:\\Work\\memo.txt")
        self.assertEqual(wide.shorten("Hello", 10), "Hello")
        self.assertTrue(wide.shorten("A longer title", 7).endswith("…"))

    def test_dashboard_dispatch_only(self):
        self.assertIn('if self.display_mode == "dashboard":\n            return dashboard_shortcuts.build(self)', APP)
        self.assertIn('if self.display_mode == "dashboard":\n            return dashboard_shortcuts.refresh(self)', APP)
        self.assertIn('if self.display_mode == "dashboard":\n            return dashboard_shortcuts.toggle_form(self, item, draft=draft)', APP)
        self.assertIn('if self.display_mode == "dashboard":\n            return dashboard_shortcuts.close_form(self)', APP)
        # The existing Normal/Mini flows must remain present and operational.
        self.assertIn('self._section_title(self.body, "Quick shortcuts"', APP)
        self.assertIn("def _link_tile(self, link):", APP)

    def test_dashboard_reuses_safe_shortcut_callbacks(self):
        for name in ("_register_shortcut_drop", "_toggle_link_form", "_save_link",
                     "_browse_shortcut", "_close_form", "open_shortcut",
                     "_copy_shortcut", "_show_link_menu", "refresh_links"):
            self.assertIn("app." + name, UI)
        self.assertIn("tk.Canvas(frame", UI)
        self.assertIn('style="Pocket.Vertical.TScrollbar"', UI)
        self.assertIn("app.links_stack.grid_columnconfigure(", UI)


if __name__ == "__main__":
    unittest.main()
