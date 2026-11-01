"""Theme settings, icon generation and source integration regression checks."""
import tempfile
import unittest
from pathlib import Path
import runpy

from pocket import icon_themes as t


class ThemeTests(unittest.TestCase):
    def test_six_supported_themes(self):
        self.assertEqual(t.THEME_ORDER, ("blue", "dark_blue", "black", "red", "green", "purple"))
        for name in t.THEME_ORDER:
            self.assertIn(name, t.THEMES)
            self.assertTrue(t.palette(name)["ACCENT"].startswith("#"))
            self.assertNotEqual(t.palette(name)["BG"], t.palette(name)["PANEL"])

    def test_unknown_or_legacy_values_use_blue(self):
        for name in (None, "", "unknown", 5, [], {}):
            self.assertEqual(t.valid_theme(name), "blue")

    def test_existing_data_persists_selected_theme(self):
        app = runpy.run_path(str((Path(__file__).resolve().parents[1] / "app.pyw")), run_name="theme_test")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "data.json"
            data = app["default_data"]()
            self.assertEqual(data["theme"], "blue")
            data["theme"] = "purple"
            app["save_data"](target, data)
            self.assertEqual(app["load_data"](target)["theme"], "purple")
            data.pop("theme")
            app["save_data"](target, data)
            self.assertEqual(app["load_data"](target)["theme"], "blue")

    def test_generate_png_and_windows_ico(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            icons = t.ensure_icons(Path(folder))
            self.assertEqual(set(icons), set(t.THEME_ORDER))
            for name, files in icons.items():
                self.assertTrue(files["png"].is_file(), name)
                self.assertTrue(files["ico"].is_file(), name)
                with Image.open(files["png"]) as image:
                    self.assertEqual(image.size, (512, 512))
                with Image.open(files["ico"]) as image:
                    self.assertIn((16,16), image.ico.sizes())
                    self.assertIn((256,256), image.ico.sizes())


if __name__ == "__main__":
    unittest.main()
