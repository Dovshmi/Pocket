"""Compact dashboard regression checks (safe on headless CI)."""
from pathlib import Path
import runpy
import tempfile
import unittest

import mini_layout as layout
import compact_dashboard as compact

app = runpy.run_path(str(Path(__file__).with_name("app.pyw")), run_name="test_import")


class CompactDashboardTests(unittest.TestCase):
    def test_sizes_and_default_mode(self):
        self.assertEqual(layout.view_dimensions("compact"), (322, 256))
        self.assertLess(layout.view_dimensions("compact")[0], layout.view_dimensions("mini")[0])
        self.assertLess(layout.view_dimensions("compact")[1], layout.view_dimensions("mini")[1])
        self.assertEqual(layout.view_dimensions("normal"), (480, 850))
        self.assertEqual(layout.view_dimensions("mini"), (346, 530))
        self.assertEqual(layout.view_dimensions("dashboard"), (1160, 800))
        self.assertEqual(app["default_data"]()["settings"]["display_mode"], "normal")
        self.assertEqual(app["normalize_settings"]({"display_mode": "compact"})["display_mode"],
                         "compact")

    def test_every_real_tool_has_a_visible_navigation_entry(self):
        keys = [key for key, _icon, _label in compact.NAVIGATION]
        self.assertEqual(len(keys), len(set(keys)))
        actual = {key for key, _label in app["VISIBLE_TABS"]}
        self.assertEqual(set(keys), actual | {"home", "settings"})
        self.assertEqual(set(compact.TOOL_DESCRIPTIONS), actual)
        self.assertEqual(set(compact.PAGES), set(keys))

    def test_menu_visibility_is_honored_without_hiding_settings(self):
        keys = [key for key, _icon, _title
                in compact.visible_navigation(["notes", "subnet"])]
        self.assertEqual(keys, ["home", "notes", "subnet", "settings"])
        keys = [key for key, _icon, _title
                in compact.visible_navigation([k for k, _ in app["VISIBLE_TABS"]])]
        self.assertEqual(keys[0], "home")
        self.assertEqual(keys[-1], "settings")
        self.assertEqual(len(keys), len(compact.NAVIGATION))

    def test_featured_cards_and_fallback_respect_visibility(self):
        self.assertEqual(compact.featured_tools(
            ["notes", "links", "ports", "mac", "commands", "subnet", "clipboard"]),
            ("commands", "notes", "clipboard", "subnet"))
        self.assertEqual(compact.featured_tools(["links", "ports", "mac"]),
                         ("links", "ports", "mac"))
        self.assertEqual(compact.featured_tools([]), ())

    def test_search_finds_real_local_items_without_executing(self):
        data = {"notes": [{"id": "note-1", "title": "Router checklist",
                            "body": "Check OSPF adjacency"}],
                "links": [{"id": "link-1", "title": "Device docs",
                            "url": "https://example.test/docs"}]}
        library = [{"id": "cmd-1", "machine": "Cisco", "category": "Routing",
                    "description": "Show OSPF neighbors",
                    "command": "show ip ospf neighbor"}]
        visible = [key for key, _caption in app["VISIBLE_TABS"]]
        note_hits = compact.search_items(data, library, "checklist", visible)
        self.assertEqual(note_hits[0]["kind"], "note")
        self.assertEqual(note_hits[0]["id"], "note-1")
        self.assertEqual(note_hits[0]["destination"], "notes")
        shortcut_hits = compact.search_items(data, library, "Device docs", visible)
        self.assertEqual(shortcut_hits[0]["destination"], "links")
        command_hits = compact.search_items(data, library, "ospf", visible)
        self.assertTrue(any(hit["kind"] == "command" for hit in command_hits))
        self.assertEqual(compact.search_items(data, library, "ospf", ["links"]), [])
        self.assertEqual(compact.search_items(data, library, "", visible), [])

    def test_launcher_dispatches_through_existing_mini_without_saving_mode(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        desk = SimpleNamespace(
            display_mode="compact", current_tab="home", _compact_return=False,
            settings={"visible_tabs": ["notes", "commands"], "display_mode": "compact"},
            data={"notes": [{"id": "n1"}], "active_note": "other"},
            _build_shell_refresh=Mock(), _command_focus_in=Mock(),
        )
        app["PocketDesk"]._open_compact_tool(
            desk, "notes", {"kind": "note", "destination": "notes", "id": "n1"})
        self.assertEqual(desk.display_mode, "mini")
        self.assertTrue(desk._compact_return)
        self.assertEqual(desk.current_tab, "notes")
        self.assertEqual(desk.data["active_note"], "n1")
        self.assertEqual(desk.settings["display_mode"], "compact")
        desk._flush_current_note = Mock()
        app["PocketDesk"]._return_to_compact(desk)
        self.assertEqual(desk.display_mode, "compact")
        self.assertEqual(desk.current_tab, "home")
        self.assertFalse(desk._compact_return)
        self.assertEqual(desk.settings["display_mode"], "compact")
        self.assertEqual(desk._build_shell_refresh.call_count, 2)

    def test_independent_saved_position_and_settings_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            data = app["default_data"]()
            data["settings"]["display_mode"] = "compact"
            data["window_positions"]["compact"] = {"x": 110, "y": 140}
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["settings"]["display_mode"], "compact")
            self.assertEqual(loaded["window_positions"]["compact"], {"x": 110, "y": 140})
            for mode in ("normal", "mini", "dashboard"):
                self.assertIsNone(loaded["window_positions"][mode])
            self.assertEqual(loaded["notes"], data["notes"])
            self.assertEqual(loaded["links"], data["links"])
            self.assertNotIn("clipboard_items", loaded)

    def test_legacy_positions_migrate_without_overwriting(self):
        positions = layout.window_positions(
            {"normal": {"x": 1, "y": 2}, "mini": {"x": 3, "y": 4},
             "dashboard": {"x": 5, "y": 6}})
        self.assertEqual(positions["normal"], {"x": 1, "y": 2})
        self.assertIsNone(positions["compact"])
        self.assertEqual(positions["dashboard"], {"x": 5, "y": 6})

    def test_app_dispatch_reuses_every_existing_tool_builder(self):
        source = Path(__file__).with_name("app.pyw").read_text(encoding="utf-8")
        self.assertIn("return compact.build_shell(self,", source)
        self.assertIn("compact.style_nav(self, which)", source)
        self.assertIn("self._open_compact_tool(which)", source)
        self.assertIn("self._return_to_compact()", source)
        self.assertIn("self._compact_return = True", source)
        self.assertIn('self.display_mode = "mini"', source)
        self.assertIn("compact.build_home(self)", source)
        self.assertIn('self.display_mode in ("dashboard", "compact")', source)
        for method in ("_build_notes", "_build_links", "_build_ports",
                       "_build_mac", "_build_commands", "_build_subnet",
                       "_build_clipboard", "_build_settings"):
            self.assertIn("self." + method + "()", source)


if __name__ == "__main__":
    unittest.main()
