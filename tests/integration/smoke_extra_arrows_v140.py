"""Real Tk smoke for Pocket Extra result arrows and space-saving controls.

Synthetic matches only; patched SQLite reads do not touch work documents,
network, the user's source workbook or the user's actual Pocket database.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pocket import extra_excel_ui
from pocket.extra_excel_lookup import ExcelHit


def widgets(parent):
    for child in parent.winfo_children():
        yield child
        yield from widgets(child)


def check(condition, reason):
    if not condition:
        raise AssertionError(reason)


hits = [
    ExcelHit("FG-26-METRO1", index, (("לקוח (A)", f"Customer {index}"),
                                    ("קוד קישור (B)", f"82-{index}"),
                                    ("VDOM (G)", "sample-vdom")), (), True)
    for index in (369, 370, 371)
]

root = tk.Tk()
root.geometry("600x800")
app = SimpleNamespace(root=root, theme="blue", display_mode="mini",
                      _extra_excel_mode="database",
                      _extra_excel_cancel=threading.Event(),
                      _extra_excel_work_token=0)
outer = tk.Frame(root)
outer.pack(fill="both", expand=True)
try:
    with patch.object(extra_excel_ui.db, "read_info",
                      return_value={"updated_at": "2026-11-22T16:30:00+00:00"}), \
         patch.object(extra_excel_ui.db, "search_database",
                      return_value=(hits, False)):
        extra_excel_ui.build(app, outer)
        root.update()
        controls = list(widgets(outer))
        result_list = next(w for w in controls if isinstance(w, tk.Listbox))
        search = next(w for w in controls if isinstance(w, tk.Button) and
                      w.cget("text") == "Search")
        browse = next(w for w in controls if isinstance(w, tk.Button) and
                      w.cget("text") == "Browse")
        sync = next(w for w in controls if isinstance(w, tk.Button) and
                    w.cget("text") == "Sync")
        # Source + Sync are descendants of the same bordered panel.
        check(sync.master.master.master is browse.master.master,
              "Database actions are still in a separate panel")
        entries = [w for w in controls if isinstance(w, tk.Entry)]
        check(len(entries) == 1, "The Excel filename was incorrectly an editable input")
        entry = entries[0]
        entry.delete(0, "end")
        entry.insert(0, "cofix")
        search.invoke()

        limit = time.monotonic() + 5
        while result_list.size() < len(hits) and time.monotonic() < limit:
            root.update()
            time.sleep(0.04)
        root.update()
        check(result_list.size() == 3, "Synthetic SQLite results not displayed")
        check(result_list.curselection() == (0,), "First result not selected")
        check(any(isinstance(w, tk.Label) and w.cget("text") == "3 rows"
                  for w in widgets(outer)), "Matches heading did not show count")

        result_list.focus_force()
        root.update()
        result_list.event_generate("<Down>")
        root.update()
        check(result_list.curselection() == (1,), "Down did not select next match")
        result_list.event_generate("<Up>")
        root.update()
        check(result_list.curselection() == (0,), "Up did not select prior match")

        # Click inside Selected Row to focus the details pane, then navigate
        # with Right/Left. There must not be any new arrow icon/buttons.
        info = next(w for w in widgets(outer) if isinstance(w, tk.Label)
                    and w.cget("text") == "FG-26-METRO1 · Row 369")
        info.event_generate("<ButtonPress-1>", x=8, y=8)
        info.event_generate("<ButtonRelease-1>", x=8, y=8)
        root.update()
        focused = root.focus_get()
        check(focused is not None and focused is info.master,
              "Clicking Selected Row did not focus the detail panel")
        focused.event_generate("<Right>")
        root.update()
        check(result_list.curselection() == (1,),
              "Right arrow in Selected Row did not advance")
        focused = root.focus_get()
        check(focused is not None, "Focus lost after moving Selected Row")
        focused.event_generate("<Left>")
        root.update()
        check(result_list.curselection() == (0,),
              "Left arrow in Selected Row did not move backward")
        print("PASS: Extra Up/Down and Left/Right, compact counts and merged Sync")
finally:
    root.destroy()
