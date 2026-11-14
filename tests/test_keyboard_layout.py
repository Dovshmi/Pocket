"""Keyboard-position converter parity with DashDash and clipboard safety."""
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import Mock

from pocket import keyboard_layout as kl
from pocket import hotkey_settings as hk

appmod = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                        run_name="keyboard_layout_test")


class FakeClipboardRoot:
    def __init__(self, text):
        self.text = text
        self.clipboard_clear = Mock(side_effect=self._clear)
        self.clipboard_append = Mock(side_effect=self._append)

    def _clear(self):
        self.text = ""

    def _append(self, value):
        self.text += value

    def clipboard_get(self):
        if not self.text:
            raise appmod["tk"].TclError("No text")
        return self.text


class ConversionTests(unittest.TestCase):
    def test_dashdash_map_matches_both_directions(self):
        self.assertEqual(kl.convert("akuo"), "שלום")
        self.assertEqual(kl.convert("שלום"), "akuo")
        self.assertEqual(kl.convert("rvh"), "רהי")
        self.assertEqual(kl.convert("ENGLISH"), "קמעךןדי")
        self.assertEqual(kl.convert("1234\nakuo 567"), "1234\nשלום 567")
        self.assertEqual(kl.convert(""), "")
        self.assertEqual(kl.convert("12345!"), "12345!")
        with self.assertRaises(TypeError):
            kl.convert(None)

    def test_dashdash_exact_punctuation_mapping(self):
        self.assertEqual(kl.convert("[];'/.,q"), "][ף,.ץת/")
        self.assertEqual(kl.convert(kl.convert("שלום")), "שלום")

    def test_global_conversion_reads_latest_real_clipboard_value(self):
        root = FakeClipboardRoot("akuo")
        app = type("AppStub", (), {})()
        app.root = root
        app.settings = {"visible_tabs": ["notes"], "clipboard_paused": False,
                        "clipboard_sensitive_filter": True}
        app.current_tab = "notes"
        app.clipboard_items = []
        app._clipboard_last = None
        app._clipboard_sequence = None
        app._notify = Mock()
        self.assertTrue(appmod["PocketDesk"]._convert_clipboard_text(app))
        self.assertEqual(root.text, "שלום")
        self.assertEqual(app.clipboard_items, [])
        app._notify.assert_called_once()
        self.assertNotIn("שלום", str(app._notify.call_args))

    def test_context_menu_converts_selected_item_not_current_clipboard(self):
        root = FakeClipboardRoot("unrelated")
        app = type("AppStub", (), {})()
        app.root = root
        app.settings = {"visible_tabs": ["notes"], "clipboard_paused": True,
                        "clipboard_sensitive_filter": True}
        app.current_tab = "notes"
        app.clipboard_items = []
        app._clipboard_sequence = None
        app._notify = Mock()
        self.assertTrue(appmod["PocketDesk"]._convert_clipboard_text(app, "akuo"))
        self.assertEqual(root.text, "שלום")

    def test_empty_and_unmapped_clipboard_preserves_contents(self):
        for value in ("", "12345"):
            root = FakeClipboardRoot(value)
            app = type("AppStub", (), {})()
            app.root = root
            app._notify = Mock()
            self.assertFalse(appmod["PocketDesk"]._convert_clipboard_text(app))
            self.assertEqual(root.text, value)
            root.clipboard_clear.assert_not_called()

    def test_hotkey_default_persisted_with_legacy_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            data = appmod["default_data"]()
            self.assertEqual(data["convert_hotkey"], hk.DEFAULT_CONVERT_HOTKEY)
            data.pop("convert_hotkey")
            appmod["save_data"](path, data)
            loaded = appmod["load_data"](path)
            self.assertEqual(loaded["convert_hotkey"], hk.DEFAULT_CONVERT_HOTKEY)
            self.assertFalse(hk.collides(loaded["convert_hotkey"], loaded["hotkey"]))

    def test_hotkey_collision_and_star_alias(self):
        popup = hk.DEFAULT_HOTKEY
        self.assertFalse(hk.collides(hk.DEFAULT_CONVERT_HOTKEY, popup))
        self.assertTrue(hk.collides(popup, popup))
        alias = dict(popup, key="8")
        self.assertTrue(hk.collides(popup, alias))
        clash = hk.normalize_convert_hotkey(popup, popup=popup)
        self.assertEqual(clash, hk.DEFAULT_CONVERT_HOTKEY)
        self.assertEqual(hk.normalize_convert_hotkey(None, popup=popup),
                         hk.DEFAULT_CONVERT_HOTKEY)
        self.assertEqual(hk.normalize_convert_hotkey({"key":"!"}, popup=alias),
                         hk.DEFAULT_CONVERT_HOTKEY)

    def test_win32_hotkey_ids_are_independent(self):
        a = hk.bindings(hk.DEFAULT_HOTKEY)
        b = hk.bindings(hk.DEFAULT_CONVERT_HOTKEY, 0xB30)
        self.assertEqual(a, ((0xB10, 0x4006, 0x38), (0xB11, 0x4006, 0x6A)))
        self.assertEqual(b, ((0xB30, 0x4003, 0x78),))
        self.assertEqual({i for i, *_ in a} & {i for i, *_ in b}, set())


if __name__ == "__main__":
    unittest.main()
