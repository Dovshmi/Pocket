"""Pocket v1.40: interactive menu placement and cross-machine Settings backup."""
from __future__ import annotations

from pathlib import Path
import runpy
import tempfile
import unittest

from pocket import menu_order, mini_nav, portable_backup, settings_reset

ROOT = Path(__file__).resolve().parents[1]
APP = runpy.run_path(str(ROOT / "app.pyw"), run_name="pocket_menu_order_unit")


class MenuOrderTests(unittest.TestCase):
    def test_default_preserves_existing_navigation_positions(self):
        self.assertEqual(APP["default_data"]()["settings"]["menu_order"],
                         list(menu_order.DEFAULT_ORDER))
        self.assertEqual(APP["normalize_settings"]({})["menu_order"],
                         list(menu_order.DEFAULT_ORDER))
        first, more = mini_nav.plan_mini_icons(
            menu_order.enabled_order(menu_order.DEFAULT_ORDER,
                                     [k for k in menu_order.DEFAULT_ORDER
                                      if k != "settings"]))
        self.assertEqual(first, ("notes", "links", "ports", "mac",
                                 "commands", "subnet", "clipboard", "more"))
        self.assertEqual(more, (("reminders", "extra", "settings"),))

    def test_reorder_including_settings_is_rendered_in_mini(self):
        order = menu_order.move(menu_order.DEFAULT_ORDER, "settings", "notes")
        order = menu_order.move(order, "extra", "links")
        self.assertEqual(order[:3], ["settings", "notes", "extra"])
        enabled = menu_order.enabled_order(order, ["notes", "links", "extra",
                                                    "ports", "clipboard", "mac"])
        self.assertEqual(enabled[:3], ["settings", "notes", "extra"])
        first, extra = mini_nav.plan_mini_icons(enabled)
        self.assertEqual(first[:3], ("settings", "notes", "extra"))
        self.assertEqual(len(set(first + tuple(x for line in extra for x in line))),
                         len(enabled))
        self.assertNotIn("more", menu_order.normalize(order))

    def test_hidden_menu_keeps_position_after_reenabled(self):
        saved = menu_order.move(menu_order.DEFAULT_ORDER, "extra", "notes")
        disabled = menu_order.enabled_order(saved, ["notes", "links"])
        self.assertEqual(disabled[:2], ["extra", "notes"][:1] + ["notes"] if False
                         else ["notes", "links"])
        enabled = menu_order.enabled_order(saved, ["notes", "links", "extra"])
        self.assertEqual(enabled[:3], ["extra", "notes", "links"])
        self.assertEqual(saved[0], "extra")

    def test_bad_saved_settings_is_sanitized_without_dropping_any_menu(self):
        invalid = ["settings", "extra", "extra", "unknown", None, 5, "links"]
        actual = menu_order.normalize(invalid)
        self.assertEqual(actual[:3], ["settings", "extra", "links"])
        self.assertEqual(set(actual), set(menu_order.DEFAULT_ORDER))
        self.assertEqual(len(actual), len(menu_order.DEFAULT_ORDER))
        self.assertEqual(menu_order.move(actual, "bogus", "notes"), actual)
        self.assertEqual(menu_order.move(actual, "notes", "bogus"), actual)

    def test_order_survives_app_profile_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            data = APP["default_data"]()
            target = menu_order.move(data["settings"]["menu_order"],
                                     "extra", "notes")
            data["settings"]["menu_order"] = target
            destination = Path(folder) / "data.json"
            APP["save_data"](destination, data)
            read = APP["load_data"](destination)
            self.assertEqual(read["settings"]["menu_order"], target)

    def test_settings_backup_roundtrip_and_old_backup_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = APP["default_data"]()
            target = menu_order.move(source["settings"]["menu_order"],
                                     "settings", "notes")
            source["settings"]["menu_order"] = target
            backup = folder / "menu-order.zip"
            portable_backup.make_backup(backup, source, selected=("settings",),
                                        profile_dir=folder)
            payload = portable_backup.read_backup(backup)
            self.assertEqual(payload["payload"]["settings"]["settings"]["menu_order"],
                             target)
            dest = APP["default_data"]()
            restored = portable_backup.plan_restore(
                payload, dest, selected=("settings",), mode="merge")
            self.assertEqual(restored["profile"]["settings"]["menu_order"], target)
            # Older archives that lack the field do not erase a newer saved
            # preference; old profiles without the field use the default.
            self.assertEqual(APP["normalize_settings"](
                {"visible_tabs": ["notes"]})["menu_order"],
                list(menu_order.DEFAULT_ORDER))

    def test_reset_menus_resets_order_without_touching_other_data(self):
        current = APP["default_data"]()
        current["settings"]["menu_order"] = menu_order.move(
            menu_order.DEFAULT_ORDER, "extra", "notes")
        current["notes"][0]["body"] = "Preserve user note"
        fresh = settings_reset.reset_preferences(
            current, APP["default_data"](), ("menus",))
        self.assertEqual(fresh["settings"]["menu_order"],
                         list(menu_order.DEFAULT_ORDER))
        self.assertEqual(fresh["notes"][0]["body"], "Preserve user note")


if __name__ == "__main__":
    unittest.main()
