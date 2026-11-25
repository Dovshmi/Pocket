"""Settings' shared renderer keeps Dashboard wide and all options functional."""
from pathlib import Path
import unittest

from pocket import dashboard_settings_ui as wide
from pocket import settings_ui
from pocket import icon_themes as themes

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.pyw").read_text(encoding="utf-8")
ADAPTER = (ROOT / "pocket" / "dashboard_settings_ui.py").read_text(encoding="utf-8")
SHARED = (ROOT / "pocket" / "settings_ui.py").read_text(encoding="utf-8")


class DashboardSettingsLayoutTests(unittest.TestCase):
    def test_dashboard_and_other_modes_share_one_modern_renderer(self):
        self.assertIn(
            'if self.display_mode == "dashboard":\n'
            '            return dashboard_settings.build(self, self.body)', APP)
        self.assertIn('return settings_ui.build_settings(self, self.body)', APP)
        self.assertIn('return settings_ui.build_settings(app, parent, wide=True)', ADAPTER)
        self.assertEqual(tuple(mode for mode, *_ in settings_ui.LAYOUTS),
                         ("normal", "mini", "dashboard"))
        self.assertTrue(callable(wide.build))

    def test_dashboard_has_independent_columns(self):
        self.assertIn('left.grid(row=0, column=0', SHARED)
        self.assertIn('right.grid(row=0, column=1', SHARED)
        self.assertIn('app._settings_sections = {}', SHARED)
        self.assertIn('_appearance(appearance, app, c, wide=wide', SHARED)
        self.assertIn('_shortcuts(shortcuts, app, c, wide=wide', SHARED)
        self.assertIn('_launcher(shortcuts, app, c, wide=wide', SHARED)
        self.assertNotIn('_tools(tools, app, c, wide=wide', SHARED)
        self.assertNotIn('menu_order_ui.build(card, app, c', SHARED)
        self.assertIn('_set_menu_order', APP)
        self.assertIn('_mini_nav_context_menu', APP)
        self.assertIn('_show_mini_add_menu', APP)
        self.assertIn('_clipboard(clipboard, app, c, wide=wide', SHARED)
        self.assertIn('_quick_slot_preferences(slot_controls, app, c,', SHARED)
        self.assertIn('_translate_preferences(slot_controls, app, c,', SHARED)
        self.assertIn('_network_preferences(network, app, c,', SHARED)
        self.assertIn('_backup_controls(maintenance, app, c,', SHARED)

    def test_every_existing_preference_keeps_its_app_callback(self):
        for method in (
                "_apply_window_profile", "_save_window_profile", "_delete_window_profile", "_choose_theme",
                "_set_extra_mini_enabled", "_edit_extra_mini_from_settings",
                "_open_hotkey_picker", "_open_convert_hotkey_picker",
                "_open_global_search", "_set_clipboard_paused",
                "_set_clipboard_sensitive_filter", "_hotkey_hint"):
            self.assertIn("app." + method, SHARED)
        # The visibility toggle is now exposed through Mini's right-click
        # context menu / Plus, not duplicated inside Settings.
        self.assertIn("def _set_visible_tab(self, key, enabled)", APP)
        self.assertNotIn('menu_order_ui.build(', SHARED)
        self.assertEqual(len(themes.THEME_ORDER), 6)
        self.assertEqual(len(settings_ui.TOOL_HELP), len(settings_ui.TOOL_ICONS))
        for code in (ADAPTER, SHARED):
            self.assertNotIn("requests.get(", code)
            self.assertNotIn("urlopen(", code)

    def test_switches_and_choices_are_keyboard_accessible(self):
        self.assertIn("tk.Checkbutton(", SHARED)
        self.assertIn("indicatoron=False", SHARED)
        self.assertIn("takefocus=True", SHARED)
        self.assertIn("control.invoke()", SHARED)
        self.assertIn("app.dashboard_settings_controls = app.settings_controls", SHARED)


if __name__ == "__main__":
    unittest.main()
