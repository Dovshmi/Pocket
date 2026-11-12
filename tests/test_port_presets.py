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

    def test_service_labels_do_not_create_default_shortcuts(self):
        nums = [number for number, _ in presets.PORT_SERVICE_CATALOG]
        self.assertGreaterEqual(len(nums), 28)
        self.assertEqual(len(nums), len(set(nums)))
        self.assertEqual(presets.quick_ports([], []), [])
        self.assertEqual(presets.port_usage(443), "HTTPS")
        self.assertEqual(presets.port_usage(8291), "WinBox")
        self.assertEqual(presets.port_usage(49152), "Custom")

    def test_favorites_and_recent_are_one_list_without_fixed_ports(self):
        # Starred ports appear first; temporary ports follow with no duplicates.
        self.assertEqual(presets.quick_ports([9000, 22], [22, 8080, 3389]),
                         [9000, 22, 8080, 3389])
        self.assertEqual(presets.quick_ports([9000, 22], [3389, 443]),
                         [9000, 22, 3389, 443])
        self.assertNotIn(8080, presets.quick_ports([9000, 22], [3389, 443]))
        self.assertNotIn(80, presets.quick_ports([], [3389]))

    def test_starring_and_unstarring_preserves_recent_ports(self):
        starred = presets.toggle_favorite([22], 9000)
        self.assertEqual(starred, [22, 9000])
        self.assertEqual(presets.quick_ports(starred, [3389, 9000]),
                         [22, 9000, 3389])
        unstarred = presets.toggle_favorite(starred, 9000)
        self.assertEqual(unstarred, [22])
        self.assertEqual(presets.quick_ports(unstarred, [3389, 9000]),
                         [22, 3389, 9000])
        self.assertEqual(presets.quick_ports(unstarred, [3389]), [22, 3389])

    def test_favorites_validate_persistent_profile_data(self):
        raw = [443, 22, 443, None, True, False, 0, 65536, "80", 9000]
        self.assertEqual(presets.normalize_favorites(raw), [443, 22, 9000])
        self.assertEqual(presets.normalize_favorites({}), [])
        with self.assertRaises(ValueError):
            presets.toggle_favorite([22], 0)
        with self.assertRaises(ValueError):
            presets.toggle_favorite(list(range(1, presets.MAX_FAVORITES + 1)), 443)


if __name__ == "__main__":
    unittest.main()
