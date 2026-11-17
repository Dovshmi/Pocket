"""Pure live recording tests: modifiers, Numpad suffix and safe rejection."""
from types import SimpleNamespace
import unittest

from pocket import shortcut_recording as recording
from pocket import hotkey_settings as hk


class ShortcutRecordingTests(unittest.TestCase):
    def test_ctrl_alt_f8(self):
        item = recording.hotkey_from_event(
            "F8", state=0x0004 | 0x0008, async_mods={})
        self.assertEqual(item, {
            "ctrl": True, "shift": False, "alt": True,
            "win": False, "key": "F8"})
        self.assertEqual(hk.hotkey_label(item), "Ctrl+Alt+F8")

    def test_win_key_is_recognized_without_tk_mask(self):
        item = recording.hotkey_from_event(
            "p", state=0x0004, async_mods={"win": True})
        self.assertTrue(item["win"])
        self.assertEqual(item["key"], "P")

    def test_modifier_only_stays_armed(self):
        self.assertIsNone(recording.hotkey_from_event(
            "Control_L", state=0x0004, async_mods={}))
        self.assertIsNone(recording.quick_slot_prefix_from_event(
            "Super_L", state=0x0004, async_mods={}))

    def test_asterisk_space_and_f12(self):
        self.assertEqual(recording.hotkey_from_event(
            "asterisk", state=0x0004, async_mods={})["key"], "*")
        self.assertEqual(recording.hotkey_from_event(
            "KP_Multiply", state=0x0004, async_mods={})["key"], "*")
        self.assertEqual(recording.hotkey_from_event(
            "space", state=0x0004, async_mods={})["key"], "Space")
        self.assertEqual(hk.key_code("Space"), 0x20)
        self.assertEqual(recording.hotkey_from_event(
            "F12", state=0x0004, async_mods={})["key"], "F12")

    def test_bare_keys_or_unsupported_shortcuts_are_rejected(self):
        with self.assertRaises(ValueError):
            recording.hotkey_from_event("a", state=0, async_mods={})
        with self.assertRaises(ValueError):
            recording.hotkey_from_event("Tab", state=0x0004, async_mods={})

    def test_numpad_prefix_recording_preserves_numeric_suffix(self):
        for flags, expected in [
            ({"ctrl": True}, "ctrl"),
            ({"ctrl": True, "alt": True}, "ctrl_alt"),
            ({"ctrl": True, "win": True}, "ctrl_win"),
            ({"ctrl": True, "alt": True, "win": True}, "ctrl_alt_win"),
        ]:
            result = recording.quick_slot_prefix_from_event(
                "KP_3", async_mods=flags)
            self.assertEqual(result, expected)
        with self.assertRaises(ValueError):
            recording.quick_slot_prefix_from_event(
                "KP_3", async_mods={"ctrl": True, "shift": True})
        with self.assertRaises(ValueError):
            recording.quick_slot_prefix_from_event(
                "3", async_mods={"ctrl": True})
        with self.assertRaises(ValueError):
            recording.quick_slot_prefix_from_event(
                "KP_0", async_mods={"ctrl": True})


if __name__ == "__main__":
    unittest.main()
