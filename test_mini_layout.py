"""Unit regression tests for Pocket Mini. No Tk display or Windows needed."""
from pathlib import Path
import runpy
import tempfile
import unittest

import mini_layout as mini

app = runpy.run_path(str(Path(__file__).with_name("app.pyw")), run_name="test_import")


class MiniLayoutTests(unittest.TestCase):
    def test_dimensions_are_smaller_than_normal(self):
        self.assertEqual(mini.view_dimensions("normal"), (480, 850))
        self.assertEqual(mini.view_dimensions("mini"), (346, 530))
        w, h = mini.view_dimensions("mini")
        self.assertLess(w, 480)
        self.assertLess(h, 850)

    def test_bad_mode_is_safe(self):
        for value in (None, 3, "MINI", [], {"x": 1}):
            self.assertEqual(mini.display_mode(value), "normal")

    def test_positions_migrate_legacy_and_stay_independent(self):
        legacy = {"x": 111, "y": 222}
        positions = mini.window_positions(None, legacy)
        self.assertEqual(positions["normal"], legacy)
        self.assertIsNone(positions["mini"])
        positions["mini"] = {"x": 600, "y": 100}
        self.assertEqual(positions["normal"], legacy)

    def test_corrupt_positions_never_reach_window_geometry(self):
        for bad in ({"x": "100", "y": 200}, {"x": 10.5, "y": 0},
                    {"x": True, "y": 2}, {"x": 100001, "y": 0}, []):
            self.assertIsNone(mini.window_position(bad))
        self.assertEqual(mini.window_positions({"normal": [], "mini": {"x": 2, "y": -6}}),
                         {"normal": None, "mini": {"x": 2, "y": -6}, "dashboard": None})

    def test_carousel_uses_ranked_first_result_and_limits(self):
        ranked = [{"id": "best"}, {"id": "next"}, {"id": "last"}]
        self.assertEqual(mini.selected_index(ranked), 0)
        self.assertEqual(mini.selected_index(ranked, "next"), 1)
        self.assertEqual(mini.selected_index(ranked, "missing"), 0)
        self.assertEqual(mini.carousel_index(0, 3, -1), 0)
        self.assertEqual(mini.carousel_index(0, 3, +1), 1)
        self.assertEqual(mini.carousel_index(2, 3, +1), 2)
        self.assertEqual(mini.carousel_index(0, 0, +1), -1)

    def test_mini_prefs_survive_storage_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "data.json"
            data = app["default_data"]()
            data["settings"]["display_mode"] = "mini"
            data["window_positions"]["mini"] = {"x": 42, "y": 89}
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["settings"]["display_mode"], "mini")
            self.assertEqual(loaded["window_positions"]["mini"], {"x": 42, "y": 89})
            self.assertEqual(loaded["window_positions"]["normal"], None)
            self.assertEqual(loaded["notes"], data["notes"])
            self.assertEqual(loaded["links"], data["links"])

    def test_old_settings_keep_normal_display_mode(self):
        self.assertEqual(app["normalize_settings"]({"visible_tabs": ["notes"]}),
                         {"visible_tabs": ["notes"], "display_mode": "normal"})
        self.assertEqual(app["normalize_settings"]({"visible_tabs": ["notes"],
                                                    "display_mode": "mini"})["display_mode"],
                         "mini")


if __name__ == "__main__":
    unittest.main()
