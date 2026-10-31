"""Regression tests for Pocket's optional wide desktop dashboard.

Pure unit tests require no windowing system and must not touch user data.
"""
from pathlib import Path
import runpy
import tempfile
import unittest

import mini_layout as layout
import dashboard_ui as dashboard

app = runpy.run_path(str(Path(__file__).with_name("app.pyw")), run_name="test_import")


class DashboardLayoutTests(unittest.TestCase):
    def test_dashboard_is_opt_in_and_existing_sizes_do_not_change(self):
        self.assertEqual(layout.view_dimensions("normal"), (480, 850))
        self.assertEqual(layout.view_dimensions("mini"), (346, 530))
        self.assertEqual(layout.view_dimensions("dashboard"), (1160, 800))
        self.assertEqual(layout.display_mode("unsupported"), "normal")
        self.assertEqual(app["default_data"]()["settings"]["display_mode"], "normal")

    def test_dashboard_position_is_independent(self):
        data = layout.window_positions(
            {"normal": {"x": 25, "y": 50},
             "mini": {"x": 75, "y": 100},
             "dashboard": {"x": 125, "y": 150}})
        self.assertEqual(data["normal"], {"x": 25, "y": 50})
        self.assertEqual(data["mini"], {"x": 75, "y": 100})
        self.assertEqual(data["dashboard"], {"x": 125, "y": 150})
        self.assertIsNone(layout.window_positions(None)["dashboard"])

    def test_dashboard_preferences_round_trip_without_changing_saved_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data.json"
            data = app["default_data"]()
            data["settings"]["display_mode"] = "dashboard"
            data["window_positions"]["dashboard"] = {"x": 11, "y": 22}
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["settings"]["display_mode"], "dashboard")
            self.assertEqual(loaded["window_positions"]["dashboard"], {"x": 11, "y": 22})
            self.assertEqual(loaded["notes"], data["notes"])
            self.assertEqual(loaded["links"], data["links"])

    def test_sidebar_navigation_is_real_tools_only(self):
        keys = [entry[0] for entry in dashboard.NAVIGATION]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("home", keys)
        self.assertIn("settings", keys)
        self.assertTrue(set(keys) - {"home", "settings"} <=
                        {key for key, _name in app["VISIBLE_TABS"]})
        self.assertIn("commands", dashboard.TITLES)

    def test_dashboard_dispatch_preserves_original_page_builders(self):
        source = Path(__file__).with_name("app.pyw").read_text(encoding="utf-8")
        self.assertIn("dashboard.build_shell(self,", source)
        self.assertIn("dashboard.style_nav(self, which)", source)
        self.assertIn("dashboard.build_home(self)", source)
        self.assertIn("self._build_commands()", source)
        self.assertIn("self._build_notes()", source)
        self.assertIn("self._build_subnet()", source)
        self.assertIn('("normal", "Normal"), ("mini", "Mini"), ("compact", "Compact"), ("dashboard", "Dashboard")',
                      source)


if __name__ == "__main__":
    unittest.main()
