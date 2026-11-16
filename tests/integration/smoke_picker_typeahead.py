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
            if sys.platform == "win32":
                # Exercise real Win32 WM_CHAR through the popup HWND. Tcl's
                # event-generate test previously passed while real typing
                # remained broken on Windows.
                import ctypes
                bridge = widget._pocket_typeahead_win32
                require(bridge.installed,
                        f"{label}: native Listbox keyboard bridge was not installed")
                user32 = ctypes.WinDLL("user32", use_last_error=True)
                user32.SendMessageW.argtypes = (
                    ctypes.c_void_p, ctypes.c_uint32,
                    ctypes.c_size_t, ctypes.c_ssize_t)
                user32.SendMessageW.restype = ctypes.c_ssize_t
                user32.GetFocus.argtypes = ()
                user32.GetFocus.restype = ctypes.c_void_p
                native_focused_hwnd = user32.GetFocus()
                require(native_focused_hwnd == bridge._child.value,
                        f"{label}: physical Windows keyboard focus must belong "
                        f"to dropdown HWND (focus={native_focused_hwnd}, "
                        f"listbox={bridge._child.value})")
            for char in phrase:
                if sys.platform == "win32":
                    user32.SendMessageW(bridge._child, bridge.WM_CHAR, ord(char), 0)
                    bridge._poll()
                else:
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
