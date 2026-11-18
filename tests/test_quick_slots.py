"""Pocket v1.39 Quick Slots: model, persistence and global key regressions."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import runpy
import tempfile
import unittest

from pocket import quick_slots, clipboard_gallery
from pocket.marked_layout import MarkError


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
        self.settled = 0
        self.snapshot_fails = False
        self.typed_text = []

    def foreground(self):
        return 100

    def wait_keys_up(self):
        return True

    @contextmanager
    def preserve_clipboard(self):
        if self.snapshot_fails:
            raise MarkError("OleGetClipboard failed before clipboard access")
        original = self.clipboard
        def restore():
            self.clipboard = original
            self.restored += 1
        yield restore

    def settle_hotkey_release(self):
        self.settled += 1

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

    def send_text(self, value, *, target_hwnd=None):
        self.keys.append("TEXT")
        self.typed_text.append(value)

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

    def test_two_direct_prefixes_with_fixed_numpad_and_no_shift(self):
        self.assertEqual(quick_slots.normalize_prefix(None), "ctrl_alt")
        self.assertEqual(quick_slots.normalize_prefix(
            None, default=quick_slots.DEFAULT_COPY_PREFIX), "ctrl_alt_win")
        self.assertTrue(quick_slots.distinct_prefixes("ctrl_alt", "ctrl_win"))
        self.assertFalse(quick_slots.distinct_prefixes("ctrl_alt", "ctrl_alt"))
        bindings = list(quick_slots.slot_hotkeys())
        self.assertEqual(len(bindings), 18)
        self.assertEqual(len({item[0] for item in bindings}), 18)
        for number in range(1, 10):
            paste, save = bindings[(number-1)*2:(number-1)*2+2]
            self.assertEqual(paste[2], 0x60 + number)
            self.assertEqual(save[2], paste[2])
            self.assertEqual(paste[1], quick_slots.modifier_flags("ctrl_alt"))
            self.assertEqual(save[1], quick_slots.modifier_flags("ctrl_alt_win"))
            self.assertFalse((paste[1] | save[1]) & quick_slots.MOD_SHIFT)
            self.assertEqual(quick_slots.hotkey_action(paste[0]), ("paste", number))
            self.assertEqual(quick_slots.hotkey_action(save[0]), ("save", number))
        self.assertIsNone(quick_slots.hotkey_action(quick_slots.PASTE_HOTKEY_BASE + 9))
        self.assertIsNone(quick_slots.hotkey_action(quick_slots.SAVE_HOTKEY_BASE + 9))
        with self.assertRaises(ValueError):
            list(quick_slots.slot_hotkeys("ctrl", "ctrl"))

    def test_register_hotkeys_and_group_swaps_are_atomic(self):
        called = []
        def register(hwnd, ident, mods, key):
            called.append(ident)
            return len(called) < 5
        unregister = Mock()
        result = quick_slots.register_all(register, unregister, 42, "ctrl_alt", "ctrl_win")
        self.assertEqual(result, set())
        self.assertEqual({x.args[1] for x in unregister.call_args_list},
                         set(called[:4]))
        unregister.reset_mock()
        self.assertEqual(len(quick_slots.register_all(
            lambda *_: True, unregister, 42, "ctrl_alt", "ctrl_win")), 18)
        self.assertEqual(len(quick_slots.register_group(
            lambda *_: True, unregister, 42, "save", "ctrl_win",
            base=quick_slots.SAVE_HOTKEY_BASE)), 9)
        self.assertFalse(quick_slots.register_all(
            lambda *_: True, unregister, 42, "ctrl_win", "ctrl_win"))
        unregister.assert_not_called()

    def test_direct_save_and_paste_hotkeys_share_slots_without_modes(self):
        desk = object.__new__(Desk)
        desk.settings = {"quick_slots_enabled": True,
                         "quick_slots_paste_prefix": "ctrl_alt",
                         "quick_slots_copy_prefix": "ctrl_win"}
        desk.clipboard_slots = {"1": "STORED"}
        desk._mark_active = False
        desk.root = Mock()
        desk._notify = Mock()
        desk.events = Mock()
        with patch.object(APP["threading"], "Thread") as thread:
            Desk._quick_slot_hotkey(desk, "save", 1, 100)
            thread.assert_called_once()
            thread.reset_mock()
            desk._mark_active = False
            Desk._quick_slot_hotkey(desk, "paste", 1, 100)
            thread.assert_called_once()
            thread.reset_mock()
            desk._mark_active = False
            Desk._quick_slot_hotkey(desk, "mode", 0, 100)
            thread.assert_not_called()

    def test_disable_quick_slots_preserves_saved_values(self):
        desk = object.__new__(Desk)
        desk.settings = {"quick_slots_enabled": True,
                         "quick_slots_paste_prefix": "ctrl_alt",
                         "quick_slots_copy_prefix": "ctrl_win"}
        desk.clipboard_slots = {"1": "IP VALUE"}
        desk.root = Mock()
        desk.tray = None
        desk.current_tab = "notes"
        desk.schedule_save = Mock()
        Desk._set_quick_slots_enabled(desk, False)
        self.assertFalse(desk.settings["quick_slots_enabled"])
        self.assertEqual(desk.clipboard_slots, {"1": "IP VALUE"})
        desk.schedule_save.assert_called_once()
        Desk._set_quick_slots_copy_prefix(desk, "ctrl_alt_win")
        self.assertEqual(desk.settings["quick_slots_copy_prefix"], "ctrl_alt_win")
        Desk._set_quick_slots_paste_prefix(desk, "ctrl")
        self.assertEqual(desk.settings["quick_slots_paste_prefix"], "ctrl")

    def test_use_existing_clipboard_without_sending_ctrl_c(self):
        backend = FakeSelectionBackend("שלום 123", "SHOULD NOT CAPTURE")
        backend.send_key = Mock(side_effect=AssertionError("Never send Ctrl+C"))
        self.assertEqual(quick_slots.read_existing_clipboard(backend=backend),
                         "שלום 123")
        self.assertEqual(backend.clipboard, "שלום 123")
        backend.send_key.assert_not_called()
        self.assertEqual(backend.restored, 0)
        with self.assertRaisesRegex(MarkError, "copy text with Ctrl\\+C first"):
            quick_slots.read_existing_clipboard(
                backend=FakeSelectionBackend(None))
        with self.assertRaisesRegex(MarkError, "copy text with Ctrl\\+C first"):
            quick_slots.read_existing_clipboard(
                backend=FakeSelectionBackend("   "))

    def test_copy_selected_text_into_slot_and_windows_clipboard(self):
        fake = FakeSelectionBackend("PREVIOUS", "SELECTED")
        self.assertEqual(
            quick_slots.capture_selection_or_clipboard(
                target_hwnd=100, backend=fake),
            "SELECTED")
        self.assertEqual(fake.keys, ["C"])
        self.assertEqual(fake.restored, 0)
        self.assertEqual(fake.clipboard, "SELECTED")
        self.assertEqual(fake.settled, 1)

    def test_no_selection_falls_back_to_current_clipboard(self):
        fake = FakeSelectionBackend("CURRENT", None)
        self.assertEqual(
            quick_slots.capture_selection_or_clipboard(
                target_hwnd=100, backend=fake),
            "CURRENT")
        self.assertEqual(fake.restored, 0)
        self.assertEqual(fake.clipboard, "CURRENT")
        self.assertEqual(fake.settled, 1)
        no_text = FakeSelectionBackend(None, None)
        with self.assertRaises(Exception):
            quick_slots.capture_selection_or_clipboard(
                target_hwnd=100, backend=no_text)

    def test_copy_selection_does_not_require_ole_snapshot(self):
        backend = FakeSelectionBackend("BEFORE", "AFTER")
        def impossible_snapshot():
            raise AssertionError("Copy must not depend on OLE clipboard snapshot")
        backend.preserve_clipboard = impossible_snapshot
        self.assertEqual(quick_slots.capture_selection_or_clipboard(
            target_hwnd=100, backend=backend), "AFTER")
        self.assertEqual(backend.clipboard, "AFTER")

    def test_unusable_selected_text_does_not_silently_save_old_clipboard(self):
        backend = FakeSelectionBackend("BEFORE", "  ")
        with self.assertRaisesRegex(Exception, "not usable text"):
            quick_slots.capture_selection_or_clipboard(
                target_hwnd=100, backend=backend)
        self.assertEqual(backend.clipboard, "  ")

    def test_auto_paste_types_without_ever_opening_clipboard(self):
        fake = FakeSelectionBackend("UNRELATED", None)
        fake.preserve_clipboard = Mock(side_effect=AssertionError("OLE is forbidden"))
        fake.put_text = Mock(side_effect=AssertionError("Clipboard write is forbidden"))
        quick_slots.paste_slot_text("SLOT TEXT", target_hwnd=100, backend=fake)
        self.assertEqual(fake.keys, ["TEXT"])
        self.assertEqual(fake.typed_text, ["SLOT TEXT"])
        self.assertEqual(fake.restored, 0)
        self.assertEqual(fake.clipboard, "UNRELATED")
        fake.preserve_clipboard.assert_not_called()
        fake.put_text.assert_not_called()

    def test_non_ascii_auto_paste_uses_unicode_clipboard_and_normal_ctrl_v(self):
        for value in ("שלום עולם", "עברית 123 English", "café", "مرحبا", "日本語", "🙂"):
            with self.subTest(value=value):
                self.assertTrue(quick_slots.requires_clipboard_paste(value))
                backend = FakeSelectionBackend("OLD", None)
                backend.preserve_clipboard = Mock(
                    side_effect=AssertionError("OLE must never run"))
                backend.send_text = Mock(
                    side_effect=AssertionError("Unicode SendInput must not run"))
                quick_slots.paste_slot_text(value, target_hwnd=100, backend=backend)
                self.assertEqual(backend.clipboard, value)
                self.assertEqual(backend.keys, ["V"])
                self.assertEqual(backend.restored, 0)
                backend.preserve_clipboard.assert_not_called()
                backend.send_text.assert_not_called()

    def test_ascii_uses_non_clipboard_path_even_with_numbers_and_newlines(self):
        for value in ("hostname-123", "192.168.0.1", "Line1\\nLine2"):
            with self.subTest(value=value):
                self.assertFalse(quick_slots.requires_clipboard_paste(value))
                backend = FakeSelectionBackend("PREVIOUS", None)
                quick_slots.paste_slot_text(value, target_hwnd=100, backend=backend)
                self.assertEqual(backend.typed_text, [value])
                self.assertEqual(backend.clipboard, "PREVIOUS")
                self.assertEqual(backend.keys, ["TEXT"])

    def test_clipboard_only_mode_uses_normal_windows_copy_semantics(self):
        self.assertEqual(quick_slots.normalize_paste_mode(None), "auto")
        self.assertEqual(quick_slots.normalize_paste_mode("unknown"), "auto")
        self.assertEqual(quick_slots.normalize_paste_mode("clipboard"), "clipboard")
        backend = FakeSelectionBackend("OLD", None)
        backend.preserve_clipboard = Mock(side_effect=AssertionError(
            "Clipboard-only must not call OLE"))
        quick_slots.copy_slot_to_clipboard("NEW", backend=backend)
        self.assertEqual(backend.clipboard, "NEW")
        self.assertEqual(backend.keys, [])
        self.assertEqual(backend.restored, 0)
        self.assertEqual(backend.settled, 1)

    def test_auto_paste_unaffected_by_ole_snapshot_failures(self):
        backend = FakeSelectionBackend("EXISTING_IMAGE_OR_TEXT", None)
        backend.snapshot_fails = True
        quick_slots.paste_slot_text("INSERTED", target_hwnd=100, backend=backend)
        self.assertEqual(backend.clipboard, "EXISTING_IMAGE_OR_TEXT")
        self.assertEqual(backend.typed_text, ["INSERTED"])
        self.assertEqual(backend.keys, ["TEXT"])
        self.assertEqual(backend.restored, 0)

    def test_auto_paste_rejects_blocked_unicode_input_without_clipboard_changes(self):
        backend = FakeSelectionBackend("EXISTING", None)
        def blocked_input(_text, **kwargs):
            raise MarkError("Windows blocked direct input")
        backend.send_text = blocked_input
        with self.assertRaisesRegex(MarkError, "blocked"):
            quick_slots.paste_slot_text("INSERTED", target_hwnd=100, backend=backend)
        self.assertEqual(backend.keys, [])
        self.assertEqual(backend.clipboard, "EXISTING")

    def test_new_mode_setting_is_persistent_and_validated(self):
        data = APP["default_data"]()
        self.assertEqual(data["settings"]["quick_slots_save_mode"], "selection")
        self.assertEqual(quick_slots.normalize_save_mode(None), "selection")
        self.assertEqual(quick_slots.normalize_save_mode("invalid"), "selection")
        self.assertEqual(quick_slots.normalize_save_mode("clipboard"), "clipboard")
        self.assertEqual(APP["normalize_settings"]({})["quick_slots_save_mode"],
                         "selection")
        self.assertEqual(APP["normalize_settings"](
            {"quick_slots_save_mode": "clipboard"})["quick_slots_save_mode"],
            "clipboard")
        self.assertEqual(data["settings"]["quick_slots_paste_mode"], "auto")
        self.assertEqual(APP["normalize_settings"]({})["quick_slots_paste_mode"], "auto")
        self.assertEqual(APP["normalize_settings"](
            {"quick_slots_paste_mode": "clipboard"})["quick_slots_paste_mode"],
            "clipboard")
        self.assertEqual(APP["normalize_settings"](
            {"quick_slots_paste_mode": "invalid"})["quick_slots_paste_mode"],
            "auto")
        desk = object.__new__(Desk)
        desk.settings = APP["normalize_settings"]({})
        desk.schedule_save = Mock()
        desk.current_tab = "notes"
        Desk._set_quick_slots_paste_mode(desk, "clipboard")
        self.assertEqual(desk.settings["quick_slots_paste_mode"], "clipboard")
        desk.schedule_save.assert_called_once()
        Desk._set_quick_slots_save_mode(desk, "clipboard")
        self.assertEqual(desk.settings["quick_slots_save_mode"], "clipboard")
        self.assertEqual(desk.settings["quick_slots_paste_mode"], "clipboard")
        self.assertEqual(desk.schedule_save.call_count, 2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "profile.json"
            data["settings"] = desk.settings
            APP["save_data"](path, data)
            restored = APP["load_data"](path)
            self.assertEqual(restored["settings"]["quick_slots_save_mode"],
                             "clipboard")
            self.assertEqual(restored["settings"]["quick_slots_paste_mode"],
                             "clipboard")

    def test_slot_hotkey_manual_mode_routes_to_clipboard_not_paste(self):
        desk = object.__new__(Desk)
        desk.settings = {"quick_slots_enabled": True,
                         "quick_slots_paste_mode": "clipboard"}
        desk.clipboard_slots = {"1": "SLOT DATA"}
        desk._mark_active = False
        desk.root = Mock()
        desk.events = Mock()
        desk._notify = Mock()
        class ImmediateThread:
            def __init__(self, *, target, **_kwargs):
                self.target = target
            def start(self):
                self.target()
        with patch.object(APP["threading"], "Thread", ImmediateThread), \
             patch.object(quick_slots, "copy_slot_to_clipboard") as copied, \
             patch.object(quick_slots, "paste_slot_text") as pasted:
            Desk._quick_slot_hotkey(desk, "paste", 1, 100)
        copied.assert_called_once()
        pasted.assert_not_called()
        desk.events.put.assert_called_once_with(
            ("quick_slot_paste_result", (1, "SLOT DATA", None, "clipboard")))

    def test_independent_save_and_paste_hotkey_combinations(self):
        class ImmediateThread:
            def __init__(self, *, target, **_kwargs):
                self.target = target
            def start(self):
                self.target()
        for save_mode in ("selection", "clipboard"):
            for paste_mode in ("auto", "clipboard"):
                with self.subTest(save=save_mode, paste=paste_mode):
                    desk = object.__new__(Desk)
                    desk.settings = {
                        "quick_slots_enabled": True,
                        "quick_slots_save_mode": save_mode,
                        "quick_slots_paste_mode": paste_mode,
                    }
                    desk.clipboard_slots = {"1": "STORED"}
                    desk._mark_active = False
                    desk.root = Mock()
                    desk.events = Mock()
                    desk._notify = Mock()
                    with patch.object(APP["threading"], "Thread", ImmediateThread), \
                         patch.object(quick_slots, "capture_selection_or_clipboard",
                                      return_value="AUTO SELECTED") as selection, \
                         patch.object(quick_slots, "read_existing_clipboard",
                                      return_value="EXISTING CLIPBOARD") as current, \
                         patch.object(quick_slots, "paste_slot_text") as pasted, \
                         patch.object(quick_slots, "copy_slot_to_clipboard") as staged:
                        Desk._quick_slot_hotkey(desk, "save", 1, 100)
                        if save_mode == "selection":
                            selection.assert_called_once()
                            current.assert_not_called()
                            desk.events.put.assert_called_with(
                                ("quick_slot_save_result", (1, "AUTO SELECTED", None)))
                        else:
                            current.assert_called_once()
                            selection.assert_not_called()
                            desk.events.put.assert_called_with(
                                ("quick_slot_save_result",
                                 (1, "EXISTING CLIPBOARD", None)))
                        desk._mark_active = False
                        Desk._quick_slot_hotkey(desk, "paste", 1, 100)
                        if paste_mode == "auto":
                            pasted.assert_called_once()
                            staged.assert_not_called()
                        else:
                            staged.assert_called_once()
                            pasted.assert_not_called()
                        desk.events.put.assert_called_with(
                            ("quick_slot_paste_result", (1, "STORED", None, paste_mode)))

    def _app(self):
        events = []
        original = [
            {"id": "old", "text": "OLD", "pinned": True},
            {"id": "new", "text": "NEW", "pinned": True}
        ]
        desk = SimpleNamespace(
            clipboard_slots={"1": "OLD"},
            clipboard_items=original,
            theme="blue",
            settings={"clipboard_storage": "ram",
                      "clipboard_sensitive_filter": False},
            _clipboard_store_is_disk=lambda: False,
            _clipboard_write_text_view=lambda rows: original.__setitem__(slice(None), rows),
            _refresh_clipboard=lambda: events.append("refresh"),
            schedule_save=lambda: events.append("save"),
            _notify=lambda title, detail: events.append("notify"),
            _notify_quick_slot=lambda action, title, detail: events.append("notify"),
            root=Mock(),
        )
        return desk, events

    def test_replace_occupied_slot_requires_confirmation(self):
        desk, events = self._app()
        with patch.object(APP["quick_slot_dialog"], "confirm_replace", return_value=False) as ask:
            self.assertFalse(Desk._assign_clipboard_slot(desk, 1, "NEW"))
        ask.assert_called_once()
        self.assertEqual(desk.clipboard_slots, {"1": "OLD"})
        self.assertEqual(events, [])

    def test_replace_unpins_promoted_favorite_no_ghost_favorite(self):
        desk, events = self._app()
        with patch.object(APP["quick_slot_dialog"], "confirm_replace", return_value=True):
            self.assertTrue(Desk._assign_clipboard_slot(desk, 1, "NEW"))
        self.assertEqual(desk.clipboard_slots, {"1": "NEW"})
        self.assertFalse(desk.clipboard_items[1]["pinned"])
        self.assertFalse(desk.clipboard_items[0]["pinned"])
        self.assertEqual(events.count("save"), 1)
        self.assertEqual(quick_slots.merged_rows(desk.clipboard_slots, desk.clipboard_items)[0]["text"], "NEW")

    def test_replace_unseen_slot_text_becomes_unpinned_ram_history(self):
        desk, events = self._app()
        desk.clipboard_items[:] = []
        with patch.object(APP["quick_slot_dialog"], "confirm_replace", return_value=True):
            self.assertTrue(Desk._assign_clipboard_slot(desk, 1, "NEW"))
        self.assertEqual(desk.clipboard_slots["1"], "NEW")
        self.assertEqual([r["text"] for r in desk.clipboard_items], ["OLD"])
        self.assertIs(desk.clipboard_items[0]["pinned"], False)
        self.assertEqual(events.count("save"), 1)

    def test_replace_history_write_failure_leaves_slot_unchanged(self):
        desk, events = self._app()
        desk.clipboard_items[:] = []
        desk._clipboard_write_text_view = Mock(side_effect=OSError("disk full"))
        desk._clipboard_report_io_error = Mock()
        with patch.object(APP["quick_slot_dialog"], "confirm_replace", return_value=True):
            self.assertFalse(Desk._assign_clipboard_slot(desk, 1, "NEW"))
        self.assertEqual(desk.clipboard_slots["1"], "OLD")
        self.assertEqual(events.count("save"), 0)

    def test_replace_unseen_slot_text_is_saved_to_database(self):
        from pocket import clipboard_database as clipdb
        with tempfile.TemporaryDirectory() as folder:
            db = clipdb.ClipboardDatabase(folder)
            desk, events = self._app()
            desk.settings["clipboard_storage"] = "database"
            desk.settings["clipboard_autodelete_days"] = 0
            desk.clipboard_database = db
            desk._clipboard_view_days = {"text": clipdb.today(), "images": clipdb.today()}
            desk._clipboard_page_index = {"text": 0, "images": 0}
            desk._clipboard_store_is_disk = lambda: True
            desk._clipboard_load_day = Mock()
            with patch.object(APP["quick_slot_dialog"], "confirm_replace", return_value=True):
                self.assertTrue(Desk._assign_clipboard_slot(desk, 1, "NEW"))
            rows = db.load_text(clipdb.today())
            self.assertEqual([r["text"] for r in rows], ["OLD"])
            self.assertIs(rows[0]["pinned"], False)
            self.assertEqual(desk.clipboard_slots["1"], "NEW")
            desk._clipboard_load_day.assert_called_once()

    def test_replacement_history_reuses_old_entry_without_duplicates(self):
        records = [
            {"id": "a" * 32, "text": "OLD", "time": "12:00", "pinned": True},
            {"id": "b" * 32, "text": "NEW", "time": "12:01", "pinned": True},
        ]
        new_record = {"id": "c" * 32, "text": "OLD", "time": "12:02",
                      "pinned": False}
        output, changed = quick_slots.replacement_history_rows(
            records, "OLD", "NEW", new_record=new_record)
        self.assertTrue(changed)
        self.assertEqual(len(output), 2)
        self.assertFalse(any(row["pinned"] for row in output))
        self.assertTrue(all(row["pinned"] for row in records))
        again, changed = quick_slots.replacement_history_rows(
            output, "OLD", "NEW", new_record=new_record)
        self.assertFalse(changed)
        self.assertEqual(again, output)

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
