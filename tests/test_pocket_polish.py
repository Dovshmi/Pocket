"""Regression checks for Pocket's refreshed visual and local-search features."""
import unittest
from pathlib import Path
import runpy
import tempfile
import clipboard_policy
import quick_search
import pocket_design
import settings_ui

APP = runpy.run_path(str((Path(__file__).resolve().parents[1] / "app.pyw")), run_name="audit_test")
TOOLS = [key for key, _ in APP["VISIBLE_TABS"]]


class SearchAndPrivacyTests(unittest.TestCase):
    def test_local_search_respects_visible_menus(self):
        data = {"notes":[{"id":"n1","title":"OSPF lab","body":"check neighbors"}],
                "links":[{"id":"l1","title":"Lab portal","url":"https://example.invalid"}]}
        commands = [{"id":"c1","machine":"Cisco","category":"Routing",
                     "description":"Show ospf neighbors","command":"show ip ospf neighbor"}]
        hits = quick_search.results(data, commands, "ospf", TOOLS)
        self.assertTrue(any(h["kind"]=="note" for h in hits))
        self.assertTrue(any(h["kind"]=="command" for h in hits))
        self.assertFalse(any(h["kind"]=="command" for h in
                             quick_search.results(data, commands, "ospf", ["notes"])))
        self.assertTrue(any(h["kind"]=="shortcut" for h in
                            quick_search.results(data, commands, "portal", TOOLS)))
        self.assertEqual(quick_search.results(data, commands, "", TOOLS), [])
        self.assertEqual(len(quick_search.results(data, commands, "ospf", TOOLS, limit=1)), 1)

    def test_sensitive_filter_rejects_common_secrets(self):
        for secret in ("-----BEGIN PRIVATE KEY-----abc", "Bearer abcdefghijklmnopqrstuvwxyz",
                       "password = supersecret", "api_key: somelongtoken",
                       "ghp_abcdefghijklmnopqrstuvwxyz"):
            with self.subTest(secret=secret):
                self.assertFalse(clipboard_policy.should_capture(secret))
                self.assertTrue(clipboard_policy.should_capture(secret, sensitive_filter=False))
        self.assertTrue(clipboard_policy.should_capture("show ip route"))
        self.assertFalse(clipboard_policy.should_capture("show ip route", paused=True))
        self.assertFalse(clipboard_policy.should_capture(" "))
        self.assertFalse(clipboard_policy.should_capture("x"*20001))

    def test_settings_migration_and_roundtrip(self):
        normalized=APP["normalize_settings"]({})
        self.assertFalse(normalized["clipboard_paused"])
        self.assertTrue(normalized["clipboard_sensitive_filter"])
        self.assertFalse(APP["normalize_settings"](
            {"clipboard_sensitive_filter":False})["clipboard_sensitive_filter"])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"data.json"
            data=APP["default_data"]()
            data["settings"]["clipboard_paused"]=True
            data["settings"]["clipboard_sensitive_filter"]=False
            APP["save_data"](path,data)
            loaded=APP["load_data"](path)
            self.assertTrue(loaded["settings"]["clipboard_paused"])
            self.assertFalse(loaded["settings"]["clipboard_sensitive_filter"])
            self.assertNotIn("clipboard_items",path.read_text(encoding="utf-8"))

    def test_design_palette_and_settings_hooks(self):
        for theme in ("blue","purple","red","green","black"):
            c=pocket_design.colors(theme)
            self.assertTrue(c["ACCENT"].startswith("#"))
        src=(Path(__file__).resolve().parents[1] / "app.pyw").read_text(encoding="utf-8")
        self.assertIn("design.section_header", src)
        self.assertIn("design.configure_ttk", src)
        self.assertIn("self._open_global_search", src)
        self.assertIn("clipboard_policy.should_capture", src)
        self.assertIn("app._open_global_search", Path(settings_ui.__file__).read_text(encoding="utf-8"))

if __name__=="__main__":
    unittest.main()
