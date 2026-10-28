"""Machine selection and merging regression tests for full Pocket source."""
import unittest
from pathlib import Path
import command_helper as ch
import machine_catalog as mc

ROOT = Path(__file__).resolve().parent

class MachineCatalogueTests(unittest.TestCase):
    def test_all_catalogued_categories_visible(self):
        names = mc.load_catalog(ROOT / "commands" / "machine_catalog.json")
        self.assertEqual(len(names), 32)
        base = ch.load_library(ROOT / "commands" / "sample_commands.json")
        extras = ch.load_library(ROOT / "commands" / "public_additions.json")
        shown = mc.machine_names(base + extras, names)
        for device in names:
            self.assertIn(device, shown)
        self.assertIn("Nokia 7210", shown)
        self.assertIn("Check Point Gaia", shown)

    def test_private_and_public_commands_merge(self):
        public = ch.load_library(ROOT / "commands" / "sample_commands.json")
        extras = ch.load_library(ROOT / "commands" / "public_additions.json")
        private = [{"id": "local:example", "machine": "Cisco",
                    "category": "Local", "description": "Local reference",
                    "command": "show example local"}]
        merged = mc.combine_references(private, public, extras)
        self.assertTrue(ch.find_commands(merged, query="show example local"))
        self.assertTrue(ch.find_commands(merged, query="show ip route"))
        self.assertTrue(ch.find_commands(merged, query="show version", machine="Ruckus Switch"))
        self.assertEqual(len({c["id"] for c in merged}), len(merged))

    def test_empty_categories_remain(self):
        shown = mc.machine_names([], mc.load_catalog(ROOT / "commands" / "machine_catalog.json"))
        self.assertIn("Nokia MSAG", shown)
        self.assertEqual(ch.find_commands([], machine="Nokia MSAG"), [])

if __name__ == "__main__":
    unittest.main()
