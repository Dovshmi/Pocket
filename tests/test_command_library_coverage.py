"""Regression checks for Pocket's public, copy-only command catalogue."""
import unittest
import re
from pathlib import Path
import command_helper as ch
import network_tools as net

ROOT = Path(__file__).resolve().parents[1]

class PublicLibraryCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.commands = ch.load_library(ROOT / "commands" / "sample_commands.json")

    def test_large_valid_reference_with_unique_ids_and_commands(self):
        self.assertGreaterEqual(len(self.commands), 100)
        self.assertEqual(len({c["id"] for c in self.commands}), len(self.commands))
        self.assertEqual(len({(c["machine"], c["command"]) for c in self.commands}), len(self.commands))
        for machine in ("Cisco", "FortiGate", "Juniper", "Nokia SR OS"):
            self.assertGreaterEqual(sum(c["machine"] == machine for c in self.commands), 15)

    def test_search_for_key_network_areas(self):
        for machine, query in (
            ("Cisco", "ospf neighbor"), ("Cisco", "etherchannel"),
            ("Cisco", "ip dhcp binding"), ("FortiGate", "sd-wan"),
            ("FortiGate", "vpn ipsec tunnel"), ("Juniper", "show bgp summary"),
            ("Juniper", "ethernet-switching"), ("Nokia SR OS", "service")
        ):
            with self.subTest(machine=machine, query=query):
                found = ch.find_commands(self.commands, query=query, machine=machine)
                self.assertTrue(found, (machine, query))

    def test_no_private_values_embedded(self):
        forbidden = re.compile(r"password|passwd|secret|bearer|api.?key|credential|token|סיסמ|סיסמא", re.I)
        ip = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])")
        for entry in self.commands:
            with self.subTest(entry=entry["id"]):
                value = entry["description"] + " " + entry["command"]
                self.assertNotRegex(value, forbidden)
                self.assertNotRegex(value, ip)
                self.assertNotRegex(value, r"https?://\S+|[\w.-]+@[\w.-]+")

    def test_empty_port_list_does_not_crash_worker(self):
        self.assertEqual(list(net.scan_tcp_ports("127.0.0.1", [])), [])

if __name__ == "__main__":
    unittest.main()
