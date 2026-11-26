"""Command palette parsing and permission boundaries; no network calls."""
import unittest
from pocket import command_palette as cp

class CommandPaletteTests(unittest.TestCase):
    def setUp(self):
        self.settings = {"window_profiles":{"Work":{"width":620,"height":700}}}
        self.enabled = ["notes","ports","mac","subnet","extra","commands","reminders","clipboard","links"]

    def search(self, text, enabled=None):
        return cp.results({"notes":[{"id":"1","title":"Welcome","body":"example"}]}, [],
                          text, self.enabled if enabled is None else enabled, self.settings)

    def test_explicit_commands(self):
        for raw, key, args in [
            ("> new note","new_note",()),
            ("> theme dark blue","theme",("dark_blue",)),
            ("> size work","size",("Work",)),
            ("> port 192.168.1.1 80,554,2079-2084","ports",("192.168.1.1","80,554,2079-2084")),
            ("> subnet 192.168.10.0/26","subnet",("192.168.10.0","26")),
            ("> remind 21:30 Check ticket","timed_reminder",("21:30","Check ticket")),
            ("> cli cisco show vlan","cli",("cisco show vlan",)),
            ("> extra 10.0.0.1","extra",("10.0.0.1",)),
            ("> note Customer follow up","new_note",("Customer follow up",)),
        ]:
            with self.subTest(raw=raw):
                hit = self.search(raw)[0]
                self.assertEqual((hit["id"],hit["args"]), (key,args))

    def test_smart_input(self):
        self.assertEqual({h["id"] for h in self.search("192.168.10.1")},
                         {"ports","subnet","extra","copy"})
        self.assertEqual(self.search("192.168.10.0/26")[0]["id"], "subnet")
        self.assertEqual(self.search("00:00:0C:12:34:56")[0]["id"], "mac")
        self.assertEqual(self.search("80,443,2079-2084")[0]["id"], "ports")
        self.assertEqual(self.search("https://example.com")[0]["id"], "copy")

    def test_hidden_tools_and_invalid_commands(self):
        self.assertFalse(self.search("> port 192.168.1.1 443", ["notes"]))
        self.assertFalse(self.search("> port 192.168.1.1 1-65535"))
        self.assertFalse(self.search("> remind 99:30 invalid"))
        self.assertFalse(self.search("> powershell calc.exe"))
        self.assertFalse(self.search("> theme unknown"))

    def test_local_search_and_empty_catalog(self):
        self.assertEqual(self.search("Welcome")[0]["kind"], "note")
        self.assertTrue(self.search(""))
        self.assertEqual(self.search("notes")[0]["kind"], "tool")

if __name__ == "__main__":
    unittest.main()
