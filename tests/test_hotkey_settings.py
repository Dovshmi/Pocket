"""Configurable Pocket popup hotkey and compact Shortcuts search."""
import tempfile
import unittest
from pathlib import Path
import runpy
from pocket import hotkey_settings as hk

app = runpy.run_path(str((Path(__file__).resolve().parents[1] / "app.pyw")), run_name="hotkey_test")

class HotkeySettingsTests(unittest.TestCase):
    def test_default_and_labels(self):
        self.assertEqual(hk.hotkey_label(hk.DEFAULT_HOTKEY), "Ctrl+Shift+*")
        self.assertEqual(hk.hotkey_label({"ctrl": True,"shift": False,"alt": False,"win": False,"key": "P"}), "Ctrl+P")

    def test_combination_win32_codes(self):
        self.assertEqual(hk.bindings(hk.DEFAULT_HOTKEY),
                         ((0xB10, 0x4006, 0x38), (0xB11, 0x4006, 0x6A)))
        self.assertEqual(hk.bindings({"ctrl": True, "shift": False, "alt": True, "win": False, "key": "F5"}),
                         ((0xB10, 0x4003, 0x74),))

    def test_reject_unsafe_and_invalid(self):
        for item in (None, {}, {"key":"!"}, {"key":"P","ctrl": False,"alt":False,"win":False,"shift":True}):
            self.assertEqual(hk.normalize_hotkey(item), hk.DEFAULT_HOTKEY)

    def test_persist_selected_and_migrate_old_data(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "data.json"
            data = app["default_data"]()
            self.assertEqual(data["hotkey"], hk.DEFAULT_HOTKEY)
            data["hotkey"] = {"ctrl":True, "shift":False, "alt":False, "win":False, "key":"F5"}
            app["save_data"](path,data)
            self.assertEqual(app["load_data"](path)["hotkey"]["key"],"F5")
            data.pop("hotkey")
            app["save_data"](path,data)
            self.assertEqual(app["load_data"](path)["hotkey"],hk.DEFAULT_HOTKEY)

    def test_shortcut_search_casefold_target_and_kind(self):
        links = [
            {"title":"GitHub","url":"https://github.com","kind":"url"},
            {"title":"Projects","url":"C:/My Documents/Work","kind":"folder"},
            {"title":"Editor","url":"C:/tools/app.exe","kind":"file"},
        ]
        self.assertEqual([x["title"] for x in hk.filter_shortcuts(links," GITHUB ")],["GitHub"])
        self.assertEqual([x["title"] for x in hk.filter_shortcuts(links,"WORK")],["Projects"])
        self.assertEqual([x["title"] for x in hk.filter_shortcuts(links,"file")],["Editor"])
        self.assertEqual(hk.filter_shortcuts(links,"zzzz"),[])
        self.assertEqual(len(hk.filter_shortcuts(links,"")),3)

if __name__ == "__main__":
    unittest.main()
