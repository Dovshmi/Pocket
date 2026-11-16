"""Regression checks for text editing and incremental OPEN-first port sorting."""
from pathlib import Path
import runpy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pocket import text_editing

APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                     run_name="pocket_input_tests")["PocketDesk"]


class FakeInput:
    def __init__(self, tag="Entry", *, state="normal", selected=True, value="Pocket"):
        self.tag, self.state, self.selected = tag, state, selected
        self.value, self.clipboard = value, ""
        self.actions = []
        self.bindings = {}

    def winfo_class(self):
        return self.tag

    def cget(self, key):
        return self.state if key == "state" else True

    def selection_present(self):
        return self.selected

    def tag_ranges(self, name):
        return (1, 2) if self.selected else ()

    def selection_range(self, first, last):
        self.actions.append(("select", first, last))

    def icursor(self, index):
        self.actions.append(("cursor", index))

    def tag_add(self, name, first, last):
        self.actions.append(("tag", name, first, last))

    def mark_set(self, name, value):
        self.actions.append(("mark", name, value))

    def see(self, index):
        self.actions.append(("see", index))

    def event_generate(self, virtual):
        self.actions.append(("event", virtual))

    def get(self, *args):
        return self.value

    def index(self, where):
        return {"sel.first": 0, "sel.last": len(self.value)}[where]

    def clipboard_clear(self):
        self.clipboard = ""
        self.actions.append(("clipboard_clear",))

    def clipboard_append(self, text):
        self.clipboard += text
        self.actions.append(("clipboard_append", text))

    def clipboard_get(self):
        return self.clipboard

    def delete(self, start, end):
        self.actions.append(("delete", start, end))
        self.value = ""
        self.selected = False

    def insert(self, index, value):
        self.actions.append(("insert", index, value))
        self.value += value

    def edit_separator(self):
        self.actions.append(("separator",))

    def edit_undo(self):
        self.actions.append(("undo",))

    def edit_redo(self):
        self.actions.append(("redo",))

    def bind(self, event):
        return self.bindings.get(event, "")


class FakeTree:
    def __init__(self):
        self.rows = []
        self.next_id = 0

    def get_children(self):
        return [row["id"] for row in self.rows]

    def set(self, iid, column):
        row = next(row for row in self.rows if row["id"] == iid)
        return str(row["values"][0 if column == "Port" else 2])

    def insert(self, parent, index, values):
        self.rows.insert(index, {"id": self.next_id, "values": values})
        self.next_id += 1

    def ports(self):
        return [row["values"][0] for row in self.rows]


class InputEditingTests(unittest.TestCase):
    def test_select_all_entries_and_multiline(self):
        entry, multiline = FakeInput(), FakeInput("Text")
        self.assertEqual(text_editing.select_all(entry), "break")
        self.assertEqual(entry.actions[0], ("select", 0, "end"))
        self.assertEqual(text_editing.select_all(multiline), "break")
        self.assertEqual(multiline.actions[0], ("tag", "sel", "1.0", "end-1c"))

    def test_keyboard_copy_cut_paste_and_readonly(self):
        entry = FakeInput()
        self.assertEqual(text_editing.perform(entry, "copy"), "break")
        self.assertEqual(entry.clipboard, "Pocket")
        self.assertEqual(text_editing.perform(entry, "cut"), "break")
        self.assertEqual(entry.value, "")
        self.assertEqual(text_editing.perform(entry, "paste"), "break")
        self.assertEqual(entry.value, "Pocket")
        self.assertNotIn(("event", "<<Copy>>"), entry.actions)
        self.assertNotIn(("event", "<<Paste>>"), entry.actions)

        readonly = FakeInput("TCombobox", state="readonly")
        text_editing.perform(readonly, "paste")
        text_editing.perform(readonly, "cut")
        self.assertEqual(readonly.actions, [])

    def test_text_undo_redo_and_clipboard_separators(self):
        editor = FakeInput("Text", selected=True)
        self.assertEqual(text_editing.perform(editor, "cut"), "break")
        self.assertEqual(editor.clipboard, "Pocket")
        self.assertEqual(editor.actions.count(("separator",)), 2)
        self.assertEqual(text_editing.perform(editor, "paste"), "break")
        self.assertEqual(editor.value, "Pocket")
        self.assertEqual(editor.actions.count(("separator",)), 4)
        text_editing.perform(editor, "undo")
        text_editing.perform(editor, "redo")
        self.assertIn(("undo",), editor.actions)
        self.assertIn(("redo",), editor.actions)

    def test_ctrl_accelerators_and_hebrew_windows_keys(self):
        widget = FakeInput()
        for keycode, action in ((65, "select_all"), (67, "copy"),
                                (86, "paste"), (88, "cut"),
                                (90, "undo"), (89, "redo")):
            with self.subTest(keycode=keycode), patch.object(text_editing.sys, "platform", "win32"):
                ev = SimpleNamespace(widget=widget, keycode=keycode,
                                     keysym="ג", state=0x0004)
                self.assertEqual(text_editing._shortcut_operation(ev), action)
        with patch.object(text_editing.sys, "platform", "win32"):
            ev = SimpleNamespace(widget=FakeInput("Text"), keycode=90,
                                 keysym="ז", state=0x0005)
            self.assertEqual(text_editing._shortcut_operation(ev), "redo")
            ev.state = 0x000C  # AltGr: Ctrl+Alt
            self.assertIsNone(text_editing._shortcut_operation(ev))
            ev.state = 0x0004
            ev.keycode = 75  # Ctrl+K stays Pocket's search
            self.assertIsNone(text_editing.handle_shortcut(ev))
        with patch.object(text_editing.sys, "platform", "linux"):
            ev = SimpleNamespace(widget=FakeInput(), keycode=54,
                                 keysym="c", state=0x0004)
            self.assertEqual(text_editing.handle_shortcut(ev), "break")
            self.assertEqual(ev.widget.clipboard, "Pocket")

    def test_install_keeps_widget_specific_context_menu(self):
        root = Mock()
        calls = []
        text_editing.install(root, lambda event: calls.append("fallback"),
                             lambda event: calls.append("focus"))
        patterns = {(call.args[0], call.args[1]): call.args[2]
                    for call in root.bind_class.call_args_list}
        for tag in text_editing.EDIT_CLASSES:
            self.assertIn((tag, "<Control-KeyPress>"), patterns)
            self.assertIn((tag, "<Control-KeyPress-c>"), patterns)
            self.assertIn((tag, "<Control-Shift-KeyPress-Z>"), patterns)
            self.assertIn((tag, "<Button-3>"), patterns)
        entry = FakeInput()
        right_click = patterns[("Entry", "<Button-3>")]
        entry.bindings["<Button-3>"] = "existing-custom-menu"
        right_click(SimpleNamespace(widget=entry))
        self.assertEqual(calls, [])
        entry.bindings.clear()
        right_click(SimpleNamespace(widget=entry))
        self.assertEqual(calls, ["fallback"])

    def test_open_ports_stay_first_during_incremental_results(self):
        tree = FakeTree()
        desk = SimpleNamespace(port_tree=tree)
        records = [(80, "TIMEOUT"), (22, "CLOSED"), (443, "OPEN"),
                   (53, "OPEN"), (8080, "TIMEOUT"), (21, "CLOSED")]
        for port, status in records:
            APP._add_port_result(desk, {"port": port, "status": status,
                                        "service": "tcp", "ms": 10})
        self.assertEqual(tree.ports(), [53, 443, 21, 22, 80, 8080])

    def test_existing_notes_rightclick_routes_remain(self):
        source = (Path(__file__).resolve().parents[1] / "app.pyw").read_text(encoding="utf-8")
        self.assertIn('self.note_body.bind("<Button-3>", self._show_note_context_menu)', source)
        self.assertIn('self.note_list.bind("<Button-3>", self._show_note_list_menu)', source)
        self.assertIn('self.mini_note_picker.bind("<Button-3>", self._show_mini_note_menu)', source)
        self.assertIn('text_editing.install(self.root, self._show_input_context_menu,', source)


if __name__ == "__main__":
    unittest.main()
