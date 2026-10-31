"""Pure Extra Mini multi-page model and old-data compatibility."""
from pathlib import Path
import runpy
import tempfile
import unittest

import launcher_pages as lp
import smart_templates as smart

ROOT = Path(__file__).resolve().parent
app = runpy.run_path(str(ROOT / "app.pyw"), run_name="test_extra_mini_pages")


class MultiPageModelTests(unittest.TestCase):
    def setUp(self):
        self.enabled = [key for key, _ in app["VISIBLE_TABS"]]
        self.data = {
            "notes": [{"id": "n1", "title": "Work checklist", "body": "Verify customer"}],
            "links": [{"id": "l1", "title": "Local wiki", "url": "https://example.test"}],
        }
        self.commands = [
            {"id": "c1", "machine": "Cisco", "category": "Routing",
             "description": "Route table", "command": "show ip route"},
            {"id": "c2", "machine": "FortiGate", "category": "Diagnostics",
             "description": "Ping target", "command": "execute ping x.x.x.x"},
        ]
        self.commands[1]["template"] = smart.validate_template(
            smart.suggest_template(self.commands[1]["command"]),
            self.commands[1]["command"])

    def test_three_pages_and_legacy_slots_migrate(self):
        pages = lp.normalize_pages(None, ["notes", None, "commands", "subnet"])
        self.assertEqual(len(pages), 3)
        self.assertTrue(all(len(page["tiles"]) == 4 for page in pages))
        self.assertEqual(pages[0]["tiles"][0], {"kind": "tool", "id": "notes"})
        self.assertIsNone(pages[0]["tiles"][1])
        self.assertEqual(lp.legacy_first_page(pages),
                         ["notes", None, "commands", "subnet"])
        self.assertEqual(pages[1]["tiles"], [None]*4)
        self.assertEqual(pages[2]["tiles"], [None]*4)

    def test_add_specific_references_and_copy_flag(self):
        pages = lp.default_pages()
        pages = lp.put(pages, 1, 0, {"kind": "note", "id": "n1", "label": "Shift"})
        pages = lp.put(pages, 1, 1, {"kind": "command", "id": "c1", "action": "copy"})
        pages = lp.put(pages, 1, 2, {"kind": "template", "id": "c2"})
        pages = lp.put(pages, 1, 3, {"kind": "shortcut", "id": "l1"})
        self.assertEqual([t["kind"] for t in pages[1]["tiles"]],
                         ["note", "command", "template", "shortcut"])
        states = [lp.lookup(tile, self.data, self.commands, self.enabled)
                  for tile in pages[1]["tiles"]]
        self.assertTrue(all(r["status"] == "ready" for r in states))
        self.assertEqual(states[0]["title"], "Shift")
        self.assertEqual(states[1]["action"], "copy")
        self.assertEqual(states[2]["detail"], "Fill template")
        self.assertEqual(states[3]["title"], "Local wiki")

    def test_hidden_deleted_and_stale_items_are_disabled_not_reassigned(self):
        self.assertEqual(lp.lookup({"kind": "note", "id": "gone"}, self.data,
                                    self.commands, self.enabled)["status"], "missing")
        self.assertEqual(lp.lookup({"kind": "command", "id": "gone"}, self.data,
                                    self.commands, self.enabled)["status"], "missing")
        self.assertEqual(lp.lookup({"kind": "tool", "id": "commands"}, self.data,
                                    self.commands, ["notes"])["status"], "hidden")
        self.assertEqual(lp.lookup({"kind": "note", "id": "n1"}, self.data,
                                    self.commands, ["commands"])["status"], "hidden")
        self.commands[1]["command"] = "execute ping 203.0.113.1"
        self.assertEqual(lp.lookup({"kind": "template", "id": "c2"}, self.data,
                                    self.commands, self.enabled)["status"], "needs_review")

    def test_rename_and_cross_page_swap_preserve_source(self):
        pages = lp.default_pages()
        pages = lp.put(pages, 1, 2, {"kind": "note", "id": "n1"})
        pages = lp.rename(pages, 1, 2, "Pinned checklist")
        pages = lp.rename_page(pages, 1, "Operations")
        self.assertEqual(pages[1]["name"], "Operations")
        pages = lp.move(pages, 1, 2, 0, 0)
        self.assertEqual(pages[0]["tiles"][0]["id"], "n1")
        self.assertEqual(pages[1]["tiles"][2], {"kind": "tool", "id": "commands"})
        self.assertEqual(lp.legacy_first_page(pages)[0], None)
        self.assertEqual(self.data["notes"][0]["id"], "n1")

    def test_search_filter_and_template_picker(self):
        self.assertTrue(any(r["tile"]["id"] == "n1" for r in
                            lp.candidates(self.data, self.commands, self.enabled,
                                          "note", "work")))
        self.assertEqual([r["tile"]["id"] for r in
                          lp.candidates(self.data, self.commands, self.enabled,
                                        "template")], ["c2"])
        self.assertEqual(lp.candidates(self.data, self.commands, ["notes"],
                                       "command", "route"), [])
        self.assertTrue(lp.candidates(self.data, self.commands, self.enabled,
                                      "shortcut", "wiki"))

    def test_corrupt_preferences_sanitized_and_page_index_bounded(self):
        self.assertEqual(lp.page_index(-1), 0)
        self.assertEqual(lp.page_index(3), 0)
        self.assertEqual(lp.page_index(True), 0)
        self.assertEqual(lp.clean_tile({"kind":"command","id":""}), None)
        self.assertEqual(lp.clean_tile({"kind":"tool","id":"missing"}), None)
        pages = lp.normalize_pages([{}, [], {"tiles": ["wrong", None, None, None]}])
        self.assertEqual(len(pages), 3)
        self.assertTrue(all(len(page["tiles"]) == 4 for page in pages))

    def test_persist_references_and_page_without_clipboard_history(self):
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "data.json"
            data = app["default_data"]()
            data["extra_mini_pages"] = lp.put(data["extra_mini_pages"], 2, 0,
                    {"kind":"note", "id":data["notes"][0]["id"]})
            data["extra_mini_page"] = 2
            app["save_data"](file, data)
            loaded = app["load_data"](file)
            self.assertEqual(loaded["extra_mini_pages"], data["extra_mini_pages"])
            self.assertEqual(loaded["extra_mini_page"], 2)
            self.assertEqual(loaded["settings"], data["settings"])
            self.assertNotIn("clipboard_items", loaded)


if __name__ == "__main__":
    unittest.main()
