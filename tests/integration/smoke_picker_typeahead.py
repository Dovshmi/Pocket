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
            require(bool(root.tk.call("winfo", "ismapped", listing)),
                    f"{label}: popup did not open")
            focus = str(root.tk.call("focus"))
            require(focus == listing,
                    f"{label}: popup must have actual keyboard focus, got {focus!r}")
            for char in phrase:
                # Deliver each key to Tk's genuinely focused dropdown Listbox.
                # The old code changed the *selected command/note* after the
                # first character, which closed or displaced real keyboard
                # focus before subsequent letters were delivered.
                root.tk.call("event", "generate", focus, f"<KeyPress-{char}>",
                             "-when", "tail")
                root.update()
                require(bool(root.tk.call("winfo", "ismapped", listing)),
                        f"{label}: popup closed while typing {phrase!r}")
                require(widget.current() == 0,
                        f"{label}: typing committed choice before Enter")
                require(str(root.tk.call("focus")) == listing,
                        f"{label}: typing stole focus from the open list")
            require(tuple(widget["values"]) == original,
                    f"{label}: popup typing must not filter or remove options")
            selected = tuple(int(v) for v in root.tk.splitlist(
                root.tk.call(listing, "curselection")))
            require(selected == (target,),
                    f"{label}: dropdown did not highlight matching item")
            require(int(root.tk.call(listing, "index", "active")) == target,
                    f"{label}: active row did not follow typed match")
            root.tk.call("event", "generate", listing, "<Return>", "-when", "tail")
            root.update()
            require(widget.current() == target,
                    f"{label}: Enter did not commit highlighted option")
            require(not bool(root.tk.call("winfo", "ismapped", listing)),
                    f"{label}: native Enter must close the popup")
        print("PASS: Notes, machines and categories navigate by typing in open readonly dropdowns")
    finally:
        root.destroy()


if __name__ == "__main__":
    run()
