"""Portable local-data routing, no-fallback and safe command seeding."""
import json
from pathlib import Path
import tempfile
import unittest
import portable_storage as p

class PortableStorageTests(unittest.TestCase):
    def test_standard_data_location_is_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "program"
            home = Path(d) / "profile"
            self.assertEqual(p.data_file(root=root, appdata=home),
                             home / "PocketDesk" / "data.json")

    def test_marker_routes_all_data_into_extracted_folder(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "Pocket"
            root.mkdir()
            (root / "portable.flag").write_text("", encoding="utf-8")
            self.assertEqual(p.data_file(root=root, appdata=Path(d) / "profile"),
                             root / "data" / "data.json")
            p.require_writable_portable_data(root)
            self.assertTrue((root / "data").is_dir())

    def test_bundle_seeds_public_commands_without_overwriting_edits(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            example = base / "bundle" / "commands" / "example_commands.json"
            example.parent.mkdir(parents=True)
            example.write_text(json.dumps({"commands":[
                {"id":"sample", "machine":"Cisco", "category":"Routing",
                 "description":"Route", "command":"show ip route"}]}), encoding="utf-8")
            target = p.resolve_portable_library(base / "data", base / "bundle")
            self.assertEqual(json.loads(target.read_text())["commands"][0]["id"],"sample")
            target.write_text('{"commands":[]}',encoding="utf-8")
            self.assertEqual(p.resolve_portable_library(base / "data", base / "bundle"),target)
            self.assertEqual(target.read_text(encoding="utf-8"),'{"commands":[]}')

    def test_no_private_sidecar_or_appdata_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root / "commands").mkdir()
            (root / "commands" / "commands.json").write_text('{"commands":[]}')
            with self.assertRaises(FileNotFoundError):
                p.resolve_portable_library(root / "data", root / "bundle")
            self.assertFalse((root / "data" / "commands.json").exists())

if __name__ == "__main__":
    unittest.main()
