"""Smart Command Templates compatibility, validation and persistence tests."""
import tempfile
from pathlib import Path
import json
import unittest

from pocket import command_store as store
from pocket import smart_templates as smart


def make_record(command="execute ping x.x.x.x"):
    return {
        "id": "example123", "machine": "FortiGate", "category": "Diagnostics",
        "description": "Ping target", "command": command,
    }


class TemplateEngineTests(unittest.TestCase):
    def test_plain_commands_remain_plain(self):
        for command in ("show ip route", "show version", "write memory",
                        "show interfaces ge-0/0/1 extensive"):
            self.assertIsNone(smart.suggest_template(command))
            self.assertEqual(smart.template_state(make_record(command)), "plain")

    def test_suggestions_do_not_alter_source(self):
        texts = [
            "execute ping x.x.x.x",
            "show route table {VRF}.inet.0 {LAN}",
            "get route <IP>",
            "show interface [interface]",
            "show port x/x/x",
            "show mac-learning domain vlan vlan *svlan*",
        ]
        for command in texts:
            with self.subTest(command=command):
                suggested = smart.suggest_template(command)
                self.assertIsNotNone(suggested)
                self.assertEqual(suggested["source_command"], command)
                self.assertNotEqual(suggested["format"], command)
                self.assertEqual(smart.template_state(make_record(command)), "plain")

    def test_distinct_ips_and_explicit_reused_names(self):
        suggestion = smart.suggest_template("route x.x.x.x (start) x.x.x.x (end)")
        self.assertEqual(smart.field_names(suggestion["format"]), ["START_IP", "END_IP"])
        suggestion = smart.suggest_template("show route {VRF} and {VRF}")
        self.assertEqual(smart.field_names(suggestion["format"]), ["VRF"])

    def test_fields_from_manual_format(self):
        fields = smart.default_fields("interface {{IFACE}}\nset vlan {{VLAN_ID}}")
        self.assertEqual([f["name"] for f in fields], ["IFACE", "VLAN_ID"])
        self.assertEqual(fields[1]["type"], "vlan")

    def test_approve_render_and_no_implicit_execution(self):
        original = make_record("execute ping x.x.x.x")
        suggestion = smart.suggest_template(original["command"])
        original["template"] = smart.validate_template(suggestion, original["command"])
        self.assertEqual(smart.template_state(original), "configured")
        self.assertEqual(smart.render_template(original, {"IP": "192.0.2.10"}),
                         "execute ping 192.0.2.10")
        self.assertEqual(original["command"], "execute ping x.x.x.x")
        self.assertEqual(original["template"]["source_command"], original["command"])

    def test_type_validation_and_inputs(self):
        types = [
            ("ipv4", "203.0.113.9", True), ("ipv4", "999.1.2.3", False),
            ("ipv6", "2001:db8::1", True), ("ipv6", "203.0.113.1", False),
            ("cidr", "192.0.2.0/24", True), ("cidr", "2001:db8::/64", False),
            ("port", "443", True), ("port", "65536", False),
            ("vlan", "4094", True), ("vlan", "4095", False),
            ("interface", "ge-0/0/1.0", True), ("interface", "wan;reload", False),
            ("vrf", "customer_A", True), ("vrf", "x\nshutdown", False),
            ("mac", "aa:bb:cc:dd:ee:ff", True), ("mac", "gg:bb:cc:dd:ee:ff", False),
            ("text", "customer-1", True), ("text", "abc;rm -rf /", False),
        ]
        for kind, val, valid in types:
            with self.subTest(kind=kind, value=val):
                field = {"type": kind, "name": "VALUE"}
                if valid:
                    self.assertEqual(smart.validate_value(field, val), val)
                else:
                    with self.assertRaises(ValueError):
                        smart.validate_value(field, val)

    def test_unapproved_and_stale_templates_never_generate(self):
        record = make_record("ping x.x.x.x")
        with self.assertRaises(ValueError):
            smart.render_template(record, {"IP": "198.51.100.1"})
        record["template"] = smart.validate_template(
            smart.suggest_template(record["command"]), record["command"])
        record["command"] = "ping x.x.x.x source wan1"
        self.assertEqual(smart.template_state(record), "needs_review")
        with self.assertRaises(ValueError):
            smart.render_template(record, {"IP": "198.51.100.1"})

    def test_schema_rejects_unknown_fields_and_unclosed_markers(self):
        command = "show {{A}}"
        for obj in [
            {"format": "show {{A}}", "fields": []},
            {"format": "show {{A}} {{B}}", "fields": [{"name": "A", "label": "A", "type": "text"}]},
            {"format": "show {{A}", "fields": [{"name": "A", "label": "A", "type": "text"}]},
        ]:
            with self.subTest(obj=obj):
                with self.assertRaises(ValueError):
                    smart.validate_template(obj, command)

    def test_choice_validation(self):
        obj = {"format": "set status {{MODE}}",
               "fields": [{"name": "MODE", "label": "Mode", "type": "choice",
                           "options": ["enable", "disable"]}]}
        record = make_record("set internet-connection name disable / enable")
        record["template"] = smart.validate_template(obj, record["command"])
        self.assertEqual(smart.render_template(record, {"MODE": "enable"}),
                         "set status enable")
        with self.assertRaises(ValueError):
            smart.render_template(record, {"MODE": "reboot"})


class TemplateStorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "commands.json"
        self.record = make_record()
        self.path.write_text(json.dumps({"schema": 1, "commands": [self.record]},
                                        ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.folder.cleanup()

    def test_templates_are_opt_in_and_manual_backup_only(self):
        template = smart.suggest_template(self.record["command"])
        store.save_template(self.path, self.record, template)
        new = store.read_document(self.path)["commands"][0]
        self.assertEqual(new["command"], self.record["command"])
        self.assertEqual(smart.template_state(new), "configured")
        self.assertFalse((self.path.parent / "backups").exists())
        backup = store.create_backup(self.path)
        self.assertTrue(backup.is_file())
        self.assertEqual(store.read_document(backup)["commands"][0]["template"], new["template"])

    def test_remove_template_does_not_delete_original(self):
        store.save_template(self.path, self.record,
                            smart.suggest_template(self.record["command"]))
        updated = store.read_document(self.path)["commands"][0]
        store.save_template(self.path, updated, None)
        restored = store.read_document(self.path)["commands"][0]
        self.assertNotIn("template", restored)
        self.assertEqual(restored["command"], self.record["command"])

    def test_stale_edit_rejected_without_overwrite(self):
        store.save_template(self.path, self.record,
                            smart.suggest_template(self.record["command"]))
        with self.assertRaises(ValueError):
            store.save_template(self.path, self.record,
                                smart.suggest_template(self.record["command"]))

    def test_normal_command_edits_preserve_metadata_and_mark_stale(self):
        meta = smart.suggest_template(self.record["command"])
        store.save_template(self.path, self.record, meta)
        current = store.read_document(self.path)["commands"][0]
        edited = dict(current)
        edited["command"] = "execute ping 1.1.1.1"
        store.save_command(self.path, edited, original=current)
        changed = store.read_document(self.path)["commands"][0]
        self.assertEqual(smart.template_state(changed), "needs_review")
        self.assertEqual(changed["command"], "execute ping 1.1.1.1")


if __name__ == "__main__":
    unittest.main()
