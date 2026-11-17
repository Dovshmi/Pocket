"""Pocket v1.39 Quick Slots: model, persistence and global key regressions."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import runpy
import tempfile
import unittest

from pocket import quick_slots, clipboard_gallery


APP = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "app.pyw"),
    run_name="quick_slot_tests")
Desk = APP["PocketDesk"]


class FakeSelectionBackend:
    def __init__(self, original="OLD", selection=None):
        self.clipboard = original
        self.selection = selection
        self.counter = 10
        self.restored = 0
        self.keys = []

    def foreground(self):
        return 100

    def wait_keys_up(self):
        return True

    @contextmanager
    def preserve_clipboard(self):
        original = self.clipboard
        def restore():
            self.clipboard = original
            self.restored += 1
        yield restore

    def read_text(self):
        return self.clipboard

    def sequence(self):
        return self.counter

    def send_key(self, key):
        self.keys.append(key)
        if key == "C" and self.selection is not None:
            self.clipboard = self.selection
            self.counter += 1

    def wait_for_sequence_change(self, baseline, timeout=0.5):
        return self.counter != baseline

    def put_text(self, value):
        self.clipboard = value
        self.counter += 1

    def pause_after_paste(self):
        pass


class QuickSlotsTests(unittest.TestCase):
    def test_nine_numbers_no_names_or_untrusted_values(self):
        self.assertEqual(quick_slots.normalize_slots(
            {"1": "10.0.0.1", "2": "AA:BB", "label": "IP",
             "10": "bad", "3": "", "4": "x" * 20_001}),
            {"1": "10.0.0.1", "2": "AA:BB"})
        self.assertEqual(quick_slots.normalize_slots(None), {})

    def test_slot_row_replaces_star_without_reflow(self):
        self.assertEqual(
            clipboard_gallery.text_row_label(
                {"slot": 1, "text": "10.0.0.1", "pinned": True}),
            "[1] 10.0.0.1")
        self.assertEqual(
            clipboard_gallery.text_row_label(
                {"text": "regular favorite", "pinned": True}),
            "★ regular favorite")

    def test_sort_slots_then_regular_pins_then_history_no_duplicates(self):
        history = [
            {"id": "a", "text": "ordinary", "pinned": False},
            {"id": "b", "text": "favorite", "pinned": True},
            {"id": "c", "text": "slot one", "pinned": True},
            {"id": "d", "text": "older ordinary", "pinned": False},
        ]
        slots = {"9": "slot nine", "1": "slot one"}
        rows = quick_slots.merged_rows(slots, history)
        self.assertEqual(
            [x["text"] for x in rows],
            ["slot one", "slot nine", "favorite", "ordinary", "older ordinary"])
        self.assertEqual([row["slot"] for row in rows[:2]], [1, 9])
        self.assertEqual(len(quick_slots.merged_rows(slots, history, "slot")), 2)
        self.assertEqual(history[2]["pinned"], True)  # View-only merge.

    def test_numlock_hardware_scan_and_no_bare_number_hotkeys(self):
        bindings = list(quick_slots.slot_hotkeys())
        self.assertEqual(len(bindings), 18)
        self.assertEqual(len({ident for ident, _, _ in bindings}), 18)
        for number in range(1, 10):
            paste = bindings[(number - 1) * 2]
            save = bindings[(number - 1) * 2 + 1]
            self.assertEqual(paste[2], 0x60 + number)
            self.assertEqual(save[2], paste[2])
            self.assertEqual(quick_slots.hotkey_action(paste[0]), ("paste", number))
            self.assertEqual(quick_slots.hotkey_action(save[0]), ("save", number))
            self.assertTrue(save[1] & quick_slots.MOD_SHIFT)
            self.assertFalse(paste[1] & quick_slots.MOD_SHIFT)

    def test_copy_current_selection_restores_previous_clipboard(self):
        fake = FakeSelectionBackend("PREVIOUS", "SELECTED")
        self.assertEqual(
            quick_slots.capture_selection_or_clipboard(
                target_hwnd=100, backend=fake),
            "SELECTED")
        self.assertEqual(fake.keys, ["C"])
        self.assertEqual(fake.restored, 1)
        self.assertEqual(fake.clipboard, "PREVIOUS")

    def test_no_selection_falls_back_to_current_clipboard(self):
        fake = FakeSelectionBackend("CURRENT", None)
        self.assertEqual(
            quick_slots.capture_selection_or_clipboard(
                target_hwnd=100, backend=fake),
            "CURRENT")
        self.assertEqual(fake.restored, 0)
        self.assertEqual(fake.clipboard, "CURRENT")
        no_text = FakeSelectionBackend(None, None)
        with self.assertRaises(Exception):
            quick_slots.capture_selection_or_clipboard(
                target_hwnd=100, backend=no_text)

    def test_paste_restores_original_clipboard(self):
        fake = FakeSelectionBackend("UNRELATED", None)
        quick_slots.paste_slot_text("SLOT TEXT", target_hwnd=100, backend=fake)
        self.assertEqual(fake.keys, ["V"])
        self.assertEqual(fake.restored, 1)
        self.assertEqual(fake.clipboard, "UNRELATED")

    def _app(self):
        events = []
        original = [
            {"id": "old", "text": "OLD", "pinned": True},
            {"id": "new", "text": "NEW", "pinned": True}
        ]
        desk = SimpleNamespace(
            clipboard_slots={"1": "OLD"},
            clipboard_items=original,
            settings={"clipboard_storage": "ram",
                      "clipboard_sensitive_filter": False},
            _clipboard_store_is_disk=lambda: False,
            _clipboard_write_text_view=lambda rows: original.__setitem__(slice(None), rows),
            _refresh_clipboard=lambda: events.append("refresh"),
            schedule_save=lambda: events.append("save"),
            _notify=lambda title, detail: events.append("notify"),
            root=Mock(),
        )
        return desk, events

    def test_replace_occupied_slot_requires_confirmation(self):
        desk, events = self._app()
        with patch.object(APP["messagebox"], "askyesno", return_value=False) as ask:
            self.assertFalse(Desk._assign_clipboard_slot(desk, 1, "NEW"))
        ask.assert_called_once()
        self.assertEqual(desk.clipboard_slots, {"1": "OLD"})
        self.assertEqual(events, [])

    def test_replace_unpins_promoted_favorite_no_ghost_favorite(self):
        desk, events = self._app()
        with patch.object(APP["messagebox"], "askyesno", return_value=True):
            self.assertTrue(Desk._assign_clipboard_slot(desk, 1, "NEW"))
        self.assertEqual(desk.clipboard_slots, {"1": "NEW"})
        self.assertFalse(desk.clipboard_items[1]["pinned"])
        self.assertFalse(desk.clipboard_items[0]["pinned"])
        self.assertEqual(events.count("save"), 1)
        self.assertEqual(quick_slots.merged_rows(desk.clipboard_slots, desk.clipboard_items)[0]["text"], "NEW")

    def test_new_profile_slot_persistence_does_not_modify_legacy_profiles(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            data = APP["default_data"]()
            self.assertEqual(data["clipboard_slots"], {})
            data["clipboard_slots"] = {"1": "10.1.1.1", "5": "AA:BB:CC"}
            APP["save_data"](path, data)
            result = APP["load_data"](path)
            self.assertEqual(result["clipboard_slots"], data["clipboard_slots"])
            self.assertEqual(result["notes"], data["notes"])
            self.assertEqual(result["links"], data["links"])


if __name__ == "__main__":
    unittest.main()
