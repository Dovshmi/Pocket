"""Headless structural regressions for the modern Settings interface."""
from pathlib import Path
import runpy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pocket import icon_themes as themes
from pocket import settings_ui
from pocket import compact_dashboard as compact

app = runpy.run_path(str((Path(__file__).resolve().parents[1] / "app.pyw")), run_name="test_import")


class ModernSettingsTests(unittest.TestCase):
    def test_translate_picker_wheel_scrolls_settings_not_selection(self):
        app_stub = SimpleNamespace(
            settings={"convert_mode": "mark"},
            _set_convert_mode=Mock(),
            _scroll_tool_on_wheel=Mock(),
        )
        with patch.object(settings_ui.tk, "Frame") as frame, \
             patch.object(settings_ui, "_label") as label, \
             patch.object(settings_ui.ttk, "Combobox") as combobox, \
             patch.object(settings_ui, "_register") as register:
            frame.return_value.pack = Mock()
            label.return_value.pack = Mock()
            select = combobox.return_value
            settings_ui._convert_mode_picker(
                Mock(), app_stub, {"PANEL": "#111111"}, compact=True)
            callbacks = {call.args[0]: call.args[1]
                         for call in select.bind.call_args_list}
            self.assertIn("<<ComboboxSelected>>", callbacks)
            self.assertEqual(
                {key for key in callbacks if key != "<<ComboboxSelected>>"},
                {"<MouseWheel>", "<Button-4>", "<Button-5>"})
            for key in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                event = SimpleNamespace(delta=120, num=4, widget=select)
                self.assertEqual(callbacks[key](event), "break")
                app_stub._scroll_tool_on_wheel.assert_called_with(
                    event, from_picker=True)
            app_stub._set_convert_mode.assert_not_called()
            register.assert_called_once_with(app_stub, "convert_mode_picker", select)


    def test_quick_slots_picker_changes_only_modifiers_and_ignores_wheel(self):
        from pocket import quick_slots
        app_stub = SimpleNamespace(
            settings={"quick_slots_paste_prefix": "ctrl_alt",
                      "quick_slots_copy_prefix": "ctrl_win"},
            _set_quick_slots_copy_prefix=Mock(), _scroll_tool_on_wheel=Mock())
        with patch.object(settings_ui.tk, "Frame") as frame, \
             patch.object(settings_ui, "_label") as label, \
             patch.object(settings_ui.ttk, "Combobox") as combobox, \
             patch.object(settings_ui, "_register") as register:
            frame.return_value.pack = Mock()
            label.return_value.pack = Mock()
            select = combobox.return_value
            settings_ui._dropdown_field(
                Mock(), app_stub, {"PANEL": "#111111"},
                "quick_slots_copy_prefix_picker", "Copy shortcut prefix", "",
                quick_slots.PREFIX_CHOICES,
                app_stub.settings["quick_slots_copy_prefix"],
                app_stub._set_quick_slots_copy_prefix,
                compact=True, wheel_scroll_page=True)
            callbacks = {call.args[0]: call.args[1]
                         for call in select.bind.call_args_list}
            self.assertEqual(len(quick_slots.PREFIX_CHOICES), 4)
            self.assertTrue(all("Num" not in text for text, _ in
                                quick_slots.PREFIX_CHOICES))
            for event_name in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.assertEqual(callbacks[event_name](Mock()), "break")
            app_stub._set_quick_slots_copy_prefix.assert_not_called()
            app_stub._scroll_tool_on_wheel.assert_called()

    def test_two_shortcuts_migrate_normalize_and_persist(self):
        from tempfile import TemporaryDirectory
        factory = app["default_data"]()["settings"]
        self.assertTrue(factory["quick_slots_enabled"])
        self.assertEqual(factory["quick_slots_paste_prefix"], "ctrl_alt")
        self.assertEqual(factory["quick_slots_copy_prefix"], "ctrl_alt_win")
        migrated = app["normalize_settings"](
            {"quick_slots_enabled": False, "quick_slots_prefix": "ctrl"})
        self.assertFalse(migrated["quick_slots_enabled"])
        self.assertEqual(migrated["quick_slots_paste_prefix"], "ctrl")
        self.assertEqual(migrated["quick_slots_copy_prefix"], "ctrl_alt_win")
        legacy_win = app["normalize_settings"]({"quick_slots_prefix": "ctrl_win"})
        self.assertEqual(legacy_win["quick_slots_paste_prefix"], "ctrl_win")
        self.assertEqual(legacy_win["quick_slots_copy_prefix"], "ctrl_alt_win")
        self.assertEqual(app["normalize_settings"](
            {"quick_slots_copy_prefix": {"bad": True}})["quick_slots_copy_prefix"],
            "ctrl_alt_win")
        with TemporaryDirectory() as folder:
            file = Path(folder) / "data.json"
            data = app["default_data"]()
            data["settings"].update(
                quick_slots_enabled=False,
                quick_slots_paste_prefix="ctrl",
                quick_slots_copy_prefix="ctrl_alt_win")
            app["save_data"](file, data)
            result = app["load_data"](file)
            self.assertFalse(result["settings"]["quick_slots_enabled"])
            self.assertEqual(result["settings"]["quick_slots_paste_prefix"], "ctrl")
            self.assertEqual(result["settings"]["quick_slots_copy_prefix"],
                             "ctrl_alt_win")
            self.assertEqual(result["clipboard_slots"], {})

    def test_one_quick_slot_notification_setting_is_defaulted_and_persisted(self):
        from tempfile import TemporaryDirectory
        from pocket import quick_slots
        self.assertEqual(app["default_data"]()["settings"][
            "quick_slots_notification_mode"], "all")
        self.assertEqual(app["normalize_settings"]({})[
            "quick_slots_notification_mode"], "all")
        self.assertEqual(app["normalize_settings"]({
            "quick_slots_notification_mode": "invalid"})[
            "quick_slots_notification_mode"], "all")
        self.assertEqual([v for _, v in quick_slots.NOTIFICATION_CHOICES],
                         ["all", "copy", "paste", "off"])
        with TemporaryDirectory() as directory:
            location = Path(directory) / "data.json"
            data = app["default_data"]()
            data["settings"]["quick_slots_notification_mode"] = "paste"
            app["save_data"](location, data)
            self.assertEqual(app["load_data"](location)["settings"][
                "quick_slots_notification_mode"], "paste")
        self.assertIn('"quick_slots_notification_mode_picker"',
                      Path(settings_ui.__file__).read_text(encoding="utf-8"))

    def test_quick_slot_notification_filter_does_not_affect_other_notices(self):
        from pocket import quick_slots
        desk = SimpleNamespace(
            settings={"quick_slots_notification_mode": "paste"},
            schedule_save=Mock(), _notify=Mock())
        target = app["PocketDesk"]
        target._notify_quick_slot(desk, "copy", "COPY [3]", "old")
        desk._notify.assert_not_called()
        target._notify_quick_slot(desk, "paste", "PASTE [3]", "value")
        desk._notify.assert_called_once_with("PASTE [3]", "value")
        target._set_quick_slots_notification_mode(desk, "off")
        desk.schedule_save.assert_called_once()
        self.assertEqual(desk.settings["quick_slots_notification_mode"], "off")
        target._notify_quick_slot(desk, "paste", "PASTE [3]", "value")
        desk._notify.assert_called_once()
        target._set_quick_slots_notification_mode(desk, "off")
        desk.schedule_save.assert_called_once()
        self.assertTrue(quick_slots.notification_enabled("all", "copy"))

    def test_quick_slot_record_buttons_hidden_but_dropdowns_kept(self):
        source = Path(settings_ui.__file__).read_text(encoding="utf-8")
        self.assertNotIn('"record_quick_slots_paste"', source)
        self.assertNotIn('"record_quick_slots_copy"', source)
        self.assertIn('"quick_slots_paste_prefix_picker"', source)
        self.assertIn('"quick_slots_copy_prefix_picker"', source)

    def test_existing_explicit_ctrl_win_preference_is_preserved(self):
        settings = app["normalize_settings"]({
            "quick_slots_paste_prefix": "ctrl_alt",
            "quick_slots_copy_prefix": "ctrl_win",
        })
        self.assertEqual(settings["quick_slots_copy_prefix"], "ctrl_win")

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
                         (10, 15, 20, 25, 30))
        self.assertEqual(app["default_data"]()["settings"]["clipboard_image_limit"], 20)
        for count in clipboard_images.IMAGE_LIMIT_CHOICES:
            self.assertEqual(app["normalize_settings"](
                {"clipboard_image_limit": count})["clipboard_image_limit"], count)
        self.assertEqual(app["normalize_settings"]({"clipboard_image_limit": 15})["clipboard_image_limit"], 15)
        self.assertEqual(app["normalize_settings"]({"clipboard_image_limit": 25})["clipboard_image_limit"], 25)
        self.assertEqual(app["normalize_settings"]({"clipboard_image_limit": 40})["clipboard_image_limit"], 30)
        self.assertEqual(app["normalize_settings"]({"clipboard_image_limit": 100})["clipboard_image_limit"], 30)
        for value in (-1, 0, 35, 105, 200, True, "30", 12.5, None):
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
            data["settings"]["clipboard_image_limit"] = 30
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["settings"]["clipboard_image_limit"], 30)
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
