"""Windows Quick Slot notifications show slot identity and a bounded text preview."""
import unittest
from pocket import quick_slots


class QuickSlotNotificationTests(unittest.TestCase):
    def test_saved_text_and_slot_number(self):
        title, detail = quick_slots.slot_notification("saved", 2, "192.168.1.254")
        self.assertIn("2", title)
        self.assertIn("Saved", title)
        self.assertIn("192.168.1.254", detail)

    def test_pasted_hebrew_text_and_slot_number(self):
        title, detail = quick_slots.slot_notification("pasted", 8, "שלום עולם")
        self.assertIn("8", title)
        self.assertIn("Pasted", title)
        self.assertIn("שלום עולם", detail)

    def test_clipboard_mode_requests_manual_paste(self):
        title, detail = quick_slots.slot_notification("clipboard", 1, "test value")
        self.assertIn("Copied", title)
        self.assertNotIn("Pasted", title)
        self.assertIn("Press Ctrl+V", detail)
        self.assertIn("test value", detail)

    def test_existing_slot_gives_readable_text(self):
        title, detail = quick_slots.slot_notification("already", 4, "same value")
        self.assertIn("Unchanged", title)
        self.assertIn("same value", detail)

    def test_multiline_long_text_is_compact_and_bounded(self):
        preview = quick_slots.notification_preview("first\n  second\t" + "x" * 200)
        self.assertTrue(preview.startswith("first second "))
        self.assertTrue(preview.endswith("…"))
        self.assertLessEqual(len(preview), 108)
        self.assertNotIn("\n", preview)

    def test_invalid_slot_and_empty_value(self):
        self.assertEqual(quick_slots.notification_preview(None), "(No text)")
        with self.assertRaises(ValueError):
            quick_slots.slot_notification("saved", 10, "hi")

    def test_new_copy_and_original_paste_defaults(self):
        self.assertEqual(quick_slots.DEFAULT_COPY_PREFIX, "ctrl_alt_win")
        self.assertEqual(quick_slots.DEFAULT_PASTE_PREFIX, "ctrl_alt")
        paste, save = tuple(quick_slots.slot_hotkeys())[:2]
        self.assertEqual(paste[1], quick_slots.modifier_flags("ctrl_alt"))
        self.assertEqual(save[1], quick_slots.modifier_flags("ctrl_alt_win"))


if __name__ == "__main__":
    unittest.main()
