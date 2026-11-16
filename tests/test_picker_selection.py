"""Regression tests for normal dropdown selection and pinned clipboard order."""
import unittest

from pocket import clipboard_gallery
from pocket import picker_selection


class FakeTcl:
    def __init__(self, open_=False):
        self.open = open_
    def call(self, *args):
        if args[0] == "ttk::combobox::PopdownWindow":
            return ".picker.popdown"
        if args[:2] == ("winfo", "ismapped"):
            return int(self.open)
        raise AssertionError(args)


class FakePicker:
    def __init__(self, open_=False):
        self.tk = FakeTcl(open_)
        self.value = "Juniper"
        self.clears = 0
        self.jobs = []
        self.callbacks = {}
        self.exists = True
    def winfo_exists(self):
        return self.exists
    def __str__(self):
        return ".picker"
    def selection_clear(self):
        self.clears += 1
    def after(self, delay, callback):
        self.jobs.append((delay, callback))
    def bind(self, event, callback, add=None):
        self.callbacks[event] = callback


class DropdownSelectionTests(unittest.TestCase):
    def test_closed_highlight_is_removed_but_value_preserved(self):
        picker = FakePicker(open_=False)
        picker_selection.install(picker)
        self.assertIn("<<ComboboxSelected>>", picker.callbacks)
        picker.callbacks["<<ComboboxSelected>>"](None)
        self.assertEqual(picker.clears, 0)
        picker.jobs.pop()[1]()
        self.assertEqual(picker.clears, 1)
        self.assertEqual(picker.value, "Juniper")

    def test_open_list_highlight_is_preserved_until_closed(self):
        picker = FakePicker(open_=True)
        picker_selection.clear_closed_selection(picker)
        self.assertEqual(picker.clears, 0)
        self.assertEqual(len(picker.jobs), 1)
        picker.tk.open = False
        picker.jobs.pop()[1]()
        self.assertEqual(picker.clears, 1)

    def test_deleted_widget_is_ignored(self):
        picker = FakePicker()
        picker.exists = False
        picker_selection.clear_closed_selection(picker)
        self.assertEqual(picker.clears, 0)

    def test_clipboard_still_sorts_pins_first_without_mutating_history(self):
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


if __name__ == "__main__":
    unittest.main()
