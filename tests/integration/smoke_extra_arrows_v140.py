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
    for index in range(369, 389)
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
        check(result_list.size() == len(hits), "Synthetic SQLite results not displayed")
        check(result_list.curselection() == (0,), "First result not selected")
        check(any(isinstance(w, tk.Label) and w.cget("text") == "20 rows"
                  for w in widgets(outer)), "Matches heading did not show count")

        # Mini has a slim dark draggable rail; the list itself must not
        # scroll on MouseWheel or Linux touchpad Button-4/5 events.
        scroll = next((w for w in widgets(outer)
                       if isinstance(w, tk.Scrollbar) and
                       w.master is result_list.master and
                       w.cget("command") == str(result_list) + " yview"), None)
        if scroll is None:
            scroll = next((w for w in widgets(outer)
                           if isinstance(w, tk.Scrollbar) and
                           w.master is result_list.master), None)
        check(scroll is not None and int(scroll.cget("width")) <= 8 and
              scroll.winfo_ismapped(),
              "Mini Matches must have a thin, visible scrollbar")
        check(result_list.yview()[1] < 1.0,
              "Synthetic results must exceed the visible five-row area")
        start_view = result_list.yview()
        result_list.event_generate("<MouseWheel>", delta=-120)
        root.update()
        check(result_list.yview() == start_view,
              "MouseWheel must not scroll the Mini Matches list")
        if sys.platform != "win32":
            # Button-4/5 is an X11 convention; synthetic Button-5 is not
            # supported by native Windows Tk and can stall the event loop.
            result_list.event_generate("<Button-5>")
            root.update()
            check(result_list.yview() == start_view,
                  "Linux mouse wheel must not scroll the Mini Matches list")
        # Invoke the *real scrollbar's command* without simulating mouse
        # grab/autorepeat: Win32's native scrollbar can keep a synthetic press
        # active indefinitely inside Tk's modal event loop.
        scroll.tk.call(scroll.cget("command"), "scroll", 3, "units")
        root.update()
        check(result_list.yview()[0] > start_view[0],
              "Matches scrollbar/yview must remain operational")
        result_list.yview_moveto(0)
        root.update()
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
        print("PASS: Extra arrows, no wheel scrolling in Matches, thin scrollbar, merged Sync")
finally:
    root.destroy()
