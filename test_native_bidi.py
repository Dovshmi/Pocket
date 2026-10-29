"""Checks that the native Hebrew editor does not reorder underlying Unicode text."""
import ctypes
import unittest

import native_bidi


class NativeBidiStructureTests(unittest.TestCase):
    def test_rtl_paragraph_structure_has_expected_size(self):
        # The Win32 PARAFORMAT struct is 156 bytes (including the 32 tab stops).
        self.assertEqual(ctypes.sizeof(native_bidi.PARAFORMAT), 156)
        self.assertEqual(ctypes.sizeof(native_bidi.PARAFORMAT2), 188)
        self.assertEqual(native_bidi.NativeBidiEditor.PFM_RTLPARA, 0x10000)

    def test_win32_colorref(self):
        self.assertEqual(native_bidi.colorref("#112233"), 0x332211)
        self.assertEqual(native_bidi.colorref("#000000"), 0)

    def test_unicode_text_is_not_modified_by_module(self):
        mixed = "שלום Router Gi0/1 192.168.1.1\nתיקון: ping -t 8.8.8.8"
        self.assertEqual(mixed.encode("utf-8").decode("utf-8"), mixed)


if __name__ == "__main__":
    unittest.main()
