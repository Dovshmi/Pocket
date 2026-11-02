"""Dashboard Settings uses wide independent columns, existing persisted callbacks."""
from pathlib import Path
import unittest

from pocket import dashboard_settings_ui as wide
from pocket import settings_ui
from pocket import icon_themes as themes

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.pyw").read_text(encoding="utf-8")
CODE = (ROOT / "pocket" / "dashboard_settings_ui.py").read_text(encoding="utf-8")


class DashboardSettingsLayoutTests(unittest.TestCase):
    def test_dashboard_only_and_old_layout_unchanged(self):
        self.assertIn('if self.display_mode == "dashboard":\n            return dashboard_settings.build(self, self.body)', APP)
        self.assertIn('return settings_ui.build_settings(self, self.body)', APP)
        self.assertEqual(tuple(mode for mode, *_ in wide.MODE_DETAILS),
                         ("normal", "mini", "dashboard"))

    def test_sections_fit_independent_columns(self):
        self.assertIn('left.grid(row=0, column=0', CODE)
        self.assertIn('right.grid(row=0, column=1', CODE)
        self.assertIn('_section(left, c, "Appearance & layout"', CODE)
        self.assertIn('_section(left, c, "Extra Mini launcher"', CODE)
        self.assertIn('_section(left, c, "Keyboard & search"', CODE)
        self.assertIn('_section(right, c, "Visible tools"', CODE)
        self.assertIn('_section(right, c, "Clipboard & privacy"', CODE)
        self.assertIn("panel.pack(fill=\"x\", pady=(0, 13))", CODE)

    def test_all_existing_preferences_still_use_app_callbacks(self):
        for method in ("_set_display_mode", "_choose_theme",
                       "_set_visible_tab", "_set_extra_mini_enabled",
                       "_edit_extra_mini_from_settings", "_open_hotkey_picker",
                       "_open_global_search", "_set_clipboard_paused",
                       "_set_clipboard_sensitive_filter", "_hotkey_hint"):
            self.assertIn("app." + method, CODE)
        self.assertEqual(len(themes.THEME_ORDER), 6)
        self.assertEqual(len(settings_ui.TOOL_HELP), 7)
        self.assertNotIn("requests.get(", CODE)
        self.assertNotIn("urlopen(", CODE)

    def test_buttons_are_keyboard_accessible(self):
        self.assertIn("tk.Checkbutton(", CODE)
        self.assertIn("takefocus=True", CODE)
        self.assertIn("app.dashboard_settings_controls", CODE)


if __name__ == "__main__":
    unittest.main()
