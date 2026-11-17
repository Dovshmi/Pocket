"""Portable selective backup regression tests, including cross-machine restore."""
from copy import deepcopy
from pathlib import Path
import base64
import json
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from pocket import portable_backup as pb
from pocket import settings_reset as sr
from pocket import clipboard_database as cdb

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/3bUAAAAASUVORK5CYII="
)


def profile():
    return {
        "notes": [{"id": "note1", "title": "Hi", "body": "First note",
                   "phone": "", "pinned": False}],
        "active_note": "note1",
        "links": [{"id": "link1", "title": "DashDash",
                   "url": "https://example.org", "kind": "url"}],
        "shortcut_folders": {"folders": [], "children": {}, "root": ["l:link1"]},
        "settings": {"display_mode": "normal", "use_windows_proxy": True,
                     "quick_slots_enabled": True,
                     "quick_slots_paste_prefix": "ctrl_alt",
                     "quick_slots_copy_prefix": "ctrl_win"},
        "clipboard_slots": {"1": "PRIVATE SLOT", "9": "PRIVATE SLOT 9"},
        "theme": "blue",
        "hotkey": {"ctrl": True, "alt": False, "shift": True,
                   "win": False, "key": "*"},
        "convert_hotkey": {"ctrl": True, "alt": True, "shift": False,
                           "win": False, "key": "V"},
        "command_state": {"machine": "All machines", "favorites": [],
                          "recent": []},
        "custom_commands": [],
    }


def cli_doc():
    return {"commands": [{
        "id": "cli1", "machine": "Cisco", "category": "show",
        "description": "See IP routes", "command": "show ip route",
        "template": {"sample": "kept"},
    }]}


class PortableBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.target = self.root / "target"
        self.source.mkdir()
        self.target.mkdir()
        self.cli = self.source / "commands.json"
        self.cli.write_text(json.dumps(cli_doc()), encoding="utf-8")

    def backup(self, selected=pb.RECOMMENDED):
        output = self.root / "portable.zip"
        pb.make_backup(output, profile(), selected=selected,
                       commands_path=self.cli, profile_dir=self.source)
        return output, pb.read_backup(output)

    def test_export_availability_only_enables_categories_with_data(self):
        existing = pb.available_export_categories(
            profile(), commands_path=self.cli, profile_dir=self.source)
        self.assertEqual(existing, ("notes", "links", "cli", "settings"))
        self.assertNotIn("clipboard_text", existing)
        self.assertNotIn("clipboard_images", existing)
        empty = profile()
        empty["links"] = []
        self.cli.write_text(json.dumps({"commands": []}), encoding="utf-8")
        available = pb.available_export_categories(
            empty, commands_path=self.cli, profile_dir=self.source)
        self.assertEqual(available, ("notes", "settings"))
        db = cdb.ClipboardDatabase(self.source)
        db.save_text("2026-11-17", [
            {"id": "f" * 32, "text": "Saved in database",
             "time": "10:00:00", "pinned": False}
        ])
        self.assertEqual(pb.available_export_categories(
            empty, commands_path=self.cli, profile_dir=self.source),
            ("notes", "settings", "clipboard_text"))

    def test_restore_availability_shows_only_present_nonempty_categories(self):
        _file, partial = self.backup(("notes", "settings"))
        self.assertEqual(pb.available_restore_categories(
            partial, commands_path=self.cli), ("notes", "settings"))
        self.assertNotIn("links", pb.available_restore_categories(
            partial, commands_path=self.cli))
        _file, full = self.backup()
        self.assertEqual(pb.available_restore_categories(
            full, commands_path=self.cli), pb.RECOMMENDED)
        self.assertEqual(pb.available_restore_categories(
            full, commands_path=None), ("notes", "links", "settings"))
        full["payload"]["links"]["links"] = []
        self.assertEqual(pb.available_restore_categories(
            full, commands_path=self.cli), ("notes", "cli", "settings"))
        self.assertNotIn("quick_slots", pb.CATEGORIES)

    def test_all_recommended_categories_exclude_quick_slots_even_settings(self):
        archive, result = self.backup()
        self.assertEqual(result["manifest"]["categories"], list(pb.RECOMMENDED))
        raw = archive.read_bytes()
        self.assertNotIn(b"PRIVATE SLOT", raw)
        self.assertNotIn("clipboard_slots", str(result["payload"]))
        self.assertFalse(set(result["payload"]["settings"]["settings"])
                         & pb.QUICK_SLOT_KEYS)
        self.assertEqual(result["payload"]["cli"]["command_state"]["favorites"], [])
        self.assertEqual(
            json.loads(result["files"]["cli/commands.json"])["commands"][0]["template"],
            {"sample": "kept"})

    def test_partial_notes_backup_and_merge_preserves_local_conflict_and_slots(self):
        _, bundle = self.backup(("notes",))
        destination = profile()
        destination["notes"][0]["body"] = "MY EDIT"
        destination["notes"].append({"id": "local", "title": "Local", "body": "Don't touch"})
        incoming = bundle["payload"]["notes"]["notes"]
        incoming.append({"id": "new", "title": "Imported", "body": "New"})
        plan = pb.plan_restore(bundle, destination, selected=("notes",), mode="merge")
        self.assertEqual(plan["report"]["notes"]["conflicts"], 1)
        self.assertEqual(plan["report"]["notes"]["added"], 1)
        self.assertEqual([x["body"] for x in plan["profile"]["notes"]],
                         ["MY EDIT", "Don't touch", "New"])
        self.assertEqual(plan["profile"]["links"], destination["links"])
        self.assertEqual(plan["profile"]["clipboard_slots"], destination["clipboard_slots"])

    def test_replace_only_links_keeps_other_categories(self):
        _, bundle = self.backup(("links",))
        current = profile()
        current["links"][0]["url"] = "https://local.invalid"
        current["notes"][0]["body"] = "Unrelated"
        plan = pb.plan_restore(bundle, current, selected=["links"], mode="replace")
        self.assertEqual(plan["profile"]["links"][0]["url"], "https://example.org")
        self.assertEqual(plan["profile"]["notes"], current["notes"])
        self.assertEqual(plan["profile"]["clipboard_slots"], current["clipboard_slots"])

    def test_settings_restore_never_overwrites_local_quick_slot_preferences(self):
        _, bundle = self.backup(("settings",))
        current = profile()
        current["settings"].update(
            display_mode="mini", quick_slots_enabled=False,
            quick_slots_paste_prefix="ctrl", quick_slots_copy_prefix="ctrl_alt_win")
        current["clipboard_slots"]["1"] = "LOCAL"
        for mode in ("merge", "replace"):
            plan = pb.plan_restore(bundle, current, selected=["settings"], mode=mode)
            settings = plan["profile"]["settings"]
            self.assertEqual(settings["display_mode"], "normal")
            self.assertFalse(settings["quick_slots_enabled"])
            self.assertEqual(settings["quick_slots_paste_prefix"], "ctrl")
            self.assertEqual(settings["quick_slots_copy_prefix"], "ctrl_alt_win")
            self.assertEqual(plan["profile"]["clipboard_slots"]["1"], "LOCAL")

    def test_cli_merge_keeps_existing_modified_and_adds_new(self):
        _, bundle = self.backup(("cli",))
        current_cli = cli_doc()
        current_cli["commands"][0]["command"] = "show running-config"
        bundle["files"]["cli/commands.json"] = json.dumps({
            "commands": cli_doc()["commands"] + [{
                "id": "cli2", "machine": "Cisco", "category": "show",
                "description": "Interfaces", "command": "show interfaces"}],
        }).encode("utf-8")
        plan = pb.plan_restore(bundle, profile(), selected=["cli"], mode="merge",
                               current_commands=current_cli)
        self.assertEqual(plan["report"]["cli"]["conflicts"], 1)
        self.assertEqual(plan["report"]["cli"]["added"], 1)
        self.assertEqual(plan["commands"]["commands"][0]["command"],
                         "show running-config")
        self.assertEqual(plan["commands"]["commands"][1]["id"], "cli2")

    def test_clipboard_database_text_and_images_are_explicit_opt_in(self):
        db = cdb.ClipboardDatabase(self.source)
        day = "2026-11-17"
        db.save_text(day, [{"id": "a" * 32, "text": "historical value",
                            "time": "12:30:00", "pinned": False}])
        db.ensure_folders()
        name = day + "_12-30-00_" + "b" * 32 + ".png"
        (db.image_dir / name).write_bytes(PNG)
        _, bundle = self.backup(("clipboard_text", "clipboard_images"))
        self.assertEqual(bundle["payload"]["clipboard_text"][day][0]["text"],
                         "historical value")
        self.assertEqual(bundle["files"]["clipboard/images/" + name], PNG)
        target_data = profile()
        target_path = self.target / "data.json"
        from pocket.data_recovery import save_profile
        save_profile(target_path, target_data)
        safety, report = pb.apply_restore(
            bundle, target_data,
            selected=["clipboard_text", "clipboard_images"], mode="merge",
            profile_path=target_path)
        self.assertTrue(safety.exists())
        imported = cdb.ClipboardDatabase(self.target)
        self.assertEqual(imported.load_text(day)[0]["text"], "historical value")
        self.assertEqual((imported.image_dir / name).read_bytes(), PNG)
        self.assertEqual(report["clipboard_images"]["items"], 1)

    def test_restore_writes_safety_and_never_loses_unselected_data(self):
        _, bundle = self.backup(("notes", "links", "cli"))
        target_data = profile()
        target_data["notes"][0]["body"] = "Different"
        target_data["clipboard_slots"] = {"4": "LOCAL ONLY"}
        from pocket.data_recovery import save_profile
        target_path = self.target / "data.json"
        save_profile(target_path, target_data)
        target_cli = self.target / "commands.json"
        target_cli.write_text(json.dumps({"commands": []}), encoding="utf-8")
        safety, _ = pb.apply_restore(
            bundle, target_data, selected=("notes", "cli"), mode="replace",
            profile_path=target_path, commands_path=target_cli)
        self.assertTrue(safety.is_file())
        self.assertEqual(pb.read_backup(safety)["manifest"]["categories"],
                         ["notes", "cli"])
        saved = json.loads(target_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["notes"][0]["body"], "First note")
        self.assertEqual(saved["links"], target_data["links"])
        self.assertEqual(saved["clipboard_slots"], {"4": "LOCAL ONLY"})
        self.assertEqual(json.loads(target_cli.read_text())["commands"][0]["id"], "cli1")

    def test_reject_zip_slip_duplicate_members_and_tampering(self):
        bad_path = self.root / "bad.zip"
        with ZipFile(bad_path, "w", ZIP_DEFLATED) as z:
            z.writestr("../escape.json", "{}")
            z.writestr("manifest.json", "{}")
        with self.assertRaises(ValueError):
            pb.read_backup(bad_path)
        good, _ = self.backup(("notes",))
        with ZipFile(good, "a") as z:
            z.writestr("payload.json", "{}")
        with self.assertRaises(ValueError):
            pb.read_backup(good)

    def test_unknown_category_and_empty_selection_rejected(self):
        for values in ([], ["quick_slots"], ["notes", "unexpected"]):
            with self.assertRaises(ValueError):
                pb.select_categories(values)
        self.assertNotIn("quick_slots", pb.CATEGORIES)


class DefaultSettingsTests(unittest.TestCase):
    def test_only_selected_preferences_are_reset(self):
        data = profile()
        defaults = deepcopy(data)
        defaults["settings"]["display_mode"] = "mini"
        defaults["settings"]["use_windows_proxy"] = False
        defaults["hotkey"]["key"] = "P"
        current = deepcopy(data)
        current["hotkey"]["key"] = "Q"
        output = sr.reset_preferences(current, defaults, ["appearance", "keyboard"])
        self.assertEqual(output["settings"]["display_mode"], "mini")
        self.assertEqual(output["hotkey"]["key"], "P")
        self.assertTrue(output["settings"]["use_windows_proxy"])
        self.assertEqual(output["notes"], data["notes"])
        self.assertEqual(output["links"], data["links"])
        self.assertEqual(output["clipboard_slots"], data["clipboard_slots"])
        self.assertEqual(current["hotkey"]["key"], "Q")


if __name__ == "__main__":
    unittest.main()
