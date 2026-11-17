"""Headless structural regressions for the modern Settings interface."""
from pathlib import Path
import runpy
import unittest

from pocket import icon_themes as themes
from pocket import settings_ui
from pocket import compact_dashboard as compact

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

    def test_clipboard_image_limit_defaults_and_rejects_unsafe_values(self):
        from pocket import clipboard_images
        self.assertEqual(clipboard_images.IMAGE_LIMIT_CHOICES,
                         tuple(range(10, 101, 10)))
        self.assertEqual(app["default_data"]()["settings"]["clipboard_image_limit"], 20)
        for count in clipboard_images.IMAGE_LIMIT_CHOICES:
            self.assertEqual(app["normalize_settings"](
                {"clipboard_image_limit": count})["clipboard_image_limit"], count)
        for value in (-1, 0, 50, 100, 200, True, "30", 12.5, None):
            self.assertEqual(app["normalize_settings"](
                {"clipboard_image_limit": value})["clipboard_image_limit"], 20)

    def test_lowering_limit_drops_oldest_ram_images_and_updates_selection(self):
        from types import SimpleNamespace
        saved = []
        images = [{"id": str(i)} for i in range(24)]
        desk = SimpleNamespace(
            settings={"clipboard_image_limit": 30},
            clipboard_images=images,
            _clipboard_selected_image_id="23",
            schedule_save=lambda: saved.append(True),
            current_tab="settings",
        )
        app["PocketDesk"]._set_clipboard_image_limit(desk, 10)
        self.assertEqual(desk.settings["clipboard_image_limit"], 10)
        self.assertEqual(len(images), 10)
        self.assertEqual([item["id"] for item in images],
                         [str(i) for i in range(10)])
        self.assertEqual(desk._clipboard_selected_image_id, "0")
        self.assertEqual(saved, [True])
        app["PocketDesk"]._set_clipboard_image_limit(desk, 10)
        self.assertEqual(saved, [True])

    def test_image_limit_persists_without_saving_image_history(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            data = app["default_data"]()
            data["settings"]["clipboard_image_limit"] = 25
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["settings"]["clipboard_image_limit"], 25)
            self.assertNotIn("clipboard_images", path.read_text(encoding="utf-8"))

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
