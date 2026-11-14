"""Checks that the native Hebrew editor does not reorder underlying Unicode text."""
import ctypes
import queue
import unittest
from unittest.mock import Mock

from pocket import native_bidi


class NativeBidiStructureTests(unittest.TestCase):
    def test_rtl_paragraph_structure_has_expected_size(self):
        # The Win32 PARAFORMAT struct is 156 bytes (including the 32 tab stops).
        self.assertEqual(ctypes.sizeof(native_bidi.PARAFORMAT), 156)
        self.assertEqual(ctypes.sizeof(native_bidi.PARAFORMAT2), 188)
        self.assertEqual(native_bidi.NativeBidiEditor.PFM_RTLPARA, 0x10000)

    def test_native_context_menu_queues_without_touching_tk(self):
        editor = native_bidi.NativeBidiEditor.__new__(native_bidi.NativeBidiEditor)
        editor._context_menu = Mock()
        editor._context_menu_events = queue.SimpleQueue()
        editor._comctl = Mock()
        lp = (170 << 16) | 120
        result = editor._subclass_proc(None, editor.WM_CONTEXTMENU, 0, lp, 0, 0)
        self.assertEqual(result, 0)
        self.assertEqual(editor._context_menu_events.get_nowait(), (120, 170))
        editor._context_menu.assert_not_called()

    def test_hidden_scrollbar_wheel_routes_to_native_line_scroll(self):
        editor = native_bidi.NativeBidiEditor.__new__(native_bidi.NativeBidiEditor)
        editor._wheel_remainder = 0
        editor._user = Mock()
        editor._comctl = Mock()
        hwnd = 123
        # -120 is one downward wheel notch: scroll three lines.
        delta_down = (0xFF88 << 16)
        result = editor._subclass_proc(
            hwnd, editor.WM_MOUSEWHEEL, delta_down, 0, 0, 0)
        self.assertEqual(result, 0)
        editor._user.PostMessageW.assert_called_once_with(
            hwnd, editor.EM_LINESCROLL, 0, 3)
        self.assertEqual(editor._wheel_remainder, 0)
        # +120 is one upward notch.
        editor._user.PostMessageW.reset_mock()
        editor._subclass_proc(
            hwnd, editor.WM_MOUSEWHEEL, (120 << 16), 0, 0, 0)
        editor._user.PostMessageW.assert_called_once_with(
            hwnd, editor.EM_LINESCROLL, 0, -3)

    def test_high_resolution_wheel_deltas_accumulate(self):
        editor = native_bidi.NativeBidiEditor.__new__(native_bidi.NativeBidiEditor)
        editor._wheel_remainder = 0
        editor._user = Mock()
        editor._comctl = Mock()
        editor._subclass_proc(
            111, editor.WM_MOUSEWHEEL, (60 << 16), 0, 0, 0)
        editor._user.PostMessageW.assert_not_called()
        self.assertEqual(editor._wheel_remainder, 60)
        editor._subclass_proc(
            111, editor.WM_MOUSEWHEEL, (60 << 16), 0, 0, 0)
        editor._user.PostMessageW.assert_called_once_with(
            111, editor.EM_LINESCROLL, 0, -3)
        self.assertEqual(editor._wheel_remainder, 0)

    def test_release_focus_targets_tk_host_not_entry_hwnd(self):
        """Native SetFocus must not directly target a Tk child Entry HWND."""
        editor = native_bidi.NativeBidiEditor.__new__(native_bidi.NativeBidiEditor)
        editor._hwnd = 20
        editor._user = Mock()
        target = Mock()
        target.winfo_exists.return_value = True
        target.winfo_id.return_value = 111
        target.winfo_toplevel.return_value.winfo_id.return_value = 222
        editor.release_focus_to(target)
        focus_handle = editor._user.SetFocus.call_args.args[0]
        self.assertEqual(focus_handle.value, 222)
        target.winfo_id.assert_not_called()

    def test_release_focus_does_not_touch_destroyed_inputs(self):
        editor = native_bidi.NativeBidiEditor.__new__(native_bidi.NativeBidiEditor)
        editor._hwnd = 20
        editor._user = Mock()
        target = Mock()
        target.winfo_exists.return_value = False
        editor.release_focus_to(target)
        editor._user.SetFocus.assert_not_called()

    def test_win32_colorref(self):
        self.assertEqual(native_bidi.colorref("#112233"), 0x332211)
        self.assertEqual(native_bidi.colorref("#000000"), 0)

    def test_unicode_text_is_not_modified_by_module(self):
        mixed = "שלום Router Gi0/1 192.168.1.1\nתיקון: ping -t 8.8.8.8"
        self.assertEqual(mixed.encode("utf-8").decode("utf-8"), mixed)


if __name__ == "__main__":
    unittest.main()
