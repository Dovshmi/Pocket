"""Real Tk integration smoke test. Uses a disposable test profile.

Runs under an actual display (Windows GitHub runner or Xvfb on Linux).
No production data, external services, or GitHub tokens are ever accessed.
"""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import tempfile
import traceback
import tkinter as tk

ROOT = Path(__file__).resolve().parent
PANES = ("notes", "links", "ports", "mac", "commands", "subnet", "clipboard", "settings")
MODES = ("normal", "mini", "dashboard")


def widgets(root):
    for child in root.winfo_children():
        yield child
        yield from widgets(child)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def capture(app, output, label):
    if not output:
        return
    try:
        from PIL import ImageGrab
        app.root.update_idletasks()
        x, y = app.root.winfo_rootx(), app.root.winfo_rooty()
        w, h = app.root.winfo_width(), app.root.winfo_height()
        ImageGrab.grab(bbox=(x, y, x+w, y+h)).save(output / (label + ".png"))
    except Exception as exc:
        print("Screenshot unavailable:", label, repr(exc))


with tempfile.TemporaryDirectory(prefix="pocket-ui-audit-") as profile:
    os.environ["APPDATA"] = profile
    appmod = runpy.run_path(str(ROOT / "app.pyw"), run_name="pocket_ui_audit")
    from compact_dashboard import display_slots
    from mini_layout import view_dimensions

    app = appmod["PocketDesk"](preview=True)
    errors = []
    def report_exception(error_type, error, trace):
        errors.append("".join(traceback.format_exception(error_type, error, trace)))
    app.root.report_callback_exception = report_exception
    output = os.environ.get("POCKET_AUDIT_SCREENSHOTS")
    output = Path(output) if output else None
    if output:
        output.mkdir(parents=True, exist_ok=True)

    try:
        app.root.update()
        check(app.display_mode == "normal", "fresh data should start in Normal")
        check(app.root.winfo_width() == view_dimensions("normal")[0],
              "Normal geometry is wrong")
        print("PASS: initial window and isolated data")

        from tkinter import ttk
        from icon_themes import palette
        style = ttk.Style(app.root)
        check(style.theme_use() == "clam", "Dark ttk theme was not selected")
        self_color = palette(app.theme)
        check(style.lookup("Pocket.TCombobox", "foreground", ("readonly",)) ==
              self_color["WHITE"], "Readonly dropdown text is not readable")
        check(style.lookup("Pocket.TCombobox", "fieldbackground", ("readonly",)) ==
              self_color["INPUT"], "Readonly dropdown has the wrong background")
        check(style.lookup("Pocket.TCombobox", "foreground", ("disabled",)) ==
              self_color["MUTED"], "Disabled dropdown lacks contrast")
        print("PASS: real ttk Combobox readonly and disabled dark-theme colors")

        for mode in MODES:
            app._set_display_mode(mode)
            app.root.update()
            check(app.display_mode == mode, "could not select " + mode)
            for page in PANES:
                app.show_tab(page)
                app.root.update()
                check(app.current_tab == page, f"{mode}: {page} did not open")
                check(app.body.winfo_exists(), f"{mode}: missing page body {page}")
                desired = view_dimensions(mode)[0]
                actual = app.root.winfo_width()
                # The wide Dashboard clamps to the monitor work area.
                max_safe = max(240, app.root.winfo_screenwidth() - 12)
                check(actual == min(desired, max_safe),
                      f"{mode}/{page}: width {actual}, expected "
                      f"{min(desired, max_safe)} (screen {app.root.winfo_screenwidth()})")
            if mode == "dashboard":
                app.show_tab("home")
                app.root.update()
                check(app.current_tab == "home", "Dashboard overview not reachable")
                tool_cards = [w for w in widgets(app.body)
                              if isinstance(w, tk.Button) and
                              str(w.cget("text")).strip() == "Open  →"]
                check(len(tool_cards) == len(app.settings["visible_tabs"]),
                      "Dashboard overview does not show every enabled tool")
                check(app._tool_scroll_canvas is not None,
                      "Expanded Dashboard overview must scroll on small screens")
                canvas = app._tool_scroll_canvas
                app.root.update_idletasks()
                check(canvas.yview()[1] < 1,
                      "Dashboard Home content should extend below viewport")
                initial_scroll = canvas.yview()[0]
                canvas.yview_scroll(3, "units")
                app.root.update_idletasks()
                check(canvas.yview()[0] > initial_scroll,
                      "Dashboard Home cannot scroll to lower tools")
            if mode == "mini":
                check(len(app.mini_icon_tabs) == len(app.settings["visible_tabs"])+1,
                      "Mini navigation should show every enabled menu plus Settings")
                for key, (tile, glyph, caption) in app.mini_icon_tabs.items():
                    check(bool(tile.bind("<Return>")) and bool(tile.bind("<space>")),
                          f"Mini tool {key}: missing keyboard access")
            app.show_tab("settings")
            app.root.update()
            names = [str(w.cget("text")) for w in widgets(app.body)
                     if isinstance(w, (tk.Label, tk.Button, tk.Checkbutton))]
            check(any("Appearance & layout" in n for n in names),
                  f"{mode}: modern Settings card missing")
            check(any("Extra Mini" in n for n in names),
                  f"{mode}: Extra Mini setting missing")
            capture(app, output, "settings_" + mode)
            print("PASS: all menu pages and modern Settings in", mode)

        app._set_display_mode("normal")
        app.show_tab("settings")
        app._set_extra_mini_enabled(True)
        app.root.update()
        app._edit_extra_mini_from_settings()
        app.root.update()
        check(app.display_mode == "compact", "Settings did not open Extra Mini")
        check(app._compact_editing, "Settings did not activate inline editor")
        check(len(app.compact_cards.winfo_children()) == 4, "not four card slots")

        def get_slot(index):
            return app.compact_cards.grid_slaves(row=0, column=index)[0]

        def tile_button(index, caption):
            for w in widgets(get_slot(index)):
                if isinstance(w, tk.Button) and str(w.cget("text")) == caption:
                    return w
            return None

        remove = tile_button(0, "×")
        check(remove is not None, "Edit did not expose tile remove button")
        remove.invoke()
        app.root.update()
        check(app.settings["extra_mini_tiles"][0] is None,
              "Removing tile did not preserve empty slot")
        check(tile_button(0, "+") is not None,
              "Missing plus button after removing a tile")
        # On headless Windows GitHub runners, native tk_popup can block forever
        # waiting for a real menu-dismiss event. Linux/Xvfb exercises the actual
        # plus popup; Windows verifies the UI state and selection data helper.
        if os.name == "nt":
            from compact_dashboard import available_tools, choose_tile
            check(bool(available_tools(app.settings["visible_tabs"],
                                       app.settings["extra_mini_tiles"], 0)),
                  "No available tools after removing a tile")
            app.settings["extra_mini_tiles"] = choose_tile(
                app.settings["extra_mini_tiles"], 0, "links",
                app.settings["visible_tabs"])
            app.compact_render_cards()
            app.schedule_save()
        else:
            preexisting = set(app.root.winfo_children())
            tile_button(0, "+").invoke()
            app.root.update_idletasks()
            choices = [w for w in app.root.winfo_children()
                       if isinstance(w, tk.Menu) and w not in preexisting]
            check(bool(choices), "Plus did not open tool-picker menu")
            picker = choices[-1]
            check(picker.index("end") is not None, "Empty picker menu")
            picker.invoke(0)
            picker.unpost()
            app.root.update()
        check(app.settings["extra_mini_tiles"][0] is not None,
              "Picker selection did not save replacement")
        check(len(set(k for k in app.settings["extra_mini_tiles"] if k)) ==
              len([k for k in app.settings["extra_mini_tiles"] if k]),
              "Duplicate tile assignments")
        check(app.compact_edit_button.cget("text") == "Done", "Missing Done control")
        app.compact_edit_button.invoke()
        app.root.update()
        check(not app._compact_editing, "Done did not leave Edit mode")
        capture(app, output, "extra_mini")
        print("PASS: Extra Mini real Edit, ×, +, selection and Done controls")

        # The tiny launcher must restore the *selected* base layout, not Mini.
        for mode in MODES:
            app._set_display_mode(mode)
            app.root.update()
            app.show_tab("notes")
            app._return_to_compact()
            app.root.update()
            check(app.display_mode == "compact", mode + ": minimize failed")
            app._open_compact_tool("subnet")
            app.root.update()
            check(app.display_mode == mode, mode + ": wrong restored layout")
            check(app.current_tab == "subnet", mode + ": wrong destination")
            app._return_to_compact()
            app.root.update()
            app._expand_from_extra_mini()
            app.root.update()
            check(app.display_mode == mode, mode + ": expand failed")
            check(app.current_tab == "subnet", mode + ": previous menu not restored")
            print("PASS: launcher minimize / restore / expand from", mode)

        # Theme and visibility must not mutate data or change the base layout.
        app._choose_theme("purple")
        app.root.update()
        check(app.theme == "purple", "theme choice did not apply")
        app.show_tab("settings")
        app._set_visible_tab("clipboard", False)
        app.root.update()
        check("clipboard" not in app.settings["visible_tabs"], "hide-menu failed")
        app._set_visible_tab("clipboard", True)
        app.root.update()
        check("clipboard" in app.settings["visible_tabs"], "restore-menu failed")
        print("PASS: theme changes and show/hide menus")

        app.show_tab("notes")
        app.add_note()
        app.root.update()
        check(len(app.data["notes"]) == 2, "new note creation failed")
        app.show_tab("subnet")
        app.subnet_ip_var.set("192.168.3.71")
        app.subnet_prefix_var.set("27")
        app._calculate_subnet()
        app.root.update()
        check(app.subnet_details["cidr"] == "192.168.3.64/27",
              "subnet calculation wrong")
        app.show_tab("commands")
        app.root.update()
        check(hasattr(app, "command_search_entry"), "CLI search missing")
        # Quick Search is a local, working popup in all three layouts.
        for working in MODES:
            app._set_display_mode(working)
            app.root.update()
            app._open_global_search()
            app.root.update()
            dialog = app._quick_search_dialog
            check(dialog is not None and dialog.winfo_exists(),
                  working + ": Quick Search failed to open")
            entries = [w for w in widgets(dialog) if isinstance(w, tk.Entry)]
            check(len(entries) == 1, working + ": search input absent")
            entries[0].insert(0, "notes")
            app.root.update()
            lists = [w for w in widgets(dialog) if isinstance(w, tk.Listbox)]
            check(lists and lists[0].size() > 0, working + ": missing local matches")
            open_buttons = [w for w in widgets(dialog)
                            if isinstance(w, tk.Button) and w.cget("text") == "Open"]
            check(open_buttons, working + ": Quick Search missing Open control")
            open_buttons[0].invoke()
            app.root.update()
            check(app._quick_search_dialog is None, working + ": search popup did not close")
            check(app.current_tab == "notes", working + ": local tool result did not navigate")
        print("PASS: Ctrl+K Quick Search popup and local results in every working layout")

        app._set_display_mode("normal")
        app.show_tab("clipboard")
        app.root.update()
        app._set_clipboard_paused(True)
        check(app.settings["clipboard_paused"], "Clipboard pause not set")
        app._set_clipboard_sensitive_filter(False)
        check(not app.settings["clipboard_sensitive_filter"], "Privacy setting not saved")
        app._set_clipboard_paused(False)
        app._set_clipboard_sensitive_filter(True)
        app.root.update()
        check("capture ON" in app.clipboard_status.cget("text"),
              "Clipboard status failed to refresh")
        print("PASS: Clipboard pause, resume and optional sensitive filtering")

        # Clipboard should remain in RAM and never be serialized.
        appmod["clipboard_add"](app.clipboard_items, "TEST AUDIT PRIVATE CLIPBOARD")
        app._write_now()
        stored = app.path.read_text(encoding="utf-8")
        check("TEST AUDIT PRIVATE CLIPBOARD" not in stored, "clipboard leaked to data.json")
        persisted = appmod["load_data"](app.path)
        check(persisted["settings"]["extra_mini_enabled"], "toggle not persisted")
        check(persisted["settings"]["display_mode"] == app.settings["display_mode"],
              "working layout not persisted")
        check(persisted["settings"]["extra_mini_tiles"] ==
              app.settings["extra_mini_tiles"], "tile slots not persisted")
        print("PASS: note, subnet, CLI entry, clipboard privacy and reload")

        check(not errors, "Tk callback errors:\n" + "\n".join(errors))
        print("GUI AUDIT PASS — all active UI interactions and settings smoke-tested")
    finally:
        # Prevent scheduled event handlers from writing after temp profile teardown.
        for job in app.root.tk.call("after", "info"):
            try:
                app.root.after_cancel(job)
            except (tk.TclError, RuntimeError):
                pass
        try:
            app.root.destroy()
        except tk.TclError as exc:
            # Windows TkDnD cleanup can encounter already-removed commands.
            if "can't delete Tcl command" not in str(exc):
                raise
