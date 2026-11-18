"""Non-GUI regressions for the compact slot confirmation and tray commands."""
import queue
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace

from pocket import quick_slot_dialog, quick_slots

APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                     run_name="test_import")
Desk = APP["PocketDesk"]


class QuickSlotDialogAndTrayTests(unittest.TestCase):
    def test_compact_replacement_preview_and_direction(self):
        values = quick_slot_dialog.confirmation_labels(
            2, "SVLAN 1557", "SVLAN 11")
        self.assertEqual(values["title"], "Replace Quick Slot [2]?")
        self.assertEqual(values["new"], "SVLAN 11")
        self.assertEqual(values["old"], "SVLAN 1557")
        long = quick_slot_dialog.confirmation_labels(3, "A" * 80, "שלום " * 20)
        self.assertLessEqual(len(long["old"]), quick_slots.REPLACEMENT_PREVIEW_LENGTH)
        self.assertLessEqual(len(long["new"]), quick_slots.REPLACEMENT_PREVIEW_LENGTH)

    def test_tray_menu_has_five_requested_actions_in_order(self):
        self.assertEqual(APP["TRAY_MENU_COMMANDS"], (
            (101, "Open Pocket", "show"),
            (102, "Open Settings", "tray_settings"),
            (103, "Create Backup", "tray_backup"),
            (104, "Restore Backup", "tray_restore"),
            (105, "Exit Pocket", "quit"),
        ))
        self.assertEqual(len({c[0] for c in APP["TRAY_MENU_COMMANDS"]}), 5)

    def test_tray_events_are_dispatched_to_existing_ui_actions(self):
        calls = []
        desk = SimpleNamespace(
            events=queue.Queue(),
            show=lambda xy=None: calls.append(("show", xy)),
            show_tab=lambda tab: calls.append(("tab", tab)),
            _open_backup_dialog=lambda: calls.append(("backup",)),
            _open_restore_dialog=lambda: calls.append(("restore",)),
        )
        for event in ("tray_settings", "tray_backup", "tray_restore"):
            desk.events.put((event, (100, 200)))
        Desk._poll_events(desk)
        self.assertEqual(calls, [
            ("show", (100, 200)), ("tab", "settings"),
            ("show", (100, 200)), ("backup",),
            ("show", (100, 200)), ("restore",),
        ])


if __name__ == "__main__":
    unittest.main()
