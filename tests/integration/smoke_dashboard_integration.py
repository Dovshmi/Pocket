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

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))
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
    from pocket.compact_dashboard import display_slots
    from pocket.mini_layout import view_dimensions

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
        from pocket.icon_themes import palette
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

        # Populate only the temporary, isolated test profile with harmless
        # example content so captures show working tool views, not blank states.
        app.data["notes"][0].update({
            "title": "Network shift notes",
            "body": "Shift handover checklist:\n\n"
                    "- Review interface status and routing changes\n"
                    "- Check important uplinks\n"
                    "- Record follow-up tasks for the next shift",
            "phone": "",
        })
        for example_clip in (
            "show ip interface brief",
            "get router info routing-table all",
            "192.168.10.0/24",
        ):
            appmod["clipboard_add"](app.clipboard_items, example_clip)

        for mode in MODES:
            app._set_display_mode(mode)
            app.root.update()
            check(app.display_mode == mode, "could not select " + mode)
            for page in PANES:
                app.show_tab(page)
                app.root.update()
                check(app.current_tab == page, f"{mode}: {page} did not open")
                check(app.body.winfo_exists(), f"{mode}: missing page body {page}")
                # Capture every actual tool page in every working layout.
                capture(app, output, mode + "_" + page)
                if page == "clipboard":
                    from PIL import Image
                    from pocket import clipboard_images
                    if not app.clipboard_images:
                        check(clipboard_images.add_image(
                            app.clipboard_images,
                            Image.new("RGB", (180, 100), "#283f74")),
                            "Image history did not accept a test screenshot")
                    check("text" in app.clipboard_page_buttons and
                          "images" in app.clipboard_page_buttons,
                          f"{mode}: missing Clipboard sub-tabs")
                    toggle = app.clipboard_page_toggle
                    check(int(toggle.cget("width")) == 44 and
                          int(toggle.cget("height")) == 22,
                          f"{mode}: Clipboard switch should be compact like Local/DashDash")
                    check(app.clipboard_page_buttons["images"].winfo_width() < 100,
                          f"{mode}: Clipboard choice button is too wide")
                    app.clipboard_page_buttons["images"].invoke()
                    app.root.update()
                    check(app.clipboard_page == "images" and
                          app.clipboard_text_page.winfo_manager() == "",
                          f"{mode}: image page should replace text search")
                    check(not app.clipboard_query_entry.winfo_ismapped(),
                          f"{mode}: image page must not show text search")
                    check(app.clipboard_images_canvas.winfo_width() >= 150,
                          f"{mode}: image gallery is too narrow")
                    check(len(app._clipboard_gallery_tiles) == 1,
                          f"{mode}: image preview tile was not rendered")
                    from pocket import clipboard_gallery
                    from unittest.mock import patch
                    image_item = app.clipboard_images[0]
                    # Real GUI action is wired to the bitmap clipboard writer.
                    with patch.object(clipboard_images, "copy_image") as copy_image:
                        clipboard_gallery.select_image(app, image_item["id"])
                        buttons = [w for w in widgets(app.clipboard_images_page)
                                   if isinstance(w, tk.Button) and w.cget("text") == "Copy"]
                        check(len(buttons) == 1, f"{mode}: image Copy action missing")
                        buttons[0].invoke()
                        copy_image.assert_called_once_with(image_item["data"])
                    capture(app, output, mode + "_clipboard_images")
                    app.clipboard_page_buttons["text"].invoke()
                    app.root.update()
                    check(app.clipboard_page == "text" and
                          app.clipboard_list.winfo_exists(),
                          f"{mode}: existing text Clipboard was lost")
                    app.clipboard_list.selection_clear(0, tk.END)
                    app.clipboard_list.selection_set(0)
                    expected_text = app._clipboard_filtered[0]["text"]
                    text_copy_buttons = [w for w in widgets(app.clipboard_text_page)
                                         if isinstance(w, tk.Button) and w.cget("text") == "Copy"]
                    check(len(text_copy_buttons) == 1,
                          f"{mode}: text Copy action missing")
                    text_copy_buttons[0].invoke()
                    app.root.update()
                    check(app.root.clipboard_get() == expected_text,
                          f"{mode}: text Copy must put full selection on Windows clipboard")
                    check(text_copy_buttons[0].winfo_rooty() +
                          text_copy_buttons[0].winfo_height() <=
                          app.root.winfo_rooty() + app.root.winfo_height(),
                          f"{mode}: copy action must stay visible")
                if page in ("ports", "mac"):
                    # The slide selector must fit on an existing input-label row,
                    # remain interactive, and never start a network operation.
                    selector = app.port_source if page == "ports" else app.mac_source
                    control = [w for w in widgets(app.body)
                               if isinstance(w, tk.Canvas) and
                               int(w.cget("width")) == 44 and
                               int(w.cget("height")) == 22]
                    check(len(control) == 1,
                          f"{mode}: {page} should have exactly one compact source switch")
                    control = control[0]
                    heading = "TARGET IP" if page == "ports" else "MAC ADDRESSES"
                    labels = [w for w in widgets(app.body)
                              if isinstance(w, tk.Label) and w.cget("text") == heading]
                    check(len(labels) == 1 and
                          abs(labels[0].winfo_rooty() - control.winfo_rooty()) <= 10,
                          f"{mode}: {page} source switch should share the input heading row")
                    selected = selector.get()
                    saved_other = app.data["tools"].get(
                        "mac_source" if page == "ports" else "source")
                    control.event_generate("<Button-1>", x=22, y=11)
                    app.root.update()
                    check(selector.get() != selected,
                          f"{mode}: {page} switch did not toggle")
                    check(app.data["tools"].get(
                        "source" if page == "ports" else "mac_source") == selector.get(),
                        f"{mode}: {page} source was not saved")
                    check(app.data["tools"].get(
                        "mac_source" if page == "ports" else "source") == saved_other,
                        f"{mode}: switching {page} changed the other tool's preference")
                    capture(app, output, mode + "_" + page + "_remote")
                    control.event_generate("<Button-1>", x=22, y=11)
                    app.root.update()
                    check(selector.get() == selected,
                          f"{mode}: {page} switch did not return to its original state")
                if page == "ports":
                    from pocket import port_presets as port_prefs
                    # Switching layouts reconstructs the tool without losing favorites.
                    if mode != "normal":
                        check(7777 in app.port_favorites,
                              f"{mode}: favorite was lost when changing layout")
                    app.port_favorites = []
                    app.data["tools"]["favorite_ports"] = []
                    app.last_scan_ports = []
                    app._render_quick_ports()
                    check(not app.port_quick_frame.winfo_ismapped(),
                          f"{mode}: Quick Port Selection must start collapsed")
                    check(not app.port_quick_buttons,
                          f"{mode}: Quick Port Selection should have no fixed port presets")
                    check(int(app.port_count.cget("text").split("/")[1]) == 16,
                          f"{mode}: sixteen-port counter is missing")
                    old_input = app.ports_var.get()
                    app.ports_var.set("7777,8888")
                    app.root.update()
                    app.port_quick_button.invoke()
                    app.root.update()
                    check(app.port_quick_frame.winfo_ismapped(),
                          f"{mode}: Quick Port Selection did not expand")
                    check(not app.port_quick_buttons,
                          f"{mode}: input text alone should not create quick items")
                    # Simulate the completion step without network I/O.
                    app._record_last_scan([7777, 8888, 443])
                    app.root.update()
                    check(list(app.port_quick_buttons) == [7777, 8888, 443],
                          f"{mode}: last-scan ports were not shown together")
                    app.port_star_buttons[7777].invoke()
                    app.root.update()
                    check(app.port_favorites == [7777] and
                          app.data["tools"]["favorite_ports"] == [7777],
                          f"{mode}: starred port was not saved")
                    check(app.port_star_buttons[7777].cget("text") == "★",
                          f"{mode}: saved port should have a filled star")
                    app._record_last_scan([3389, 9000])
                    app.root.update()
                    check(list(app.port_quick_buttons) == [7777, 3389, 9000],
                          f"{mode}: stale temporary ports were not removed")
                    check(app.port_quick_buttons[9000].cget("text") == "9000 · Custom",
                          f"{mode}: unknown ports must display Custom usage")
                    check(app.port_star_buttons[9000].cget("text") == "☆",
                          f"{mode}: temporary ports should show an empty star")
                    app.port_quick_buttons[3389].invoke()
                    app.root.update()
                    check(app.ports_var.get() == "7777,8888,3389",
                          f"{mode}: quick click replaced manually entered ports")
                    app.port_quick_buttons[3389].invoke()
                    app.root.update()
                    check(app.ports_var.get() == "7777,8888",
                          f"{mode}: clicking again should only remove the selected port")
                    app.port_star_buttons[9000].invoke()
                    app.root.update()
                    check(app.port_favorites == [7777, 9000],
                          f"{mode}: second star did not save as favorite")
                    app.port_star_buttons[9000].invoke()
                    app.root.update()
                    check(app.port_favorites == [7777] and
                          9000 in app.port_quick_buttons,
                          f"{mode}: unstarred recent port should stay until next check")
                    app._record_last_scan([443])
                    app.root.update()
                    check(list(app.port_quick_buttons) == [7777, 443],
                          f"{mode}: unstarred temporary port should vanish next check")
                    # A full input must not accept a seventeenth port.
                    app.ports_var.set(",".join(map(str, range(1, 17))))
                    app.root.update()
                    app.port_quick_buttons[443].invoke()
                    app.root.update()
                    check(len(port_prefs.parse_manual_ports(app.ports_var.get())) == 16,
                          f"{mode}: quick selection exceeded the port limit")
                    capture(app, output, mode + "_ports_favorites")
                    app.port_quick_button.invoke()
                    app.root.update()
                    check(not app.port_quick_frame.winfo_ismapped(),
                          f"{mode}: quick panel did not collapse")
                    app.ports_var.set(old_input)
                    app.root.update()
                    check(not app.scanning, f"{mode}: favorites started a scan")
                if page == "settings" and mode == "dashboard":
                    controls = app.dashboard_settings_controls
                    check(all(key in controls for key in (
                        "mode_normal", "mode_mini", "mode_dashboard",
                        "extra_mini", "customize_launcher",
                        "change_hotkey", "quick_search",
                        "clipboard_paused", "sensitive_filter")),
                        "Dashboard Settings is missing important controls")
                    for tool, _caption in app.VISIBLE_TABS_REFERENCE:
                        check("tool_" + tool in controls,
                              f"Dashboard Settings lost the {tool} visibility control")
                    check(controls["mode_normal"].winfo_rootx() <
                          controls["tool_notes"].winfo_rootx(),
                          "Dashboard Settings should use two side-by-side columns")
                    check(controls["theme_blue"].winfo_exists() and
                          controls["theme_purple"].winfo_exists(),
                          "Dashboard Settings has no visible color palette")
                    original_filter = app.settings["clipboard_sensitive_filter"]
                    controls["sensitive_filter"].invoke()
                    check(app.settings["clipboard_sensitive_filter"] != original_filter,
                          "Dashboard sensitive-text toggle did not apply")
                    controls["sensitive_filter"].invoke()
                    check(app.settings["clipboard_sensitive_filter"] == original_filter,
                          "Dashboard sensitive-text toggle did not restore the preference")
                if page == "links" and mode == "dashboard":
                    check(app.dashboard_shortcut_columns >= 2,
                          "Dashboard Shortcuts should display multiple columns")
                    check(app._scroll_canvas.winfo_height() >= 240,
                          "Dashboard Shortcuts results need proper vertical space")
                    check(app.dashboard_shortcut_count.winfo_exists(),
                          "Dashboard shortcut result count missing")
                    check(len(app.dashboard_shortcut_cards) == len(app.data["links"]),
                          "Dashboard shortcut cards missing")
                    app._toggle_link_form(None)
                    app.root.update()
                    check(bool(app.form_holder.winfo_manager()),
                          "Dashboard inline shortcut form did not open")
                    app._save_link("Dashboard test shortcut", "https://example.org", "url")
                    app.root.update()
                    check(any(link["title"] == "Dashboard test shortcut"
                              for link in app.data["links"]),
                          "Dashboard shortcut form could not save a URL")
                    check(not app.form_holder.winfo_manager(),
                          "Dashboard saved shortcut left a blank form gap")
                    app.dashboard_shortcut_kind.set("file")
                    app.refresh_links()
                    app.root.update()
                    check(len(app.dashboard_shortcut_cards) ==
                          sum(link.get("kind", "url") == "file" and
                              not app.link_query.get().strip()
                              for link in app.data["links"]),
                          "Dashboard shortcut type filter did not update cards")
                    app.dashboard_shortcut_kind.set("all")
                    app.refresh_links()
                    app.root.update()
                    extra = next(link for link in app.data["links"]
                                 if link["title"] == "Dashboard test shortcut")
                    app._toggle_link_form(extra)
                    app.root.update()
                    check(bool(app.form_holder.winfo_manager()),
                          "Dashboard edit-shortcut form did not open")
                    app._close_form()
                    app.root.update()
                    check(not app.form_holder.winfo_manager(),
                          "Dashboard cancelled edit left a blank form gap")
                    app._delete_link(extra)
                    app.root.update()
                if page == "notes" and mode == "dashboard":
                    # The wide Notes workspace should devote most of its
                    # height to editing, not to stacked Title/Phone cards.
                    check(app.note_body.winfo_rootx() > app.note_list.winfo_rootx(),
                          "Dashboard Notes editor must sit to the right of the note list")
                    check(app.title_entry.winfo_rooty() == app.phone_entry.winfo_rooty(),
                          "Dashboard Notes title and phone should share one compact row")
                    visible_editor = (app.bidi_editor if app._bidi_active()
                                      else app.note_body)
                    check(visible_editor.winfo_width() >= 350,
                          "Dashboard Notes editor must be substantially wider than Normal")
                    check(visible_editor.winfo_height() >= 250,
                          "Dashboard Notes editor does not have enough writing height")
                    check(app.title_entry.winfo_exists() and app.phone_entry.winfo_exists(),
                          "Dashboard Notes title or phone input is missing")
                    check(app.reminder_action.winfo_exists() and app.save_status.winfo_exists(),
                          "Dashboard Notes lost reminders or autosave indicator")
                if page == "commands" and mode == "dashboard":
                    check(str(app.command_panes.cget("orient")) == "horizontal",
                          "Dashboard Commands should use side-by-side panes")
                    if app.root.winfo_width() >= 1050:
                        check(app.command_tree.winfo_width() >= 400,
                              "Dashboard Commands list should get a real wide column")
                        check(app.command_code.winfo_width() >= 260,
                              "Dashboard command editor should remain usable")
                    check(int(app.command_tree.cget("height")) >= 14,
                          "Dashboard Commands must show more than four results")
                    check(app.command_code.winfo_rootx() > app.command_tree.winfo_rootx(),
                          "Dashboard command editor should be to the right of results")
                    check(app.command_tree.winfo_height() >= 200,
                          "Dashboard results table has too little vertical room")
                if page == "commands" and mode == "normal":
                    check(str(app.command_panes.cget("orient")) == "vertical",
                          "Normal Commands split should remain vertical")
                    check(int(app.command_tree.cget("height")) == 4,
                          "Normal Commands list should retain four-row layout")
                if page == "commands":
                    check(hasattr(app, "smart_template_edit") and
                          app.smart_template_edit.winfo_exists(),
                          f"{mode}: missing Smart Template control")
                    check("Plain command" in app.smart_template_badge.cget("text") or
                          "Template" in app.smart_template_badge.cget("text"),
                          f"{mode}: template status not shown")
                    app.smart_template_edit.invoke()
                    app.root.update()
                    dialogs = [w for w in app.root.winfo_children()
                               if isinstance(w, tk.Toplevel)]
                    check(dialogs, f"{mode}: template review editor did not open")
                    dialog = dialogs[-1]
                    check(any(isinstance(w, tk.Text) for w in widgets(dialog)),
                          f"{mode}: missing editable template format")
                    field_count = [w for w in widgets(dialog)
                                   if isinstance(w, tk.Label) and
                                   "detected" in str(w.cget("text"))]
                    check(field_count, f"{mode}: missing detected-fields count")
                    check(not any(isinstance(w, ttk.Combobox) for w in widgets(dialog)),
                          f"{mode}: advanced selectors displayed without request")
                    refresh_buttons = [w for w in widgets(dialog)
                                       if isinstance(w, tk.Button) and
                                       "Refresh fields" in str(w.cget("text"))]
                    check(refresh_buttons, f"{mode}: Refresh fields button missing")
                    refresh_buttons[0].invoke()
                    app.root.update()
                    check(not any(isinstance(w, ttk.Combobox) for w in widgets(dialog)),
                          f"{mode}: Refresh reintroduced complicated field controls")
                    cancels = [w for w in widgets(dialog)
                               if isinstance(w, tk.Button) and w.cget("text") == "Cancel"]
                    check(cancels, f"{mode}: template editor cannot cancel")
                    cancels[-1].invoke()
                    app.root.update()
                    check(not app._modal, f"{mode}: template editor did not close")
                    check(app.command_code.winfo_exists(),
                          f"{mode}: original command editor lost")
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
                capture(app, output, "dashboard_home_scrolled")
                canvas.yview_moveto(0)
                app.root.update()
                capture(app, output, "dashboard_home")
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
        # The new searchable picker replaces the native popup menu on all OSes.
        tile_button(0, "+").invoke()
        app.root.update()
        dialogs = [w for w in app.root.winfo_children()
                   if isinstance(w, tk.Toplevel)]
        check(dialogs, "Plus did not open searchable quick-action picker")
        picker_dialog = dialogs[-1]
        choices = [w for w in widgets(picker_dialog) if isinstance(w, tk.Listbox)]
        check(choices and choices[0].size() > 0,
              "Quick-action picker has no available Pocket tools")
        add_buttons = [w for w in widgets(picker_dialog)
                       if isinstance(w, tk.Button) and w.cget("text") == "Add action"]
        check(add_buttons, "Picker has no Add to tile button")
        add_buttons[0].invoke()
        app.root.update()
        check(not app._modal, "Quick-action picker did not close")
        check(app.settings["extra_mini_tiles"][0] is not None,
              "Picker selection did not save replacement")
        check(len(app._compact_pages()) == 1 and
              all(len(page["tiles"]) == 4 for page in app._compact_pages()),
              "Extra Mini did not collapse empty pages")
        check(bool(app.compact_add_button.winfo_manager()), "Footer Add missing in Edit mode")
        check(app.compact_edit_button.cget("text") == "Done", "Missing Done control")
        app.compact_edit_button.invoke()
        app.root.update()
        check(not app._compact_editing, "Done did not leave Edit mode")
        check(not app.compact_add_button.winfo_manager(), "Footer Add remains visible after Done")
        capture(app, output, "extra_mini")
        print("PASS: Extra Mini real Edit, ×, +, selection and Done controls")

        # Three-page launcher, scroll/arrow paging, reference tiles, and
        # deletion/hidden-menu handling with original working layout retained.
        from pocket.launcher_pages import put, lookup, rename_page, move, PAGE_COUNT
        note_id = app.data["notes"][0]["id"]
        pages = app._compact_pages()
        pages = put(pages, 1, 0, {"kind": "note", "id": note_id})
        pages = put(pages, 2, 0, {"kind": "tool", "id": "mac"})
        pages = rename_page(pages, 1, "Work")
        app._save_compact_pages(pages)
        app._set_compact_page(1)
        app.root.update()
        check("Work" in app.compact_status.cget("text"), "Page rename not reflected")
        check(app.data["extra_mini_page"] == 1, "Page selection did not persist")
        check(len(app.compact_cards.winfo_children()) == 4,
              "Extra Mini page does not show four tiles")
        check(lookup(pages[1]["tiles"][0], app.data, app.command_library,
                     app.settings["visible_tabs"])["status"] == "ready",
              "Saved note quick action does not resolve")
        app.compact_switch_page(1)
        check(app.data["extra_mini_page"] == 2, "Next-page control broken")
        app.compact_switch_page(-1)
        check(app.data["extra_mini_page"] == 1, "Previous-page control broken")
        pages = move(app._compact_pages(), 1, 0, 2, 2)
        app._save_compact_pages(pages)
        check(pages[1]["tiles"][0] is None and
              pages[2]["tiles"][2]["id"] == note_id,
              "Cross-page move did not move note reference")
        app._set_compact_page(2)
        app._launch_compact_item(pages[2]["tiles"][2])
        app.root.update()
        check(app.display_mode == "normal" and app.current_tab == "notes" and
              app.data["active_note"] == note_id,
              "Saved note tile did not restore working mode and open exact note")
        app._return_to_compact()
        app.root.update()
        check(app.data["extra_mini_page"] == 2, "Launcher page reset after closing")
        check(lookup({"kind": "note", "id": "deleted-not-found"}, app.data,
                     app.command_library, app.settings["visible_tabs"])["status"] == "missing",
              "Deleted note tile does not show missing state")
        check(lookup({"kind": "tool", "id": "commands"}, app.data,
                     app.command_library, ["notes"])["status"] == "hidden",
              "Hidden tool still active in launcher")
        print("PASS: Extra Mini paging, rename, saved note, moves and missing item protections")

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

        # Direct saved command references, copy-only, Smart Template and
        # shortcut tiles must dispatch to the exact saved item.
        from types import SimpleNamespace
        from pocket import smart_templates as smart
        app._set_display_mode("normal")
        app._return_to_compact()
        app._set_compact_page(0)
        app.root.update()
        app.compact_handle_wheel(SimpleNamespace(
            widget=app.compact_cards, delta=-120, num=None))
        check(app.data["extra_mini_page"] == 1, "Mouse-wheel paging broken")
        app.compact_handle_wheel(SimpleNamespace(
            widget=app.compact_cards, delta=120, num=None))
        check(app.data["extra_mini_page"] == 0, "Reverse wheel paging broken")
        reference = app.command_library[0]
        app._launch_compact_item({"kind": "command", "id": reference["id"],
                                  "action": "copy"})
        check(app.display_mode == "compact", "Direct Copy changed layout")
        check(app.root.clipboard_get() == reference["command"],
              "Direct Copy changed or executed original command")
        check(app._clipboard_last == reference["command"],
              "Direct Copy should not enter session Clipboard History")
        app._launch_compact_item({"kind": "command", "id": reference["id"]})
        app.root.update()
        check(app.current_tab == "commands" and
              app.selected_command_id == reference["id"],
              "Specific command action did not open its exact record")
        app._return_to_compact()
        app.root.update()

        local_link = app.data["links"][0]
        launched = []
        previous_opener = app.open_shortcut
        app.open_shortcut = lambda item: launched.append(item["id"])
        try:
            app._launch_compact_item({"kind": "shortcut", "id": local_link["id"]})
            check(launched == [local_link["id"]],
                  "Shortcut tile did not dispatch through existing shortcut handler")
        finally:
            app.open_shortcut = previous_opener

        template_record = {
            "id": "test:extra-mini-template", "machine": "FortiGate",
            "category": "Diagnostics", "description": "Test ping",
            "command": "execute ping x.x.x.x",
        }
        template_record["template"] = smart.validate_template(
            smart.suggest_template(template_record["command"]),
            template_record["command"])
        app.command_library.append(template_record)
        try:
            app._launch_compact_item({"kind": "template", "id": template_record["id"]})
            app.root.update()
            check(app.current_tab == "commands" and
                  app.selected_command_id == template_record["id"],
                  "Smart Template tile did not select exact command")
            template_dialogs = [w for w in app.root.winfo_children()
                                if isinstance(w, tk.Toplevel)]
            check(template_dialogs, "Smart Template tile did not open fill form")
            cancel_buttons = [w for w in widgets(template_dialogs[-1])
                              if isinstance(w, tk.Button) and w.cget("text") == "Cancel"]
            check(cancel_buttons, "Smart Template tile has no Cancel action")
            cancel_buttons[0].invoke()
            app.root.update()
            check(not app._modal, "Smart Template dialog left modal state enabled")
        finally:
            app.command_library.remove(template_record)
        print("PASS: wheel paging and exact direct command, template, copy and shortcut actions")

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
        # Fully exercise fill-and-copy with synthetic reference data. The
        # entered address must not be persisted to user data or commands.json.
        from pocket import smart_templates as smart
        from pocket import template_ui
        example = {"id": "synthetic", "machine": "FortiGate", "category": "Diagnostics",
                   "description": "Synthetic test", "command": "execute ping x.x.x.x"}
        example["template"] = smart.validate_template(
            smart.suggest_template(example["command"]), example["command"])
        app._set_display_mode("mini")
        app.show_tab("commands")
        app.root.update()
        copied = []
        def capture_generated(command, ident):
            copied.append((command, ident))
            app._copy_generated_command(command, ident)
        template_ui.open_filler(app, example, on_copy=capture_generated)
        app.root.update()
        dialogs = [w for w in app.root.winfo_children() if isinstance(w, tk.Toplevel)]
        check(dialogs, "Synthetic Smart Template fill dialog did not open")
        dialog = dialogs[-1]
        entries = [w for w in widgets(dialog) if isinstance(w, tk.Entry)]
        check(entries, "Smart Template fill field missing")
        entries[0].insert(0, "192.0.2.10")
        app.root.update()
        # Copy is immediately below the completed command preview and remains
        # accessible as a real native button.
        check(any(isinstance(w, tk.Text) and
                  "execute ping 192.0.2.10" in w.get("1.0", "end-1c")
                  for w in widgets(dialog)),
              "Generated command preview did not update")
        copy_buttons = [w for w in widgets(dialog)
                        if isinstance(w, tk.Button) and w.cget("text") == "Copy command"]
        check(copy_buttons and copy_buttons[0].cget("state") == "normal",
              "Validated template cannot be copied")
        copy_buttons[0].invoke()
        app.root.update()
        check(copied == [("execute ping 192.0.2.10", "synthetic")],
              "Generated command did not use entered IP")
        check(not app._modal, "Fill form did not close")
        check(app._clipboard_last == "execute ping 192.0.2.10",
              "Generated text was not excluded from automatic clipboard monitoring")
        app._clipboard_poll()
        check(not any("192.0.2.10" in value.get("text", "")
                      for value in app.clipboard_items if isinstance(value, dict)),
              "Generated command leaked into clipboard history")
        check("192.0.2.10" not in app.path.read_text(encoding="utf-8")
              if app.path.exists() else True,
              "Filled command leaked to data file")
        print("PASS: Smart Template edit dialog in every layout, optional generated copy and privacy")

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
