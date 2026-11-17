"""Factory defaults vs. saved user preferences: local, headless regressions."""
from pathlib import Path
import runpy
import tempfile
import unittest

from pocket import port_presets, shortcut_folders


app = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "app.pyw"),
    run_name="test_factory_defaults")
default_data = app["default_data"]
load_data = app["load_data"]
save_data = app["save_data"]
restored_tab = app["restored_tab"]


class FactoryDefaultsTests(unittest.TestCase):
    def test_brand_new_profile_is_mini_with_two_links_inside_hebrew_folder(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            data = load_data(path)
            self.assertFalse(path.exists())
        self.assertEqual(data["settings"]["display_mode"], "mini")
        self.assertEqual(data["last_tab"], "notes")
        self.assertEqual(len(data["notes"]), 1)
        self.assertEqual(data["notes"][0]["title"], "הבאכש מתקרר")
        self.assertEqual(data["notes"][0]["body"], "תקלה באיזור בוכרה, הכל תקין אבל החינקלי כבר קר!!!!!")
        self.assertEqual(data["notes"][0]["direction"], "rtl")
        self.assertEqual(
            [(row["title"], row["url"], row["kind"]) for row in data["links"]],
            [
                ("DashDash", "https://dashdash-tau.vercel.app", "url"),
                ("My GitHub", "https://github.com/Dovshmi", "url"),
            ])
        layout = data["shortcut_folders"]
        self.assertEqual(len(layout["folders"]), 1)
        folder = layout["folders"][0]
        self.assertEqual(folder["title"], "אושפלו")
        self.assertTrue(folder["expanded"])
        self.assertEqual(layout["root"], [shortcut_folders.folder_key(folder["id"])])
        self.assertEqual(layout["children"][folder["id"]],
                         [item["id"] for item in data["links"]])
        # Both links stay in the folder after normalization and not unfiled.
        self.assertEqual(shortcut_folders.normalize(layout, data["links"]), layout)

    def test_untouched_legacy_first_note_is_migrated_with_id_preserved(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            legacy = default_data()
            first = legacy["notes"][0]
            first["title"] = "הבחשט מתקרר"
            first["body"] = "תקלה באזור הבוכרה, הכל תקין טבל החינקלי כבר קר."
            first_id = first["id"]
            legacy["notes"].append(app["new_note"]("Personal", "Keep this"))
            save_data(path, legacy)
            loaded = load_data(path)
        self.assertEqual(loaded["notes"][0]["id"], first_id)
        self.assertEqual(loaded["notes"][0]["title"], "הבאכש מתקרר")
        self.assertEqual(loaded["notes"][0]["body"],
                         "תקלה באיזור בוכרה, הכל תקין אבל החינקלי כבר קר!!!!!")
        self.assertEqual(loaded["notes"][1], legacy["notes"][1])
        self.assertEqual(loaded["active_note"], first_id)

    def test_first_note_with_user_edits_is_never_overwritten(self):
        for changed in ("title", "body"):
            with self.subTest(changed=changed):
                with tempfile.TemporaryDirectory() as tempdir:
                    path = Path(tempdir) / "data.json"
                    data = default_data()
                    first = data["notes"][0]
                    first["title"] = "הבחשט מתקרר"
                    first["body"] = "תקלה באזור הבוכרה, הכל תקין טבל החינקלי כבר קר."
                    first[changed] = "User's own content"
                    save_data(path, data)
                    loaded = load_data(path)
                self.assertEqual(loaded["notes"][0]["title"], first["title"])
                self.assertEqual(loaded["notes"][0]["body"], first["body"])

    def test_existing_legacy_starter_content_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            old = default_data()
            old["notes"][0]["title"] = "Welcome"
            old["notes"][0]["body"] = "Existing note text"
            old["notes"][0]["direction"] = "ltr"
            old["shortcut_folders"]["folders"][0]["title"] = "Ushpelo"
            save_data(path, old)
            restored = load_data(path)
        self.assertEqual(restored["notes"], old["notes"])
        self.assertEqual(restored["shortcut_folders"], old["shortcut_folders"])

    def test_tcp_input_defaults_are_prefilled_but_never_scanned(self):
        tools = default_data()["tools"]
        self.assertEqual(tools["target"], "8.8.8.8")
        self.assertEqual(tools["ports_input"], "21,22,443,80,8080,3389,53")
        self.assertEqual(port_presets.migrate_port_input(tools),
                         tools["ports_input"])
        self.assertEqual(port_presets.parse_manual_ports(tools["ports_input"]),
                         [21, 22, 443, 80, 8080, 3389, 53])
        self.assertEqual(tools["source"], "local")
        self.assertEqual(tools["mac_source"], "local")

    def test_existing_profile_preferences_and_custom_links_survive_upgrade(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            data = default_data()
            data["links"] = [app["new_link"]("My Tool", "https://example.org")]
            data.pop("shortcut_folders")  # Legacy flat shortcuts
            data["settings"]["display_mode"] = "normal"
            data["tools"].update(target="10.99.0.1",
                                 ports_input="443,12345", source="dashdash")
            data["last_tab"] = "ports"
            data["active_note"] = data["notes"][0]["id"]
            save_data(path, data)
            restored = load_data(path)
            self.assertEqual(restored["settings"]["display_mode"], "normal")
            self.assertEqual(restored["last_tab"], "ports")
            self.assertEqual(restored["tools"]["target"], "10.99.0.1")
            self.assertEqual(restored["tools"]["ports_input"], "443,12345")
            self.assertEqual(restored["tools"]["source"], "dashdash")
            self.assertEqual(restored["links"], data["links"])
            self.assertEqual(restored["shortcut_folders"]["folders"], [])
            self.assertEqual(restored["active_note"], data["active_note"])
            self.assertEqual(restored["notes"], data["notes"])

    def test_deleting_starter_links_does_not_reseed_them(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            data = default_data()
            data["links"] = []
            data["shortcut_folders"] = shortcut_folders.normalize(None, [])
            save_data(path, data)
            restored = load_data(path)
            self.assertEqual(restored["links"], [])
            self.assertEqual(restored["shortcut_folders"]["folders"], [])

    def test_legacy_profile_without_last_tab_preserves_old_mode(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            data = default_data()
            data.pop("last_tab")
            data["settings"]["display_mode"] = "normal"
            data["tools"] = {"target": "192.0.2.10", "single_port": "8443",
                             "mode": "single", "source": "local"}
            save_data(path, data)
            restored = load_data(path)
            self.assertEqual(restored["settings"]["display_mode"], "normal")
            self.assertEqual(restored["last_tab"], "notes")
            self.assertEqual(restored["tools"]["target"], "192.0.2.10")
            self.assertEqual(port_presets.migrate_port_input(restored["tools"]), "8443")
            data["settings"]["display_mode"] = "dashboard"
            save_data(path, data)
            restored = load_data(path)
            self.assertEqual(restored["settings"]["display_mode"], "dashboard")
            self.assertEqual(restored["last_tab"], "home")

    def test_restores_last_tool_and_recovers_hidden_or_invalid_tabs(self):
        data = default_data()
        settings = data["settings"]
        for choice in ("links", "ports", "commands", "settings", "notes"):
            self.assertEqual(restored_tab(choice, settings), choice)
        self.assertEqual(restored_tab("home", settings), "notes")
        self.assertEqual(restored_tab({"not": "a tool"}, settings), "notes")
        self.assertEqual(restored_tab("out-of-range", settings), "notes")
        settings["visible_tabs"] = ["mac", "ports"]
        self.assertEqual(restored_tab("links", settings), "mac")
        self.assertEqual(restored_tab("ports", settings), "ports")
        settings["display_mode"] = "dashboard"
        self.assertEqual(restored_tab("home", settings), "home")
        self.assertEqual(restored_tab("missing", settings), "home")

    def test_last_tool_and_mode_survive_profile_roundtrip(self):
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            data = default_data()
            data["last_tab"] = "links"
            data["settings"]["display_mode"] = "dashboard"
            save_data(path, data)
            restored = load_data(path)
            self.assertEqual(restored["last_tab"], "links")
            self.assertEqual(restored["settings"]["display_mode"], "dashboard")
            self.assertEqual(restored["shortcut_folders"], data["shortcut_folders"])


if __name__ == "__main__":
    unittest.main()
