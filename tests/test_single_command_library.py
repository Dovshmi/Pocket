"""Single-library compatibility checks. Uses synthetic, non-private data."""
import json
import tempfile
import unittest
from pathlib import Path
from pocket import command_helper as ch

class SingleLibraryTests(unittest.TestCase):
    def test_machine_names_and_commands_share_one_json(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"commands.json"
            path.write_text(json.dumps({"machines":["Cisco","Nokia MSAG","Ruckus Switch"],
                "commands":[{"id":"a1","machine":"Cisco","category":"Routing",
                            "command":"show ip route","description":"Route lookup"}]}),encoding="utf-8")
            commands=ch.load_library(path)
            names=ch.machines_for(commands,ch.load_machine_names(path))
            self.assertEqual(len(commands),1)
            self.assertEqual(names,["Cisco","Nokia MSAG","Ruckus Switch"])
            self.assertTrue(ch.find_commands(commands,machine="Cisco",query="ip route"))
            self.assertEqual(ch.find_commands(commands,machine="Nokia MSAG"),[])

    def test_missing_and_invalid_library(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/"commands.json"
            self.assertEqual(ch.load_library(path),[])
            self.assertEqual(ch.load_machine_names(path),[])
            path.write_text("invalid-json",encoding="utf-8")
            self.assertEqual(ch.load_library(path),[])
            self.assertEqual(ch.load_machine_names(path),[])

if __name__=="__main__":
    unittest.main()
