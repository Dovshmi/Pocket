"""Regression tests for memory-only image history and adaptive Clipboard gallery."""
from __future__ import annotations
import sys
import unittest
from unittest.mock import patch
from PIL import Image
from pocket import clipboard_images, clipboard_gallery


class ClipboardImagesTests(unittest.TestCase):
    def test_twenty_first_picture_removes_oldest(self):
        history = []
        for number in range(21):
            self.assertTrue(clipboard_images.add_image(
                history, Image.new("RGB", (16, 12), (number, 60, 90))))
        self.assertEqual(len(history), 20)
        self.assertEqual(clipboard_images.decode_image(
            history[0]["data"]).getpixel((0, 0)), (20, 60, 90))
        self.assertEqual(clipboard_images.decode_image(
            history[-1]["data"]).getpixel((0, 0)), (1, 60, 90))

    def test_duplicate_does_not_consume_slot(self):
        history = []
        image = Image.new("RGBA", (30, 30), (10, 50, 200, 100))
        self.assertTrue(clipboard_images.add_image(history, image))
        self.assertFalse(clipboard_images.add_image(history, image.copy()))
        self.assertEqual(len(history), 1)
        self.assertEqual(clipboard_images.decode_image(
            history[0]["data"]).getpixel((0, 0)), (10, 50, 200, 100))

    def test_image_limit_independent_of_text(self):
        text = [{"text": "important note", "pinned": True}]
        pictures = []
        for index in range(23):
            clipboard_images.add_image(
                pictures, Image.new("RGB", (8, 8), (index, 2, 3)))
        self.assertEqual(len(pictures), 20)
        self.assertEqual(text, [{"text": "important note", "pinned": True}])

    def test_limits_reject_unreasonably_large_image(self):
        pictures = []
        self.assertFalse(clipboard_images.add_image(
            pictures, Image.new("RGB", (12, 12)), maximum_pixels=100))
        self.assertFalse(clipboard_images.add_image(
            pictures, Image.new("RGB", (12, 12)), maximum_bytes=2))
        self.assertEqual(pictures, [])

    def test_read_image_ignores_file_drop(self):
        with patch.object(clipboard_images, "image_available", return_value=True):
            with patch.object(clipboard_images.ImageGrab, "grabclipboard",
                              return_value=["C:/file.png"]):
                self.assertIsNone(clipboard_images.read_image())
            original = Image.new("RGB", (2, 2))
            with patch.object(clipboard_images.ImageGrab, "grabclipboard",
                              return_value=original):
                self.assertIs(clipboard_images.read_image(), original)

    def test_responsive_gallery_columns(self):
        self.assertEqual(clipboard_gallery.columns_for_width(180), 1)
        self.assertEqual(clipboard_gallery.columns_for_width(315), 1)
        self.assertEqual(clipboard_gallery.columns_for_width(490), 2)
        self.assertEqual(clipboard_gallery.columns_for_width(840), 4)
        self.assertEqual(clipboard_gallery.columns_for_width(2000), 5)

    @unittest.skipUnless(sys.platform == "win32", "requires Windows clipboard")
    def test_real_windows_bitmap_copy_round_trip(self):
        # Verify the native CF_DIB writer is actually pasteable.
        from PIL import ImageGrab
        history = []
        original = Image.new("RGB", (6, 4), (17, 121, 231))
        self.assertTrue(clipboard_images.add_image(history, original))
        clipboard_images.copy_image(history[0]["data"])
        pasted = ImageGrab.grabclipboard()
        self.assertIsInstance(pasted, Image.Image)
        self.assertEqual(pasted.size, (6, 4))
        self.assertEqual(pasted.convert("RGB").getpixel((2, 1)),
                         (17, 121, 231))

    def test_keyboard_moves_without_wrapping_or_leaving_images(self):
        from types import SimpleNamespace
        app = SimpleNamespace(
            current_tab="clipboard", clipboard_page="images",
            clipboard_images=[{"id": "a"}, {"id": "b"}, {"id": "c"}],
            _clipboard_selected_image_id="a")
        def select(app, ident):
            app._clipboard_selected_image_id = ident
        with patch.object(clipboard_gallery, "select_image", side_effect=select) as chosen:
            self.assertEqual(clipboard_gallery.move_selection(app, 1), "break")
            self.assertEqual(app._clipboard_selected_image_id, "b")
            clipboard_gallery.move_selection(app, 1)
            clipboard_gallery.move_selection(app, 1)
            self.assertEqual(app._clipboard_selected_image_id, "c")
            clipboard_gallery.move_selection(app, -1)
            self.assertEqual(app._clipboard_selected_image_id, "b")
            self.assertEqual(chosen.call_count, 4)
            app.clipboard_page = "text"
            self.assertIsNone(clipboard_gallery.move_selection(app, 1))
            self.assertEqual(app._clipboard_selected_image_id, "b")
            app.current_tab = "notes"
            app.clipboard_page = "images"
            self.assertIsNone(clipboard_gallery.move_selection(app, 1))
            self.assertEqual(app._clipboard_selected_image_id, "b")

    def test_keyboard_on_empty_gallery_is_safe(self):
        from types import SimpleNamespace
        app = SimpleNamespace(
            current_tab="clipboard", clipboard_page="images",
            clipboard_images=[], _clipboard_selected_image_id=None)
        self.assertEqual(clipboard_gallery.move_selection(app, 1), "break")

    def test_non_windows_clipboard_is_guarded(self):
        with patch.object(sys, "platform", "linux"):
            self.assertIsNone(clipboard_images.sequence_number())
            self.assertFalse(clipboard_images.image_available())
            with self.assertRaises(OSError):
                clipboard_images.copy_image(b"not-an-image")


if __name__ == "__main__":
    unittest.main()
