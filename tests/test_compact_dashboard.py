"""Tests for optional Extra Mini launcher, independent of a Tk display."""
from pathlib import Path
import runpy
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from pocket import mini_layout as layout
from pocket import compact_dashboard as compact

app = runpy.run_path(str((Path(__file__).resolve().parents[1] / "app.pyw")), run_name="test_import")
Desk = app["PocketDesk"]


class ExtraMiniTests(unittest.TestCase):
    def test_geometry_and_saved_base_mode(self):
        self.assertEqual(layout.view_dimensions("compact"), (322, 256))
        self.assertLess(322, layout.view_dimensions("mini")[0])
        self.assertLess(256, layout.view_dimensions("mini")[1])
        self.assertEqual(layout.view_dimensions("normal"), (480, 850))
        self.assertEqual(layout.view_dimensions("mini"), (346, 530))
        self.assertEqual(layout.view_dimensions("dashboard"), (1160, 800))
        self.assertFalse(app["default_data"]()["settings"]["extra_mini_enabled"])
        self.assertEqual(app["default_data"]()["settings"]["display_mode"], "normal")

    def test_legacy_compact_migrates_to_mini_with_toggle(self):
        old = app["normalize_settings"]({"display_mode": "compact"})
        self.assertEqual(old["display_mode"], "mini")
        self.assertTrue(old["extra_mini_enabled"])
        fresh = app["normalize_settings"]({"display_mode": "dashboard",
                                            "extra_mini_enabled": True})
        self.assertEqual(fresh["display_mode"], "dashboard")
        self.assertTrue(fresh["extra_mini_enabled"])

    def test_navigation_uses_every_real_menu(self):
        keys = [key for key, _icon, _label in compact.NAVIGATION]
        real = {key for key, _name in app["VISIBLE_TABS"]}
        self.assertEqual(set(keys), real | {"home", "settings"})
        self.assertEqual(set(compact.TOOL_DESCRIPTIONS), real)
        self.assertEqual(set(compact.PAGES), set(keys))
        subset = [key for key, _icon, _title in compact.visible_navigation(["notes","subnet"])]
        self.assertEqual(subset, ["home", "notes", "subnet", "settings"])

    def test_four_fixed_slots_remove_and_add(self):
        full = [key for key, _name in app["VISIBLE_TABS"]]
        original = ["commands", "notes", "clipboard", "subnet"]
        self.assertEqual(compact.display_slots(full, original), tuple(original))
        removed = compact.remove_tile(original, 1)
        self.assertEqual(removed, ["commands", None, "clipboard", "subnet"])
        self.assertEqual(compact.display_slots(full, removed), tuple(removed))
        self.assertEqual(compact.featured_tools(full, removed),
                         ("commands", "clipboard", "subnet"))
        self.assertNotIn("notes", [key for key, _icon, _title in
                                 compact.available_tools(full, original)])
        choices = [key for key, _icon, _title in compact.available_tools(full, removed)]
        self.assertIn("notes", choices)
        self.assertIn("links", choices)
        added = compact.choose_tile(removed, 1, "links", full)
        self.assertEqual(added, ["commands", "links", "clipboard", "subnet"])
        self.assertEqual(compact.choose_tile(added, 1, "mac", ["notes"]), added)

    def test_duplicate_selection_swaps_and_empty_slots_remain_empty(self):
        full = [key for key, _name in app["VISIBLE_TABS"]]
        chosen = compact.choose_tile(
            ["commands", "notes", "clipboard", "subnet"], 1, "commands", full)
        self.assertEqual(chosen, ["notes", "commands", "clipboard", "subnet"])
        self.assertEqual(len(set(chosen)), 4)
        empty = compact.remove_tile(["commands", None, "clipboard", "subnet"], 2)
        self.assertEqual(empty, ["commands", None, None, "subnet"])
        self.assertEqual(compact.configured_tiles(empty), empty)
        self.assertEqual(compact.display_slots(["commands"], empty),
                         ("commands", None, None, None))

    def test_hidden_tools_are_placeholders_without_losing_preferences(self):
        chosen = ["commands", "notes", "clipboard", "subnet"]
        self.assertEqual(compact.display_slots(["notes", "ports"], chosen),
                         (None, "notes", None, None))
        self.assertEqual(compact.featured_tools(["notes", "ports"], chosen),
                         ("notes",))
        self.assertEqual(compact.featured_tools([]), ())
        self.assertEqual(compact.display_slots(
            ["commands", "notes", "clipboard", "subnet"], chosen), tuple(chosen))

    def test_malformed_tile_preferences_are_sanitized(self):
        values = compact.configured_tiles(["bad", "notes", "notes", "links", 3])
        self.assertEqual(values, [None, "notes", None, "links"])
        self.assertEqual(compact.configured_tiles(None),
                         ["commands", "notes", "clipboard", "subnet"])
        self.assertEqual(compact.configured_tiles([]), [None] * 4)

    def test_local_search_returns_real_results(self):
        data = {"notes":[{"id":"n1","title":"Router checklist","body":"OSPF peer"}],
                "links":[{"id":"l1","title":"Lab docs","url":"https://example.test"}]}
        library = [{"id":"c1","machine":"Cisco","category":"Routing",
                    "description":"Show OSPF","command":"show ip ospf neighbor"}]
        visible = [key for key, _name in app["VISIBLE_TABS"]]
        self.assertEqual(compact.search_items(data, library, "checklist", visible)[0]["id"], "n1")
        self.assertEqual(compact.search_items(data, library, "Lab docs", visible)[0]["kind"], "shortcut")
        self.assertTrue(any(hit["kind"] == "command" for hit in
                            compact.search_items(data, library, "ospf", visible)))
        self.assertEqual(compact.search_items(data, library, "ospf", ["links"]), [])
        self.assertEqual(compact.search_items(data, library, "", visible), [])

    def make_desk(self, base):
        return SimpleNamespace(
            display_mode="compact", current_tab="home", _compact_return=False,
            _extra_mini_previous_tab="notes",
            settings={"visible_tabs": ["notes", "commands", "subnet"],
                      "display_mode": base, "extra_mini_enabled": True},
            data={"notes": [{"id":"n1"}], "active_note":"other"},
            _build_shell_refresh=Mock(), _command_focus_in=Mock(), schedule_save=Mock(),
            _flush_current_note=Mock())

    def test_tap_tile_restores_selected_mode_and_minimizes_again(self):
        for base in ("normal", "mini", "dashboard"):
            with self.subTest(base=base):
                desk = self.make_desk(base)
                Desk._open_compact_tool(desk, "notes",
                                         {"kind":"note","id":"n1","destination":"notes"})
                self.assertEqual(desk.display_mode, base)
                self.assertEqual(desk.settings["display_mode"], base)
                self.assertEqual(desk.current_tab, "notes")
                self.assertEqual(desk.data["active_note"], "n1")
                self.assertTrue(desk._compact_return)
                Desk._return_to_compact(desk)
                self.assertEqual(desk.display_mode, "compact")
                self.assertEqual(desk.current_tab, "home")
                self.assertEqual(desk.settings["display_mode"], base)
                self.assertEqual(desk._build_shell_refresh.call_count, 2)

    def test_expand_restores_previous_tool(self):
        desk = self.make_desk("dashboard")
        desk._extra_mini_previous_tab = "subnet"
        Desk._expand_from_extra_mini(desk)
        self.assertEqual(desk.display_mode, "dashboard")
        self.assertEqual(desk.current_tab, "subnet")
        self.assertEqual(desk.settings["display_mode"], "dashboard")

    def test_disable_option_returns_from_launcher(self):
        desk = self.make_desk("normal")
        desk._expand_from_extra_mini = Mock()
        Desk._set_extra_mini_enabled(desk, False)
        self.assertFalse(desk.settings["extra_mini_enabled"])
        desk._expand_from_extra_mini.assert_called_once()
        desk.schedule_save.assert_called_once()

    def test_saved_settings_and_position_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"data.json"
            data = app["default_data"]()
            data["settings"]["display_mode"] = "dashboard"
            data["settings"]["extra_mini_enabled"] = True
            data["settings"]["extra_mini_tiles"] = ["ports","links","notes","mac"]
            data["window_positions"]["compact"] = {"x":110,"y":140}
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["settings"], data["settings"])
            self.assertEqual(loaded["window_positions"]["compact"], {"x":110,"y":140})
            self.assertEqual(loaded["notes"], data["notes"])
            self.assertNotIn("clipboard_items", loaded)

    def test_real_feature_dispatch_kept(self):
        source = (Path(__file__).resolve().parents[1] / "app.pyw").read_text(encoding="utf-8")
        self.assertIn("settings_ui.build_settings(self, self.body)", source)
        self.assertIn("self._edit_extra_mini_from_settings", source)
        self.assertIn("self._return_to_compact", source)
        self.assertIn("compact.build_shell(self,", source)
        self.assertIn("self.settings[\"display_mode\"]", source)
        for tool in ("notes","links","ports","mac","commands","subnet","clipboard","settings"):
            self.assertIn(f"self._build_{tool}()", source)


if __name__ == "__main__":
    unittest.main()
