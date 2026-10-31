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
        self.assertEqual(layout.view_dimensions("compact"), (820, 680))
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
        self.assertIn("compact.build_home(self)", source)
        self.assertIn('self.display_mode in ("dashboard", "compact")', source)
        for method in ("_build_notes", "_build_links", "_build_ports",
                       "_build_mac", "_build_commands", "_build_subnet",
                       "_build_clipboard", "_build_settings"):
            self.assertIn("self." + method + "()", source)


if __name__ == "__main__":
    unittest.main()
