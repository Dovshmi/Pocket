"""Headless structural regressions for the modern Settings interface."""
from pathlib import Path
import runpy
import unittest

import icon_themes as themes
import settings_ui
import compact_dashboard as compact

app = runpy.run_path(str((Path(__file__).resolve().parents[1] / "app.pyw")), run_name="test_import")


class ModernSettingsTests(unittest.TestCase):
    def test_all_working_layouts_have_selection_cards(self):
        keys = [mode for mode, _icon, _title, _detail in settings_ui.LAYOUTS]
        self.assertEqual(keys, ["normal", "mini", "dashboard"])
        self.assertNotIn("compact", keys)

    def test_every_existing_menu_has_an_accessible_toggle_and_description(self):
        menus = {key for key, _title in app["VISIBLE_TABS"]}
        self.assertEqual(set(settings_ui.TOOL_HELP), menus)
        self.assertEqual(set(settings_ui.TOOL_ICONS), menus)

    def test_theme_palette_is_shared_with_all_modes(self):
        for name in themes.THEME_ORDER:
            c = themes.palette(name)
            for field in ("BG", "PANEL", "CARD", "CARD_HOVER", "ACCENT",
                          "ACCENT_DARK", "INPUT", "BORDER"):
                self.assertTrue(c[field].startswith("#"))

    def test_settings_builder_shared_between_modes(self):
        source = (Path(__file__).resolve().parents[1] / "app.pyw").read_text(encoding="utf-8")
        self.assertIn("return settings_ui.build_settings(self, self.body)", source)
        self.assertIn("self._edit_extra_mini_from_settings", source)
        self.assertIn("self._return_to_compact()", source)
        self.assertIn("self._set_extra_mini_enabled", source)

    def test_empty_slots_survive_json_settings_round_trip(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            data = app["default_data"]()
            data["settings"]["extra_mini_enabled"] = True
            data["settings"]["extra_mini_tiles"] = ["notes", None, None, "commands"]
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["settings"]["extra_mini_tiles"],
                             ["notes", None, None, "commands"])
            self.assertEqual(compact.display_slots(
                loaded["settings"]["visible_tabs"],
                loaded["settings"]["extra_mini_tiles"]),
                ("notes", None, None, "commands"))


if __name__ == "__main__":
    unittest.main()
