"""Real Tk smoke: ordinary dropdown selection with no sticky text highlight."""
from pathlib import Path
import sys
import time
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import picker_selection


def require(value, message):
    if not value:
        raise AssertionError(message)


def run():
    root = tk.Tk()
    root.geometry("380x280")
    root.title("Pocket normal dropdown selection")
    try:
        for label, options, target in (
            ("Notes", ["Welcome", "★ Router Notes", "Network handover"], 2),
            ("Machines", ["All machines", "Cisco", "Fortinet", "Juniper"], 3),
            ("Categories", ["All categories", "Interfaces", "Routing"], 1),
        ):
            ttk.Label(root, text=label).pack(anchor="w")
            picker = ttk.Combobox(root, values=options, state="readonly", width=26)
            picker.current(0)
            picker.pack(fill="x")
            chosen = []
            picker.bind("<<ComboboxSelected>>", lambda _e: chosen.append(picker.get()))
            picker_selection.install(picker)
            root.update()
            require(not hasattr(picker, "_pocket_typeahead"),
                    f"{label}: custom typeahead was not removed")
            original = tuple(picker["values"])
            popup = root.tk.call("ttk::combobox::PopdownWindow", str(picker))
            listing = str(popup) + ".f.l"
            root.tk.call("ttk::combobox::Post", str(picker))
            root.update()
            require(bool(int(root.tk.call("winfo", "ismapped", listing))),
                    f"{label}: standard dropdown did not open")
            # Preserve the default internal Listbox selection/highlight.
            root.tk.call(listing, "selection", "clear", 0, "end")
            root.tk.call(listing, "selection", "set", target)
            root.tk.call(listing, "activate", target)
            root.tk.call(listing, "see", target)
            root.update()
            selection = root.tk.splitlist(root.tk.call(listing, "curselection"))
            require(selection == (str(target),),
                    f"{label}: opened dropdown must highlight selected row")
            root.tk.call("event", "generate", listing, "<Return>", "-when", "tail")
            root.update()
            require(picker.current() == target and chosen and chosen[-1] == options[target],
                    f"{label}: default Enter did not select requested option")
            require(not bool(int(root.tk.call("winfo", "ismapped", listing))),
                    f"{label}: dropdown must close after selection")
            time.sleep(.09)
            root.update()
            require(not picker.selection_present(),
                    f"{label}: text remains highlighted after choosing")
            require(picker.get() == options[target],
                    f"{label}: chosen value should remain visible")
            require(tuple(picker["values"]) == original,
                    f"{label}: normal dropdown options changed")
        print("PASS: native dropdowns select normally and clear closed highlight")
    finally:
        root.destroy()


if __name__ == "__main__":
    run()
