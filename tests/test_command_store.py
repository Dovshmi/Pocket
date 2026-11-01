"""Regression checks for one writable command library and backup safety."""
import json
from pathlib import Path
import tempfile
import unittest
from pocket import command_store as store

FIXTURE = {"schema": 1, "machines": ["Cisco", "Nokia 7210"],
           "commands": [{"id": "legacy123", "machine": "Cisco", "category": "Routing",
                         "description": "Read", "command": "show ip route", "source_row": 7}]}

class CommandStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.file = self.folder / "commands" / "commands.json"
        self.file.parent.mkdir()
        self.file.write_text(json.dumps(FIXTURE), encoding="utf-8")

    def test_add_edit_delete_without_automatic_backup(self):
        row = {"id": "user:"+"a"*32, "machine": "Nokia 7210", "category": "System",
               "description": "Version", "command": "show version"}
        store.save_command(self.file, row)
        old = store.read_document(self.file)["commands"][0]
        store.save_command(self.file, dict(old, description="Updated"), original=old)
        self.assertEqual(store.read_document(self.file)["commands"][0]["source_row"], 7)
        store.delete_command(self.file, row)
        self.assertEqual(len(store.read_document(self.file)["commands"]), 1)
        self.assertFalse((self.file.parent/"backups").exists())

    def test_explicit_backup_and_restore(self):
        backup = store.create_backup(self.file)
        self.assertTrue(backup.exists())
        row = {"id": "new", "machine": "Cisco", "category": "Routing",
               "description": "Added", "command": "show interfaces"}
        store.save_command(self.file, row)
        self.assertEqual(len(store.read_document(self.file)["commands"]), 2)
        store.restore_backup(self.file, backup)
        self.assertEqual(store.read_document(self.file), FIXTURE)
        self.assertEqual(len(list(backup.parent.glob("commands-*.json"))), 1)

    def test_legacy_migration_without_duplicates(self):
        row = {"id": "user:"+"b"*32, "machine": "Cisco", "category": "Other",
               "description": "Example", "command": "show custom"}
        self.assertEqual(store.migrate_custom(self.file, [row])[0], 1)
        self.assertEqual(store.migrate_custom(self.file, [row])[0], 0)

    def test_reject_conflict_and_corruption(self):
        old = store.read_document(self.file)["commands"][0]
        with self.assertRaises(ValueError):
            store.delete_command(self.file, dict(old, description="Stale"))
        self.file.write_text("{invalid", encoding="utf-8")
        with self.assertRaises(ValueError):
            store.save_command(self.file, old)
        self.assertEqual(self.file.read_text(), "{invalid")

    def test_recover_legacy_nested_file(self):
        self.file.unlink()
        old = self.folder/"Pocket_Commands_One_Library"/"commands"/"commands.json"
        old.parent.mkdir(parents=True)
        old.write_text(json.dumps(FIXTURE), encoding="utf-8")
        actual = store.resolve_library(self.folder, self.folder/"appdata", self.folder)
        self.assertEqual(actual, self.file)
        self.assertTrue(old.is_file())

if __name__ == "__main__":
    unittest.main()
