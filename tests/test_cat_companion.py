"""Pocket Cat experiment: deterministic motion, original pixels, and safe settings.

The motion/sprite checks intentionally run without a Windows UI or network.
"""
from __future__ import annotations

import runpy
from pathlib import Path
import unittest

from pocket.cat_companion import CatMotion, SIZE, POSES, sprite_pixels
from pocket.cat_navigation import SafeSpace, overlaps
from pocket.cat_sprites import PIXELS, FRAMES, INK, EYES
from pocket.mini_layout import view_dimensions

ROOT = Path(__file__).resolve().parents[1]


class CatMotionTests(unittest.TestCase):
    def test_original_pixel_art_is_visible_and_transparent(self):
        for pose in POSES:
            for face in (-1, 1):
                for frame in range(FRAMES):
                    pixels = sprite_pixels(pose, face, frame)
                    self.assertEqual(len(pixels), PIXELS)
                    self.assertTrue(all(len(line) == PIXELS for line in pixels))
                    flat = [p for line in pixels for p in line]
                    self.assertIn("", flat, "The sprite requires a clear background")
                    self.assertIn(INK, flat, "The cat must have black outlines")
                    self.assertGreater(len([p for p in flat if p]), 80)
        self.assertNotEqual(sprite_pixels("walk", 1, 0),
                            sprite_pixels("walk", 1, 1),
                            "Walking must use two visibly different frames")
        self.assertNotEqual(sprite_pixels("walk", -1, 0),
                            sprite_pixels("walk", 1, 0),
                            "A cat must actually face its movement direction")
        self.assertNotEqual(sprite_pixels("sleep"), sprite_pixels("sit"))
        self.assertIn(EYES, [pixel for row in sprite_pixels("sit") for pixel in row])
        self.assertNotEqual(sprite_pixels("play", frame=0), sprite_pixels("play", frame=1))
        self.assertEqual(FRAMES, 8)
        self.assertEqual(PIXELS, 36)
        self.assertGreaterEqual(len(set(sprite_pixels("walk", 1, f)
                                        for f in range(FRAMES))), 6,
                                "Smoother walking requires several distinct silhouettes")
        self.assertNotEqual(sprite_pixels("purr", frame=2), sprite_pixels("purr", frame=7))

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
                self.assertIn(frame, range(FRAMES))
                poses.add(pose)
                destinations.add((x // 8, y // 8))
        self.assertIn("walk", poses)
        self.assertIn("sit", poses)
        self.assertTrue(len(destinations) > 15, "Cat should explore rather than stay static")
        self.assertLessEqual(SIZE, view_dimensions("compact")[0])

    def test_safe_space_avoids_controls_and_guards_entire_body(self):
        obstacles = ((95, 0, 205, 210), (0, 90, 80, 115),
                     (212, 180, 300, 220))
        board = SafeSpace(320, 240, size=32, obstacles=obstacles, spacing=12)
        self.assertTrue(board.available)
        for point in board.points.values():
            for obstruction in obstacles:
                self.assertFalse(overlaps((point[0], point[1],
                                           point[0]+32, point[1]+32), obstruction))
        rng = __import__("random").Random(33)
        paths = [board.route(10, 10, rng) for _ in range(12)]
        self.assertTrue(any(paths))
        for path in paths:
            for x, y in path:
                self.assertTrue(board.clear(x, y))

    def test_cat_movement_never_enters_text_boxes_or_results(self):
        blockers = ((82, 45, 260, 180), (14, 188, 312, 218))
        board = SafeSpace(346, 256, size=32, obstacles=blockers, spacing=12)
        cat = CatMotion(seed=21)
        poses = set()
        coordinates = set()
        for i in range(900):
            x, y, pose, _, _ = cat.step(346, 256, (160, 90),
                                        safe_space=board)
            self.assertTrue(board.clear(x, y), (x, y, pose))
            poses.add(pose)
            coordinates.add((x, y))
        self.assertIn("walk", poses)
        self.assertGreater(len(coordinates), 12)
        self.assertIn("sleep", set(POSES))

    def test_cat_stays_quiet_during_input_focus(self):
        board = SafeSpace(480, 850, size=40, obstacles=((110, 110, 420, 810),))
        cat = CatMotion(seed=8)
        first = cat.step(480, 850, safe_space=board, busy=True)
        for _ in range(180):
            frame = cat.step(480, 850, safe_space=board, busy=True)
            self.assertEqual((frame[0], frame[1]), (first[0], first[1]))
            self.assertIn(frame[2], ("sit", "blink"))
            self.assertTrue(board.clear(frame[0], frame[1]))
        self.assertEqual(cat.route, [])
        # When typing stops, normal independent roaming may resume.
        resumed = set()
        for _ in range(220):
            resumed.add(cat.step(480, 850, safe_space=board)[2])
        self.assertIn("walk", resumed)

    def test_overcrowded_screen_reports_no_safe_place(self):
        board = SafeSpace(322, 256, size=32, obstacles=((0, 0, 322, 256),))
        self.assertFalse(board.available)
        self.assertEqual(board.route(0, 0, __import__("random").Random(1)), [])

    def test_hover_purrs_only_in_clear_space_and_stays_noninteractive(self):
        board = SafeSpace(320, 230, size=40,
                          obstacles=((120, 50, 310, 190),))
        cat = CatMotion(seed=14)
        initial = cat.step(320, 230, safe_space=board, busy=True)
        pointer = (initial[0] + 20, initial[1] + 20)
        self.assertTrue(board.clear(pointer[0] - 20, pointer[1] - 20))
        reactions = []
        for _ in range(15):
            point = cat.step(320, 230, pointer=pointer, safe_space=board)
            self.assertTrue(board.clear(point[0], point[1]))
            reactions.append(point[2])
        self.assertIn("purr", reactions)
        self.assertGreater(cat._purr_cooldown, 0)
        # A pointer on top of a protected field is not a navigation target.
        cat.step(320, 230, pointer=(180, 110), safe_space=board)
        self.assertIsNone(cat.last_pointer)
        self.assertEqual(cat._hover_ticks, 0)
        frozen = cat.step(320, 230, pointer=pointer, safe_space=board, busy=True)
        self.assertIn(frozen[2], ("sit", "blink"))
        self.assertEqual(cat.route, [])

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
        for forbidden in ("import urllib", "import requests", "socket.", "clipboard_get",
                          "clipboard_clear", "keyboard", "pynput", "subprocess"):
            self.assertNotIn(forbidden, source)
        app = (ROOT / "app.pyw").read_text(encoding="utf-8")
        self.assertIn('editing=native_typing)', app)
        self.assertIn('self.cat.tick(blocked=self._modal or self._dragging_window,', app)
        self.assertIn('self.cat.hide()', app)
        self.assertIn('cat.destroy()', app)


if __name__ == "__main__":
    unittest.main()
