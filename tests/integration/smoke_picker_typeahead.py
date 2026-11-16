"""Real Tk smoke: type-to-jump inside the existing posted readonly dropdown."""
from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pocket import picker_typeahead


def require(check, message):
    if not check:
        raise AssertionError(message)


def run():
    root = tk.Tk()
    root.title("Pocket dropdown typeahead")
    root.geometry("350x250")
    try:
        for label, options, phrase, target in (
            ("Notes", ["Welcome", "★ Juniper operations", "Network handover"],
             "juniper", 1),
            ("Machines", ["All machines", "Cisco", "Fortinet", "Juniper"],
             "juniper", 3),
            ("Categories", ["All categories", "Interfaces", "Routing", "Security"],
             "security", 3),
        ):
            ttk.Label(root, text=label).pack(anchor="w")
            widget = ttk.Combobox(
                root, values=options, state="readonly", width=26)
            widget.current(0)
            widget.pack(fill="x")
            picker_typeahead.install(widget)
            root.update()
            listing = getattr(widget, "_pocket_typeahead_popdown", None)
            require(listing and root.tk.call("winfo", "exists", listing),
                    f"{label}: actual Tk dropdown Listbox is missing")
            require(str(widget.cget("state")) == "readonly",
                    f"{label}: native readonly behavior was lost")
            original = tuple(widget["values"])
            root.tk.call("ttk::combobox::Post", str(widget))
            root.update()
            for char in phrase:
                root.tk.call("event", "generate", listing, f"<KeyPress-{char}>")
                root.update()
            require(widget.current() == target,
                    f"{label}: popup typing did not select the matching option")
            require(tuple(widget["values"]) == original,
                    f"{label}: popup typing must not filter or remove options")
            selected = tuple(int(v) for v in root.tk.splitlist(
                root.tk.call(listing, "curselection")))
            require(selected == (target,),
                    f"{label}: dropdown should highlight and navigate to match")
            root.tk.call("ttk::combobox::Unpost", str(widget))
            root.update()
        print("PASS: Notes, machines and categories navigate by typing in open readonly dropdowns")
    finally:
        root.destroy()


if __name__ == "__main__":
    run()
