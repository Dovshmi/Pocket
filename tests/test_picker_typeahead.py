"""Keyboard navigation keeps existing Pocket readonly dropdowns unchanged."""
import unittest
from types import SimpleNamespace

from pocket import clipboard_gallery
from pocket import picker_typeahead


class FakePicker:
    def __init__(self, values, current=0):
        self.values = tuple(values)
        self.index = current
        self.bindings = {}
        self.events = []
        self.tk = SimpleNamespace(splitlist=lambda text: tuple(text.split()))

    def __getitem__(self, key):
        assert key == "values"
        return self.values

    def bind(self, sequence, callback, add=None):
        self.bindings[sequence] = callback
        return "binding"

    def current(self, index=None):
        if index is None:
            return self.index
        self.index = index

    def event_generate(self, name):
        self.events.append(name)


class PickerTypeaheadTests(unittest.TestCase):
    def test_casefold_prefix_then_contains_search_keeps_all_options(self):
        options = ("All machines", "Cisco", "Juniper", "Fortinet")
        self.assertEqual(picker_typeahead.find_match(options, "Ju"), 2)
        self.assertEqual(picker_typeahead.find_match(options, "tine"), 3)
        self.assertEqual(picker_typeahead.find_match(options, "not-found"), -1)
        self.assertEqual(picker_typeahead.find_match(["★ סיכום", "בדיקה"], "סיכ"), 0)
        self.assertEqual(picker_typeahead.find_match(["אביב", "תל אביב"], "תל"), 1)

    def test_typing_letters_selects_existing_machine_without_filtering(self):
        clock = [0.0]
        picker = FakePicker(["All machines", "Cisco", "Juniper", "Junos", "Fortinet"])
        picker_typeahead.install(picker, time_source=lambda: clock[0])
        def key(char, keysym=None, state=0):
            return picker._pocket_typeahead(SimpleNamespace(
                char=char, keysym=keysym or char, state=state))
        for char in "juni":
            self.assertEqual(key(char), "break")
            clock[0] += .12
        self.assertEqual(picker.index, 2)
        self.assertEqual(len(picker.values), 5)
        self.assertEqual(picker.events, ["<<ComboboxSelected>>"])
        self.assertIsNone(key("k", state=0x0004))  # Ctrl+K remains Pocket's
        self.assertEqual(len(picker.values), 5)

    def test_new_phrase_timeout_backspace_and_repeated_key_cycle(self):
        clock = [0.0]
        picker = FakePicker(["All", "Cisco", "Citrix", "Juniper"])
        picker_typeahead.install(picker, time_source=lambda: clock[0])
        def key(char="", keysym="", state=0):
            return picker._pocket_typeahead(SimpleNamespace(
                char=char, keysym=keysym or char, state=state))
        key("c")
        self.assertEqual(picker.index, 1)
        clock[0] += .1
        key("c")
        self.assertEqual(picker.index, 2)  # second C cycles choices
        clock[0] += 1.3
        key("j")
        self.assertEqual(picker.index, 3)
        self.assertEqual(key(keysym="BackSpace"), "break")
        self.assertIsNone(key(keysym="Down"))  # regular arrow still works
        self.assertIsNone(key(keysym="Escape"))  # default popup behavior

    def test_note_picker_selection_by_title_not_body_filter(self):
        picker = FakePicker(["Welcome", "★ Router Commands", "Meeting Notes", "Network test"])
        picker_typeahead.install(picker, time_source=lambda: 0)
        for char in "router":
            picker._pocket_typeahead(SimpleNamespace(char=char, keysym=char, state=0))
        self.assertEqual(picker.current(), 1)
        self.assertEqual(len(picker.values), 4)
        self.assertEqual(picker.events, ["<<ComboboxSelected>>"])

    def test_clipboard_pinned_first_stable_and_input_unchanged(self):
        entries = [
            {"id": "new", "text": "new", "pinned": False},
            {"id": "older", "text": "older", "pinned": True},
            {"id": "middle", "text": "middle", "pinned": False},
            {"id": "oldest", "text": "oldest", "pinned": True},
        ]
        ordered = clipboard_gallery.pinned_first(entries)
        self.assertEqual([x["id"] for x in ordered],
                         ["older", "oldest", "new", "middle"])
        self.assertEqual([x["id"] for x in entries],
                         ["new", "older", "middle", "oldest"])
        entries[1]["pinned"] = False
        self.assertEqual([x["id"] for x in clipboard_gallery.pinned_first(entries)],
                         ["oldest", "new", "older", "middle"])


if __name__ == "__main__":
    unittest.main()
