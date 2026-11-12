"""Unified manual TCP port entry and additive quick-preset regression tests."""
import unittest

from pocket import port_presets as presets


class PortPresetTests(unittest.TestCase):
    def test_one_or_multiple_comma_separated_ports(self):
        self.assertEqual(presets.parse_manual_ports("443"), [443])
        self.assertEqual(presets.parse_manual_ports("22,80,443,3389"), [22, 80, 443, 3389])
        self.assertEqual(presets.parse_manual_ports(" 443, 22, 443,80, "), [443, 22, 80])
        self.assertEqual(presets.parse_manual_ports("", allow_empty=True), [])

    def test_limit_is_sixteen_unique_ports(self):
        self.assertEqual(len(presets.parse_manual_ports(",".join(map(str, range(1, 17))))), 16)
        with self.assertRaisesRegex(ValueError, "Maximum 16"):
            presets.parse_manual_ports(",".join(map(str, range(1, 18))))

    def test_invalid_entries_never_reach_scanner(self):
        for text in ("", "0", "65536", "22;80", "22 80", "22,,443",
                     "80-85", "abc", "22,80,broken", "22,-1", "22,443.0"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                presets.parse_manual_ports(text)

    def test_quick_selection_appends_without_replacing_manual_ports(self):
        self.assertEqual(presets.toggle_quick_port("7777,8888", 443), "7777,8888,443")
        self.assertEqual(presets.toggle_quick_port("22", 80), "22,80")
        self.assertEqual(presets.toggle_quick_port("", 3389), "3389")

    def test_selected_preset_removes_only_itself(self):
        self.assertEqual(presets.toggle_quick_port("7777,443,8888", 443), "7777,8888")
        self.assertEqual(presets.toggle_quick_port("22", 22), "")

    def test_duplicate_presets_do_not_duplicate_ports(self):
        self.assertEqual(presets.toggle_quick_port("443,22,443", 3389), "443,22,3389")
        self.assertEqual(presets.toggle_quick_port("443,22,443", 443), "22")

    def test_quick_selection_preserves_input_on_errors(self):
        raw = "22,not-a-port"
        with self.assertRaises(ValueError):
            presets.toggle_quick_port(raw, 443)
        full = ",".join(map(str, range(1, 17)))
        with self.assertRaisesRegex(ValueError, "Maximum 16"):
            presets.toggle_quick_port(full, 443)
        self.assertEqual(presets.toggle_quick_port(full, 16),
                         ",".join(map(str, range(1, 16))))

    def test_legacy_single_and_selected_are_migrated(self):
        self.assertEqual(presets.migrate_port_input({"mode": "single", "single_port": "443"}), "443")
        self.assertEqual(presets.migrate_port_input({
            "mode": "selected", "selected_ports": [443, 80, 443],
            "custom_ports": "8080, 8443-8444",
        }), "443,80,8080,8443,8444")
        self.assertEqual(presets.migrate_port_input({
            "ports_input": "22,443", "mode": "selected", "selected_ports": [80]
        }), "22,443")
        self.assertEqual(presets.migrate_port_input({"mode": "selected",
                                                     "selected_ports": [22],
                                                     "custom_ports": "bad"}), "22,bad")

    def test_extra_quick_ports_have_unique_tcp_numbers(self):
        nums = [number for number, _ in presets.QUICK_PORTS]
        self.assertGreaterEqual(len(nums), 28)
        self.assertEqual(len(nums), len(set(nums)))
        self.assertTrue(all(isinstance(number, int) and 1 <= number <= 65535
                            for number in nums))


if __name__ == "__main__":
    unittest.main()
