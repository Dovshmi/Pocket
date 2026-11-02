"""Win32 global-shortcut mapping tests (Windows API is injected and mocked)."""
from pathlib import Path
import runpy
import unittest

mod = runpy.run_path(str((Path(__file__).resolve().parents[1] / 'app.pyw')), run_name='test_import')


class HotkeyRegistrationTests(unittest.TestCase):
    def test_standard_and_numeric_multiply(self):
        calls = []

        def register(hwnd, id_, modifiers, key):
            calls.append((hwnd, id_, modifiers, key))
            return True

        ids = mod['register_toggle_hotkeys'](register, 42)
        self.assertEqual(ids, {0xB10, 0xB11})
        self.assertEqual([c[3] for c in calls], [0x38, 0x6A])
        self.assertTrue(all(c[0] == 42 for c in calls))
        self.assertTrue(all(c[2] & 0x02 and c[2] & 0x04 for c in calls))
        self.assertTrue(all(c[2] & 0x4000 for c in calls))

    def test_collision_does_not_block_other_binding(self):
        ids = mod['register_toggle_hotkeys'](lambda hwnd, id_, mods, vk: id_ == 0xB11, 1)
        self.assertEqual(ids, {0xB11})

    def test_total_collision_allows_fallback_to_tray(self):
        ids = mod['register_toggle_hotkeys'](lambda *_: False, 1)
        self.assertEqual(ids, set())

    def test_windows_tray_recognizes_hotkey_message(self):
        self.assertEqual(mod['WindowsTray'].WM_HOTKEY, 0x0312)
        self.assertEqual(mod['WindowsTray'].WM_TRAY, 0x8000 + 37)


if __name__ == '__main__':
    unittest.main()
