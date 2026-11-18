"""Verify Quick Slot replacement uses the native OS MessageBox API, not Toplevel."""
import sys
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import quick_slot_dialog


def run():
    root = tk.Tk()
    root.withdraw()
    try:
        for accepted in (False, True):
            with patch.object(quick_slot_dialog.messagebox, "askyesno",
                              return_value=accepted) as native:
                result = quick_slot_dialog.confirm_replace(
                    root, "blue", 2, "SVLAN 1557", "SVLAN 11")
                assert result is accepted
                native.assert_called_once_with(
                    "Replace Quick Slot [2]?",
                    "Old text: SVLAN 1557\n↓\nNew text: SVLAN 11",
                    parent=root)
            assert not any(isinstance(w, tk.Toplevel)
                           for w in root.winfo_children()), (
                "Custom Tkinter replacement window should not be created")
    finally:
        root.destroy()
    print("PASS: native Windows askyesno, Old -> New, both Yes/No outcomes")


if __name__ == "__main__":
    run()
