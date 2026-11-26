import unittest
from pocket import palette_preferences as prefs, command_palette as palette


class PalettePreferencesTests(unittest.TestCase):
    def test_defaults_and_bounds(self):
        self.assertEqual(prefs.normalize(None), {
            "palette_opacity": 95, "palette_remember_position": True,
            "palette_position": None})
        self.assertEqual(prefs.opacity(0), 60)
        self.assertEqual(prefs.opacity(200), 100)
        self.assertEqual(prefs.opacity(True), 95)

    def test_restore_negative_monitor_and_disable(self):
        raw = {"palette_position": {"x": -1550, "y": 100}, "palette_opacity": 80}
        self.assertEqual(prefs.normalize(raw)["palette_position"], raw["palette_position"])
        self.assertIsNone(prefs.normalize(dict(raw, palette_remember_position=False))["palette_position"])
        self.assertIsNone(prefs.position({"x": "1", "y": 2}))
        self.assertEqual(prefs.clamp(-1550, 100, 550, 420, (-1920, 0, 0, 1040)), (-1550, 100))
        self.assertEqual(prefs.clamp(-1550, 100, 550, 420, (0, 0, 1920, 1040)), (5, 100))

    def test_adaptive_size(self):
        area = (0, 0, 1920, 1080)
        self.assertLess(prefs.dimensions(area, 1)[1], prefs.dimensions(area, 6)[1])
        self.assertEqual(prefs.dimensions(area, 6), prefs.dimensions(area, 99))

    def test_tool_icons(self):
        for key in ("extra", "ports", "mac", "notes", "subnet", "commands", "clipboard", "settings"):
            hit = {"kind": "tool", "destination": key}
            self.assertEqual(palette.search_icon("> open " + key, hit), key)
        self.assertEqual(palette.search_icon("", {"destination": "notes"}), "search")
        self.assertEqual(palette.search_icon(">"), "commands")
        self.assertEqual(palette.result_icon({"kind": "completion", "id": "> extra ", "destination": None}), "extra")


if __name__ == "__main__":
    unittest.main()
