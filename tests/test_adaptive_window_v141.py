"""Pocket v1.41 adaptive geometry; runs headlessly and needs no network."""
from pathlib import Path
import runpy
import tempfile
import unittest

from pocket import adaptive_window as aw

APP_PATH = Path(__file__).resolve().parents[1] / "app.pyw"
app = runpy.run_path(str(APP_PATH), run_name="test_import")


class AdaptiveWindowTests(unittest.TestCase):
    def test_size_validation_and_legacy_data(self):
        self.assertIsNone(aw.saved_size(None))
        for bad in ({}, [], {"width": True, "height": 600},
                    {"width": 500.0, "height": 600},
                    {"width": 0, "height": 500},
                    {"width": 50000, "height": 500}):
            self.assertIsNone(aw.saved_size(bad))
        self.assertEqual(aw.saved_size({"width": 595, "height": 710}),
                         {"width": 595, "height": 710})
        self.assertIsNone(app["default_data"]()["window_size"])

    def test_breakpoints_do_not_turn_extra_mini_on(self):
        self.assertEqual(aw.layout_for(346, 530), "mini")
        self.assertEqual(aw.layout_for(480, 850), "normal")
        self.assertEqual(aw.layout_for(1160, 800), "dashboard")
        self.assertEqual(aw.layout_for(1050, 480), "normal")
        self.assertEqual(aw.layout_for(949, 800), "normal")

    def test_resize_edges_and_corners_on_negative_monitor(self):
        screen = (-1600, 0, 0, 1000)
        original = (-1400, 100, 480, 600)
        self.assertEqual(aw.resize_rectangle(original, "e", 70, 0, screen),
                         (-1400, 100, 550, 600))
        self.assertEqual(aw.resize_rectangle(original, "nw", -60, -30, screen),
                         (-1460, 70, 540, 630))
        self.assertEqual(aw.resize_rectangle(original, "se", 50, 50, screen),
                         (-1400, 100, 530, 650))
        # Can never drag a right-hand corner past the current monitor.
        self.assertEqual(aw.resize_rectangle(original, "e", 5000, 0, screen)[2], 1393)
        # Keep the original right edge fixed when narrowing from the left.
        x, y, width, height = aw.resize_rectangle(original, "w", 500, 0, screen)
        self.assertEqual(x + width, original[0] + original[2])
        self.assertEqual(width, aw.MIN_WIDTH)

    def test_monitor_limits_and_minimum_height(self):
        screen = (0, 0, 800, 600)
        x, y, width, height = aw.resize_rectangle((100, 50, 470, 500), "se", -1000, -1000, screen)
        self.assertEqual((x, y, width, height), (100, 50, 330, 440))
        self.assertEqual(aw.resize_rectangle((100, 50, 470, 500), "se", 5000, 5000, screen),
                         (100, 50, 693, 543))

    def test_profile_roundtrip_preserves_normal_mini_dashboard_and_launcher(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            data = app["default_data"]()
            data["window_size"] = {"width": 1020, "height": 750}
            data["settings"]["display_mode"] = "dashboard"
            data["settings"]["extra_mini_enabled"] = True
            data["window_positions"]["compact"] = {"x": 10, "y": 20}
            app["save_data"](path, data)
            loaded = app["load_data"](path)
            self.assertEqual(loaded["window_size"], {"width": 1020, "height": 750})
            self.assertEqual(loaded["settings"]["display_mode"], "dashboard")
            self.assertTrue(loaded["settings"]["extra_mini_enabled"])
            self.assertEqual(loaded["window_positions"]["compact"], {"x": 10, "y": 20})


if __name__ == "__main__":
    unittest.main()
