"""Pocket Cat experiment: deterministic motion, original pixels, and safe settings.

The motion/sprite checks intentionally run without a Windows UI or network.
"""
from __future__ import annotations

import runpy
from pathlib import Path
import unittest

from pocket.cat_companion import CatMotion, SIZE, POSES, sprite_pixels
from pocket.mini_layout import view_dimensions

ROOT = Path(__file__).resolve().parents[1]


class CatMotionTests(unittest.TestCase):
    def test_original_pixel_art_is_visible_and_transparent(self):
        for pose in POSES:
            for face in (-1, 1):
                for frame in (0, 1):
                    pixels = sprite_pixels(pose, face, frame)
                    self.assertEqual(len(pixels), 24)
                    self.assertTrue(all(len(line) == 24 for line in pixels))
                    flat = [p for line in pixels for p in line]
                    self.assertIn("", flat, "The sprite requires a clear background")
                    self.assertIn("#07090d", flat, "The cat must have black fur")
                    self.assertGreater(len([p for p in flat if p]), 40)
        self.assertNotEqual(sprite_pixels("walk", 1, 0),
                            sprite_pixels("walk", 1, 1),
                            "Walking must use two visibly different frames")
        self.assertNotEqual(sprite_pixels("walk", -1, 0),
                            sprite_pixels("walk", 1, 0),
                            "A cat must actually face its movement direction")
        self.assertNotEqual(sprite_pixels("sleep"), sprite_pixels("sit"))

    def test_invalid_pose_rejected(self):
        with self.assertRaises(ValueError):
            sprite_pixels("not-a-real-pose")

    def test_roaming_is_within_every_real_layout(self):
        cat = CatMotion(seed=42)
        poses = set()
        destinations = set()
        for mode in ("normal", "mini", "dashboard", "compact"):
            width, height = view_dimensions(mode)
            for tick in range(260):
                # Occasionally offer the local pointer, also test out-of-range
                # coordinates and waking behavior without any OS/global hook.
                pointer = ((tick * 7) % width, (tick * 11) % height) if tick % 17 == 0 else None
                x, y, pose, face, frame = cat.step(width, height, pointer)
                left, right, top, bottom = cat.limits(width, height)
                self.assertGreaterEqual(x, left)
                self.assertLessEqual(x, right + 1)
                self.assertGreaterEqual(y, top)
                self.assertLessEqual(y, bottom + 1)
                self.assertIn(pose, POSES)
                self.assertIn(face, (-1, 1))
                self.assertIn(frame, (0, 1))
                poses.add(pose)
                destinations.add((x // 8, y // 8))
        self.assertIn("walk", poses)
        self.assertIn("sit", poses)
        self.assertTrue(len(destinations) > 15, "Cat should explore rather than stay static")
        self.assertLessEqual(SIZE, view_dimensions("compact")[0])

    def test_motion_is_repeatable_for_a_test_seed(self):
        a, b = CatMotion(seed=93), CatMotion(seed=93)
        for _ in range(600):
            self.assertEqual(a.step(322, 256), b.step(322, 256))

    def test_settings_default_on_but_allow_user_to_disable(self):
        app = runpy.run_path(str(ROOT / "app.pyw"), run_name="pocket_cat_tests")
        normalize = app["normalize_settings"]
        self.assertTrue(app["default_data"]()["settings"]["pocket_cat"])
        self.assertTrue(normalize({})["pocket_cat"])
        self.assertFalse(normalize({"pocket_cat": False})["pocket_cat"])
        self.assertTrue(normalize({"pocket_cat": True})["pocket_cat"])
        self.assertTrue(normalize({"pocket_cat": "false"})["pocket_cat"],
                        "Untrusted string values should not disable the feature")

    def test_no_network_or_clipboard_access_in_cat_module(self):
        source = (ROOT / "pocket" / "cat_companion.py").read_text(encoding="utf-8")
        for forbidden in ("urllib", "requests", "socket.", "clipboard_get",
                          "clipboard_clear", "keyboard", "pynput", "subprocess"):
            self.assertNotIn(forbidden, source)
        app = (ROOT / "app.pyw").read_text(encoding="utf-8")
        self.assertIn('self.cat.tick(blocked=self._modal)', app)
        self.assertIn('self.cat.hide()', app)
        self.assertIn('cat.destroy()', app)


if __name__ == "__main__":
    unittest.main()
