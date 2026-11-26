"""Clipboard right-click handoff to local Pocket tools (no implicit scans)."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from pocket import clipboard_routing


class ClipboardRoutingTests(unittest.TestCase):
    def test_exact_ip_routes_to_ports_and_subnet(self):
        self.assertEqual(
            clipboard_routing.destination_values(" 192.168.10.5 "),
            {"ports": "192.168.10.5",
             "subnet": ("192.168.10.5", None),
             "notes": "192.168.10.5"})
        self.assertEqual(
            clipboard_routing.destination_values("192.168.10.5/27"),
            {"subnet": ("192.168.10.5", "27"),
             "notes": "192.168.10.5/27"})
        self.assertEqual(
            clipboard_routing.destination_values("2001:db8::1"),
            {"ports": "2001:db8::1", "notes": "2001:db8::1"})

    def test_mac_is_normalized_and_does_not_trigger_ip_action(self):
        for raw in ("00:11:22:33:44:55", "0011.2233.4455", "001122334455"):
            with self.subTest(raw=raw):
                values = clipboard_routing.destination_values(raw)
                self.assertEqual(values["mac"], "00:11:22:33:44:55")
                self.assertNotIn("ports", values)
                self.assertNotIn("subnet", values)

    def test_unsupported_text_does_not_open_network_tools(self):
        for raw in ("show ip interface brief", "router 192.168.0.1",
                    "192.168.1.999", "255.255.255.0 extra",
                    "", "   "):
            values = clipboard_routing.destination_values(raw)
            self.assertNotIn("ports", values)
            self.assertNotIn("mac", values)
            self.assertNotIn("subnet", values)
        self.assertEqual(clipboard_routing.destination_values(" "), {})

    def fake_app(self, tabs=None):
        app = SimpleNamespace()
        app.settings = {"visible_tabs": tabs or ["notes", "ports", "mac", "subnet"]}
        app.host_var = SimpleNamespace(set=Mock())
        app.subnet_ip_var = SimpleNamespace(set=Mock())
        app.subnet_prefix_var = SimpleNamespace(set=Mock())
        app.data = {"notes": [], "active_note": None}
        app.mac_draft = ""
        app.show_tab = Mock()
        app.schedule_save = Mock()
        app._calculate_subnet = Mock()
        return app

    def test_ports_only_prefill_no_scan(self):
        app = self.fake_app()
        self.assertTrue(clipboard_routing.send_to_tool(app, "ports", " 10.0.0.12 "))
        app.show_tab.assert_called_once_with("ports")
        app.host_var.set.assert_called_once_with("10.0.0.12")
        app.schedule_save.assert_not_called()
        app._calculate_subnet.assert_not_called()

    def test_mac_only_prefill_no_lookup(self):
        app = self.fake_app()
        self.assertTrue(clipboard_routing.send_to_tool(app, "mac", "aa-bb-cc-dd-ee-ff"))
        self.assertEqual(app.mac_draft, "AA:BB:CC:DD:EE:FF")
        app.show_tab.assert_called_once_with("mac")

    def test_subnet_updates_prefix_and_calculates_locally(self):
        app = self.fake_app()
        self.assertTrue(clipboard_routing.send_to_tool(app, "subnet", "172.16.1.20/29"))
        app.show_tab.assert_called_once_with("subnet")
        app.subnet_ip_var.set.assert_called_once_with("172.16.1.20")
        app.subnet_prefix_var.set.assert_called_once_with("29")
        app._calculate_subnet.assert_called_once_with()
        app2 = self.fake_app()
        self.assertTrue(clipboard_routing.send_to_tool(app2, "subnet", "10.0.0.1"))
        app2.subnet_prefix_var.set.assert_not_called()

    def test_notes_create_new_record_without_overwriting_old(self):
        app = self.fake_app()
        existing = {"id": "original", "body": "Keep this"}
        app.data["notes"].append(existing)
        self.assertTrue(clipboard_routing.send_to_tool(app, "notes", "copied line"))
        self.assertEqual(app.data["notes"][1], existing)
        self.assertEqual(app.data["notes"][0]["body"], "copied line")
        self.assertEqual(app.data["active_note"], app.data["notes"][0]["id"])
        app.show_tab.assert_called_once_with("notes")
        app.schedule_save.assert_called_once_with()

    def test_hidden_tabs_and_invalid_targets_remain_unmodified(self):
        app = self.fake_app(tabs=["notes"])
        self.assertFalse(clipboard_routing.send_to_tool(app, "ports", "192.0.2.1"))
        self.assertFalse(clipboard_routing.send_to_tool(app, "subnet", "192.0.2.1/24"))
        self.assertFalse(clipboard_routing.send_to_tool(app, "mac", "00:11:22:33:44:55"))
        self.assertFalse(clipboard_routing.send_to_tool(app, "ports", "show ip route"))
        app.show_tab.assert_not_called()


class SmartClipboardTests(unittest.TestCase):
    def keys(self, value, enabled=("ports", "mac", "subnet", "extra", "notes")):
        return {item[0] for item in clipboard_routing.suggestions(value, enabled)}

    def test_ip_mac_and_cidr(self):
        self.assertEqual(self.keys("192.0.2.5"), {"ports", "subnet", "extra", "notes", "translate"})
        self.assertEqual(self.keys("2001:db8::1"), {"ports", "extra", "notes", "translate"})
        self.assertEqual(self.keys("0011.2233.4455"), {"mac", "extra", "notes", "translate"})
        self.assertEqual(self.keys("192.0.2.5/27"), {"subnet", "notes", "translate"})

    def test_phone_line_ports_and_url(self):
        for value in ("050-1234567", "+972501234567", "82-123456"):
            self.assertIn("extra", self.keys(value))
            self.assertNotIn("port_list", self.keys(value))
        self.assertIn("port_list", self.keys("80,443,2079-2084"))
        self.assertIn("port_list", self.keys("2079-2084"))
        self.assertIn("url", self.keys("https://example.test/path"))
        for value in ("javascript:alert(1)", "https://user:secret@example.test", "https://example.test:99999"):
            self.assertNotIn("url", self.keys(value))

    def test_hidden_tools_and_unstructured_text(self):
        self.assertEqual(self.keys("192.0.2.5", ("notes",)), {"notes", "translate"})
        self.assertEqual(self.keys("router 192.0.2.5\nshow config"), {"notes", "translate"})
        self.assertEqual(self.keys(""), set())

    def test_extra_dispatch_is_explicit(self):
        app = SimpleNamespace(settings={"visible_tabs": ["extra"]}, _run_palette_action=Mock())
        choice = next(i for i in clipboard_routing.suggestions("82-123456", ["extra"]) if i[0] == "extra")
        app._run_palette_action.assert_not_called()
        self.assertTrue(clipboard_routing.run_suggestion(app, choice))
        app._run_palette_action.assert_called_once_with(
            {"kind": "action", "id": "extra", "destination": "extra", "args": ("82-123456",)})
        app.settings["visible_tabs"] = []
        self.assertFalse(clipboard_routing.run_suggestion(app, choice))
        self.assertEqual(app._run_palette_action.call_count, 1)


if __name__ == "__main__":
    unittest.main()
