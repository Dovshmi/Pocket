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

def menu_labels(menu):
    """A separator has no -label option on Windows or X11 Tk."""
    end = menu.index("end")
    if end is None:
        return []
    return [menu.entrycget(i, "label") if menu.type(i) != "separator" else ""
            for i in range(end + 1)]



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
    from pocket import app_info

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
        check(app.display_mode == "mini", "fresh data should start in Mini")
        # Author starts directly below Pocket's final letter, not its P.
        # Enabling Extra Mini must only add a small '_' action; neither
        # logo nor title may move when its visibility changes.
        header = app.header_credit.master
        name = next(w for w in header.winfo_children()
                    if isinstance(w, tk.Label) and w.cget("text") == "Pocket")
        original_name_x = name.winfo_rootx()
        original_logo_x = app.header_icon.winfo_rootx()
        check(app.header_credit.winfo_rootx() >=
              name.winfo_rootx() + name.winfo_width() - 2,
              "Mini credit must begin at the end of Pocket, not under the P")
        check(not any(isinstance(w, tk.Button) and w.cget("text") == "_"
                      for w in header.winfo_children()),
              "Extra Mini button displayed while option is disabled")
        app._set_extra_mini_enabled(True)
        app.root.update()
        header = app.header_credit.master
        mini_buttons = [w for w in header.winfo_children()
                        if isinstance(w, tk.Button) and w.cget("text") == "_"]
        check(len(mini_buttons) == 1 and mini_buttons[0].winfo_width() <= 30,
              "Extra Mini control should be one small underscore button")
        check(abs(mini_buttons[0].winfo_height() -
                  app.pin_button.winfo_height()) <= 1,
              "Mini Extra Mini button must match PIN height")
        name = next(w for w in header.winfo_children()
                    if isinstance(w, tk.Label) and w.cget("text") == "Pocket")
        check(name.winfo_rootx() == original_name_x and
              app.header_icon.winfo_rootx() == original_logo_x,
              "Extra Mini toggle must not shift the Pocket logo or title")
        app._set_extra_mini_enabled(False)
        app.root.update()
        header = app.header_credit.master
        check(not any(isinstance(w, tk.Button) and w.cget("text") == "_"
                      for w in header.winfo_children()),
              "Extra Mini control remained after the option was unchecked")
        check(app.root.winfo_width() == view_dimensions("mini")[0],
              "Mini geometry is wrong")
        check(app.current_tab == "notes", "Fresh Pocket must open Notes")
        check(app.data["last_tab"] == "notes", "Factory tab was not initialized")
        check(app.data["settings"]["display_mode"] == "mini",
              "Mini must be the saved factory mode")
        # Only the two requested starter links should appear inside Ushpelo.
        initial_links = app.data["links"]
        check([(link["title"], link["url"]) for link in initial_links] == [
            ("DashDash", "https://dashdash-tau.vercel.app"),
            ("My GitHub", "https://github.com/Dovshmi")],
              "Factory shortcuts are incorrect")
        folders = app.data["shortcut_folders"]
        check(len(folders["folders"]) == 1 and
              folders["folders"][0]["title"] == "Ushpelo",
              "Ushpelo default folder is missing")
        folder_id = folders["folders"][0]["id"]
        check(folders["children"][folder_id] ==
              [link["id"] for link in initial_links],
              "Factory shortcuts must appear in user-requested order")
        check(folders["root"] == ["f:" + folder_id],
              "Factory folder should be first and contain both shortcuts")
        check(app.data["tools"]["target"] == "8.8.8.8" and
              app.data["tools"]["ports_input"] == "21,22,443,80,8080,3389,53",
              "Factory TCP presets were not applied")
        check(not app.scanning, "Fresh profile must not initiate a TCP scan")
        # Verify that user navigation persists a preferred tool to the saved
        # profile, not just to this in-memory preview window.
        app.show_tab("ports")
        app.root.update()
        app._write_now()
        check(appmod["load_data"](app.path)["last_tab"] == "ports",
              "Active Ports tool was not persisted across restart")
        app.show_tab("links")
        app.root.update()
        app._write_now()
        check(appmod["load_data"](app.path)["last_tab"] == "links",
              "Active Shortcuts tool was not persisted across restart")
        app.show_tab("notes")
        app.root.update()
        print("PASS: Mini startup, Ushpelo links, TCP defaults and last-tab restore")

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
            check(app.header_credit.winfo_exists() and
                  app.header_credit.cget("text") == app_info.AUTHOR_CREDIT,
                  f"{mode}: Pocket author credit is missing")
            check(app.header_credit.cget("font") and
                  app.header_credit.winfo_manager() in ("place", "pack"),
                  f"{mode}: author credit has no usable layout")
            if mode == "normal":
                # The brand must sit immediately alongside its logo, not
                # float toward the center of the header.
                brand_container = app.header_credit.master
                brand_title = next(
                    w for w in brand_container.winfo_children()
                    if isinstance(w, tk.Label) and w.cget("text") == "Pocket")
                logo_right = app.header_icon.winfo_rootx() + app.header_icon.winfo_width()
                gap = brand_title.winfo_rootx() - logo_right
                check(0 <= gap <= 20,
                      "Normal Pocket branding drifted away from its logo")
                title_x = brand_title.winfo_rootx()
                logo_x = app.header_icon.winfo_rootx()
                app._set_extra_mini_enabled(True)
                app.root.update()
                header = app.header_credit.master.master
                actions = [w for w in header.winfo_children()
                           if isinstance(w, tk.Button) and w.cget("text") == "_"]
                check(len(actions) == 1 and
                      abs(actions[0].winfo_height() -
                          app.pin_button.winfo_height()) <= 1,
                      "Normal Extra Mini button must match PIN height")
                brand_title = next(
                    w for w in app.header_credit.master.winfo_children()
                    if isinstance(w, tk.Label) and w.cget("text") == "Pocket")
                check(brand_title.winfo_rootx() == title_x and
                      app.header_icon.winfo_rootx() == logo_x,
                      "Normal Extra Mini toggle shifted Pocket branding")
                app._set_extra_mini_enabled(False)
                app.root.update()
            # Audit the content gutter through every menu transition. A
            # scrolling page must be mounted beneath the original shell body,
            # never inside a scroll canvas left over from the previous tool.
            stable_shell_body = app._mini_root_body
            stable_shell_x = stable_shell_body.winfo_rootx() - app.root.winfo_rootx()
            stable_shell_width = stable_shell_body.winfo_width()
            for page in PANES:
                app.show_tab(page)
                app.root.update()
                check(app.current_tab == page, f"{mode}: {page} did not open")
                check(app.body.winfo_exists(), f"{mode}: missing page body {page}")
                check(app._mini_root_body is stable_shell_body and
                      stable_shell_body.winfo_exists(),
                      f"{mode}/{page}: lost the original tool-content frame")
                check(abs(stable_shell_body.winfo_rootx() -
                          app.root.winfo_rootx() - stable_shell_x) <= 2 and
                      abs(stable_shell_body.winfo_width() -
                          stable_shell_width) <= 2,
                      f"{mode}/{page}: content gutter shifted on menu switch")
                if app._tool_scroll_canvas is None:
                    check(app.body is stable_shell_body,
                          f"{mode}/{page}: tool was rendered in an old canvas")
                else:
                    check(app._tool_scroll_canvas.master is stable_shell_body,
                          f"{mode}/{page}: nested scrolling canvas shifted the content")
                # Capture every actual tool page in every working layout.
                capture(app, output, mode + "_" + page)
                if page == "ports" and mode == "mini":
                    check(app.host_var.get() == "8.8.8.8" and
                          app.ports_var.get() == "21,22,443,80,8080,3389,53",
                          "Mini TCP input must reflect factory ports")
                    check(app.port_source.get() == "local",
                          "Default port source must remain local")
                if mode == "mini" and page == "notes":
                    picker = app.mini_note_picker
                    options = tuple(picker["values"])
                    check(str(picker.cget("state")) == "readonly",
                          "Mini Notes must preserve the normal readonly dropdown")
                    check(not hasattr(picker, "_pocket_typeahead"),
                          "Mini Notes must not install the removed typing search")
                    # The chosen value must remain visible, but any text
                    # selection highlight should disappear after the popup.
                    picker.selection_range(0, tk.END)
                    picker.event_generate("<<ComboboxSelected>>")
                    app.root.update()
                    import time
                    time.sleep(.07)
                    app.root.update()
                    check(not picker.selection_present(),
                          "Mini Notes must clear closed dropdown text highlighting")
                    check(tuple(picker["values"]) == options,
                          "Mini Notes dropdown options changed unexpectedly")
                if mode == "mini" and page == "commands":
                    # Machine LEFT, category RIGHT, search full width beneath.
                    category, machine = app.command_category_picker, app.machine_picker
                    search = app.command_search_entry
                    check(machine.winfo_rootx() < category.winfo_rootx(),
                          "Mini CLI machine must be left of category")
                    check(abs(category.winfo_width() - machine.winfo_width()) <= 6,
                          "Mini CLI pickers must share the width equally")
                    check(search.winfo_rooty() >=
                          machine.winfo_rooty() + machine.winfo_height(),
                          "Mini CLI search must appear below both dropdowns")
                    check(search.winfo_width() >=
                          category.winfo_width() + machine.winfo_width() - 12,
                          "Mini CLI search must span the full filter width")
                    for picker in (machine, category):
                        check(str(picker.cget("state")) == "readonly",
                              "Mini CLI dropdowns must remain readonly")
                        check(not hasattr(picker, "_pocket_typeahead"),
                              "Mini CLI dropdown search must be removed")
                        selected_before = picker.get()
                        choices_before = tuple(picker["values"])
                        picker.selection_range(0, tk.END)
                        picker.event_generate("<<ComboboxSelected>>")
                        app.root.update()
                        import time
                        time.sleep(.07)
                        app.root.update()
                        check(not picker.selection_present(),
                              "Mini CLI must clear closed dropdown highlighting")
                        check(picker.get() == selected_before,
                              "Clearing CLI text highlight must preserve chosen option")
                        check(tuple(picker["values"]) == choices_before,
                              "Mini CLI must retain its normal dropdown options")
                if page == "clipboard" and app.clipboard_page == "text":
                    selected_history = app.clipboard_items[-1]
                    old_pin = selected_history["pinned"]
                    app.clipboard_list.selection_clear(0, tk.END)
                    old_index = next(i for i, entry in enumerate(app._clipboard_filtered)
                                     if entry["id"] == selected_history["id"])
                    app.clipboard_list.selection_set(old_index)
                    app._pin_clipboard_item()
                    app.root.update()
                    check(app._clipboard_filtered[0]["id"] == selected_history["id"],
                          f"{mode}: pinned clipboard item must be displayed first")
                    check(app._selected_clipboard_item()["id"] == selected_history["id"],
                          f"{mode}: clipboard selected item must survive pin reorder")
                    app._pin_clipboard_item()
                    app.root.update()
                    check(selected_history["pinned"] == old_pin,
                          f"{mode}: clipboard unpin did not restore item")
                if page == "commands" and sys.platform == "win32":
                    # The old Win32 overlay left the placeholder inside the
                    # actual edit control even after focus. Test in Pocket,
                    # not only in a standalone Tk host window.
                    search = app.command_search_entry
                    check(bool(getattr(search, "native_hwnd", None)),
                          f"{mode}: CLI search has no native Windows edit")
                    search.focus_force()
                    import time
                    for _ in range(12):
                        app.root.update()
                        if (not app._command_placeholder_active and
                                search.get() == ""):
                            break
                        time.sleep(.035)
                    check(not app._command_placeholder_active and search.get() == "",
                          f"{mode}: CLI search placeholder was not cleared on focus "
                          f"(flag={app._command_placeholder_active}, var={app.command_query.get()!r}, "
                          f"native={search.get()!r}, focused={search.has_native_focus()}, "
                          f"tk_focus={app.root.focus_get()!s})")
                    for char in "ping":
                        search._send(0x0102, ord(char), 1)  # WM_CHAR from native keyboard
                    for _ in range(12):
                        app.root.update()
                        if app.command_query.get() == "ping":
                            break
                        time.sleep(.035)
                    check(app.command_query.get() == "ping",
                          f"{mode}: typed native CLI search not synchronized")
                    search.delete(0, tk.END)
                    app._command_focus_out()
                if page == "notes" and sys.platform == "win32":
                    # A Win32 child posts WM_CONTEXTMENU. Confirm the real
                    # Pocket popup (not Windows' long white default) appears.
                    field = app.title_entry
                    check(bool(getattr(field, "native_hwnd", None)),
                          f"{mode}: Notes title is not backed by Windows Edit")
                    import time
                    px, py = field.winfo_rootx() + 10, field.winfo_rooty() + 9
                    lp = ((py & 0xffff) << 16) | (px & 0xffff)
                    # Windows' TrackPopupMenu blocks a headless GUI test.
                    # Intercept only *posting*, not the actual native HWND
                    # routing or Pocket's menu construction and callbacks.
                    from unittest.mock import patch
                    observed = []
                    def inspect_menu(menu, x, y, *args, **kwargs):
                        observed.append((menu_labels(menu), x, y))
                    try:
                        with patch.object(tk.Menu, "tk_popup", inspect_menu):
                            field._send(0x007B, field.native_hwnd, lp)
                            for _ in range(15):
                                app.root.update()
                                if observed:
                                    break
                                time.sleep(.035)
                    finally:
                        app._dismiss_input_context_menu()
                    check(observed and all(v in observed[0][0] for v in (
                        "Undo", "Redo", "Cut", "Copy", "Paste", "Select all")),
                        f"{mode}: native right click did not construct Pocket menu: {observed}")
                if page == "notes":
                    # Windows RichEdit is an HWND distinct from Tk's Entry
                    # controls. Explicitly exercise the reported Mini failure:
                    # click Title / Phone after typing in the note body.
                    if sys.platform == "win32" and app.bidi_editor is not None:
                        # The native white scrollbar must be hidden, not just
                        # recolored. Keep Win32 multiline/autoscroll styles.
                        import ctypes
                        hwnd = ctypes.c_void_p(app.bidi_editor._hwnd)
                        user32 = ctypes.windll.user32
                        user32.GetWindowLongW.argtypes = (
                            ctypes.c_void_p, ctypes.c_int)
                        user32.GetWindowLongW.restype = ctypes.c_long
                        flags = user32.GetWindowLongW(hwnd, -16)
                        check(not (flags & 0x00200000),
                              f"{mode}: RichEdit still shows a native vertical scrollbar")
                        check(flags & 0x00000040,
                              f"{mode}: RichEdit lost keyboard/caret autoscroll")
                        # Long notes must remain navigable without showing a
                        # scrollbar; test the actual native mouse-wheel path.
                        saved_text = app.bidi_editor.get_text()
                        try:
                            app.bidi_editor.set_text(
                                "\n".join(f"Scroll line {i}" for i in range(120)))
                            app.root.update()
                            before = app.bidi_editor._send(0x00CE)
                            app.bidi_editor._send(0x020A, (0xFF88 << 16), 0)
                            app.root.update()
                            after = app.bidi_editor._send(0x00CE)
                            check(after > before,
                                  f"{mode}: scrolling long notes no longer works")
                        finally:
                            app.bidi_editor.set_text(saved_text)
                            app.root.update()
                        app.root.focus_force()
                        app.root.update()
                        for field, title in ((app.phone_entry, "Phone"),
                                             (app.title_entry, "Title")):
                            app.bidi_editor.focus_set()
                            app.root.update()
                            field.event_generate("<ButtonPress-1>", x=6, y=6)
                            app.root.update()
                            check(
                                (field.has_native_focus() if getattr(field, "native_hwnd", None)
                                 else app.root.focus_get() is field),
                                f"{mode}: click did not move keyboard focus to {title}")
                            check(not app.bidi_editor.has_focus(),
                                  f"{mode}: RichEdit still owns typing after {title} click")
                        # A native popup may be dismissed without <Unmap>;
                        # the next field click must clear its stale modal flag.
                        stale = app._build_note_context_menu()
                        app._note_context_menu = stale
                        app._note_context_menu_was_modal = False
                        app._modal = True
                        app.bidi_editor.focus_set()
                        app.phone_entry.event_generate("<ButtonPress-1>",
                                                       x=6, y=6)
                        app.root.update()
                        check(not app._modal and app._note_context_menu is None,
                              f"{mode}: dismissed Notes popup trapped modal state")
                        check(
                            (app.phone_entry.has_native_focus()
                             if getattr(app.phone_entry, "native_hwnd", None)
                             else app.root.focus_get() is app.phone_entry)
                            and not app.bidi_editor.has_focus(),
                            f"{mode}: Phone remains trapped after popup dismiss")
                        stale.destroy()
                    # Compact native submenus explain editor actions and
                    # which Pocket tools require a selected text fragment.
                    from unittest.mock import patch
                    with patch.object(app, "_selected_note_text", return_value="8.8.8.8"):
                        note_menu = app._build_note_context_menu()
                    labels = menu_labels(note_menu)
                    check("Text direction" in labels and "Note actions" in labels,
                          f"{mode}: Notes right-click lacks clear action groups")
                    check("Use selected text in Pocket" in labels,
                          f"{mode}: selected text tool group is missing")
                    edit_index = labels.index("Copy selected text")
                    check(note_menu.entrycget(edit_index, "state") == "normal",
                          f"{mode}: Copy selected text must be enabled")
                    submenu_path = note_menu.entrycget(
                        labels.index("Use selected text in Pocket"), "menu")
                    pocket_menu = app.root.nametowidget(submenu_path)
                    choices = menu_labels(pocket_menu)
                    check(any("port check" in text for text in choices),
                          f"{mode}: selected IP action missing from Notes")
                    note_menu.destroy()
                    with patch.object(app, "_selected_note_text", return_value=""):
                        no_selection = app._build_note_context_menu()
                    empty_labels = menu_labels(no_selection)
                    check("Select text to use Pocket tools" in empty_labels,
                          f"{mode}: Notes must explain why selection tools are unavailable")
                    from tkinter import font as tkfont
                    cut_index = empty_labels.index("Cut selected text")
                    check(no_selection.entrycget(cut_index, "state") == "disabled",
                          f"{mode}: Cut without a selection must be disabled")
                    check(no_selection.cget("disabledforeground") ==
                          no_selection.cget("foreground"),
                          f"{mode}: disabled menu labels should not be dimmed")
                    cut_font = no_selection.entrycget(cut_index, "font")
                    check(cut_font and tkfont.Font(root=app.root, font=cut_font
                              ).actual("overstrike"),
                          f"{mode}: disabled Cut needs a visible strikethrough")
                    placeholder_index = empty_labels.index(
                        "Select text to use Pocket tools")
                    placeholder_font = no_selection.entrycget(
                        placeholder_index, "font")
                    check(placeholder_font and tkfont.Font(
                        root=app.root, font=placeholder_font).actual("overstrike"),
                          f"{mode}: disabled placeholder also needs strikethrough")
                    no_selection.destroy()
                    # State changes must restore the normal font, and keep
                    # disabled actions non-invokable (not just visually dim).
                    from pocket import menu_style
                    dynamic_menu = menu_style.Menu(
                        app.root, tearoff=False, fg="#E8ECF6",
                        disabledforeground="#666666")
                    check(str(dynamic_menu.cget("disabledforeground")).lower() == "#e8ecf6",
                          f"{mode}: disabled items were dimmed despite override")
                    hits = []
                    dynamic_menu.add_command(
                        label="Unavailable", state="disabled",
                        command=lambda: hits.append("invoked"))
                    dynamic_menu.invoke(0)
                    check(not hits, f"{mode}: disabled item executed")
                    dynamic_menu.entryconfigure(0, state="normal")
                    check(dynamic_menu.entrycget(0, "font") != cut_font,
                          f"{mode}: enabled item kept strikethrough font")
                    dynamic_menu.invoke(0)
                    check(hits == ["invoked"],
                          f"{mode}: enabled item failed to execute")
                    dynamic_menu.entryconfig(0, state="disabled")
                    check(tkfont.Font(
                        root=app.root, font=dynamic_menu.entrycget(0, "font")
                        ).actual("overstrike"),
                          f"{mode}: re-disabled menu action lost strikethrough")
                    dynamic_menu.destroy()
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
                    check(toggle.winfo_rootx() > app.body.winfo_rootx() +
                          app.body.winfo_width() // 2,
                          f"{mode}: Clipboard switch must be aligned to the right")
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
                    canvas = app.clipboard_images_canvas
                    for keystroke in ("<Left>", "<Right>", "<Control-c>",
                                      "<Return>", "<Delete>"):
                        check(bool(canvas.bind(keystroke)),
                              f"{mode}: image gallery is missing {keystroke}")
                    if mode == "mini":
                        original_images = list(app.clipboard_images)
                        for color in ((32, 91, 162), (11, 149, 85)):
                            check(clipboard_images.add_image(
                                app.clipboard_images,
                                Image.new("RGB", (160, 80), color)),
                                "Mini: extra image was not added")
                        app._clipboard_selected_image_id = app.clipboard_images[0]["id"]
                        clipboard_gallery.refresh_images(app, force=True)
                        app.root.update()
                        check(len(app._clipboard_gallery_tiles) == 3,
                              "Mini: horizontal gallery must render all cards")
                        frames = [app._clipboard_gallery_tiles[item["id"]]
                                  for item in app.clipboard_images]
                        check(len({tile.winfo_y() for tile in frames}) == 1,
                              "Mini: images must all share a horizontal row")
                        check(frames[0].winfo_x() < frames[1].winfo_x()
                              < frames[2].winfo_x(),
                              "Mini: image cards must advance left to right")
                        check(canvas.xview()[1] - canvas.xview()[0] < 0.99,
                              "Mini: horizontal overflow must enable scrolling")
                        canvas.focus_force()
                        canvas.event_generate("<Right>")
                        app.root.update()
                        check(app._clipboard_selected_image_id ==
                              app.clipboard_images[1]["id"],
                              "Mini: Right key must select the next image")
                        canvas.event_generate("<Right>")
                        app.root.update()
                        check(app._clipboard_selected_image_id ==
                              app.clipboard_images[2]["id"],
                              "Mini: Right key must select third image")
                        check(canvas.xview()[0] > 0.01,
                              "Mini: keyboard navigation must scroll horizontally")
                        check("3 / 3 selected" in app.clipboard_images_status.cget("text"),
                              "Mini: selected-image counter is incorrect")
                        selected_before_switch = app._clipboard_selected_image_id
                        app.clipboard_page_buttons["text"].invoke()
                        app.root.update()
                        app.clipboard_page_buttons["images"].invoke()
                        app.root.update()
                        check(app._clipboard_selected_image_id == selected_before_switch,
                              "Mini: chosen image was lost on page switch")
                        capture(app, output, "mini_clipboard_horizontal_gallery")
                        app.clipboard_images[:] = original_images
                        app._clipboard_selected_image_id = original_images[0]["id"]
                        clipboard_gallery.refresh_images(app, force=True)
                        app.root.update()
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
                    # A native Listbox defaults to a thick white focus frame
                    # and legacy Clipboard rows had three leading spaces.
                    # The border, data and gutters should match the other
                    # Pocket tools in Normal, Mini and Dashboard.
                    listbox = app.clipboard_list
                    text_panel = app.clipboard_text_page
                    left_inset = (listbox.winfo_rootx() -
                                  text_panel.winfo_rootx())
                    right_inset = (text_panel.winfo_rootx() +
                                   text_panel.winfo_width() -
                                   listbox.winfo_rootx() -
                                   listbox.winfo_width())
                    check(left_inset >= 0 and right_inset >= 0 and
                          abs(left_inset - right_inset) <= 1,
                          f"{mode}: Clipboard text box has uneven left/right gutters")
                    check(int(listbox.cget("highlightthickness")) == 1 and
                          int(listbox.cget("borderwidth")) == 0,
                          f"{mode}: Clipboard list still uses the legacy thick frame")
                    from pocket import clipboard_gallery
                    palette = clipboard_gallery.themes.palette(app.theme)
                    check(listbox.winfo_rgb(listbox.cget("highlightbackground")) ==
                          listbox.winfo_rgb(palette["BORDER"]),
                          f"{mode}: Clipboard border does not match other inputs")
                    check(all(listbox.get(i) ==
                              clipboard_gallery.text_row_label(item)
                              for i, item in enumerate(app._clipboard_filtered)),
                          f"{mode}: Clipboard rows gained unwanted left padding")
                    check(app.clipboard_query_entry.winfo_width() <
                          app.clipboard_text_page.winfo_width() * 0.8,
                          f"{mode}: Clipboard search should be narrow")
                    check(app.clipboard_query_entry.winfo_height() < 36,
                          f"{mode}: Clipboard search should be shorter")
                    actions_y = app.clipboard_text_actions.winfo_rooty()
                    list_y = app.clipboard_list.winfo_rooty()
                    if mode == "mini":
                        check(actions_y >= list_y + app.clipboard_list.winfo_height(),
                              "Mini: Copy/Pin/Delete must be beneath the text history")
                    else:
                        check(actions_y < list_y,
                              f"{mode}: keep text actions above the list")
                    app.clipboard_list.selection_clear(0, tk.END)
                    app.clipboard_list.selection_set(0)
                    expected_text = app._clipboard_filtered[0]["text"]
                    menu_colors = clipboard_gallery.themes.palette(app.theme)
                    sample_menu = clipboard_gallery.build_text_context_menu(
                        app, menu_colors, {"text": "8.8.8.8", "pinned": False})
                    main_labels = menu_labels(sample_menu)
                    check("Copy full text" in main_labels and
                          "Use text in Pocket" in main_labels and
                          "TRANSLATE EN/HE" not in main_labels,
                          f"{mode}: Clipboard right-click groups missing")
                    tool_path = sample_menu.entrycget(
                        main_labels.index("Use text in Pocket"), "menu")
                    tool_menu = app.root.nametowidget(tool_path)
                    tool_labels = menu_labels(tool_menu)
                    check("TRANSLATE EN/HE" in tool_labels,
                          f"{mode}: clipboard translation must be inside Use text in Pocket")
                    check("Prepare TCP port check" in tool_labels and
                          "Open Subnet Calculator" in tool_labels and
                          "Create a new Note from text" in tool_labels,
                          f"{mode}: Clipboard context tool actions missing")
                    check("Open MAC lookup with address" not in tool_labels,
                          f"{mode}: irrelevant MAC action should be hidden for IP")
                    sample_menu.destroy()
                    converted_menu = clipboard_gallery.build_text_context_menu(
                        app, menu_colors, {"text": "akuo", "pinned": False})
                    labels = menu_labels(converted_menu)
                    submenu_name = converted_menu.entrycget(
                        labels.index("Use text in Pocket"), "menu")
                    convert_submenu = app.root.nametowidget(submenu_name)
                    convert_labels = menu_labels(convert_submenu)
                    convert_submenu.invoke(convert_labels.index("TRANSLATE EN/HE"))
                    app.root.update()
                    check(app.root.clipboard_get() == "שלום",
                          f"{mode}: context keyboard layout must copy corrected text")
                    converted_menu.destroy()
                    # Conversion legitimately prepends corrected text to the
                    # session history and refreshes the list selection.
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
                if page == "settings":
                    check(app._convert_hotkey_hint().startswith("Ctrl+Alt+F9"),
                          f"{mode}: converter shortcut was not restored")
                    labels = [str(widget.cget("text")) for widget in widgets(app.body)
                              if isinstance(widget, tk.Label) and "text" in widget.keys()]
                    check(any("Fix EN / HE keyboard layout" in t or
                              "FIX KEYBOARD LAYOUT" in t for t in labels),
                          f"{mode}: converter hotkey is missing from Settings")
                    # All working modes share the modern selection, palette
                    # and keyboard-accessible switch components.
                    common = app.settings_controls
                    required = {"mode_normal", "mode_mini", "mode_dashboard",
                                "theme_blue", "theme_purple", "extra_mini",
                                "change_hotkey", "change_convert_hotkey",
                                "quick_search", "clipboard_paused",
                                "sensitive_filter"}
                    required.update("tool_" + key
                                    for key, _ in app.VISIBLE_TABS_REFERENCE)
                    required.update("image_limit_" + str(value)
                                    for value in (10, 15, 20, 25, 30))
                    check(required.issubset(common),
                          f"{mode}: modern Settings options are missing")
                    check(all(isinstance(common[key], tk.Checkbutton) and
                              not bool(int(common[key].cget("indicatoron")))
                              for key in ("extra_mini", "clipboard_paused",
                                          "sensitive_filter")),
                          f"{mode}: legacy checkbox indicators remain visible")
                    check(common["theme_blue"].winfo_exists() and
                          common["mode_mini"].winfo_exists(),
                          f"{mode}: themed selection cards disappeared")
                    old_limit = app.settings["clipboard_image_limit"]
                    common["image_limit_30"].invoke()
                    check(app.settings["clipboard_image_limit"] == 30,
                          f"{mode}: image history capacity did not update")
                    check("✓" in common["image_limit_30"].cget("text"),
                          f"{mode}: selected image limit is not highlighted")
                    common["image_limit_" + str(old_limit)].invoke()
                    check(app.settings["clipboard_image_limit"] == old_limit,
                          f"{mode}: prior image limit was not restored")
                if page == "settings":
                    check(app.settings_footer_author.winfo_exists() and
                          app.settings_footer_author.cget("text") ==
                          app_info.AUTHOR_CREDIT,
                          f"{mode}: Settings author credit is missing")
                    check(app.settings_footer_version.winfo_exists() and
                          app.settings_footer_version.cget("text") ==
                          "Version " + app_info.version_label(),
                          f"{mode}: Settings version is incorrect")
                if page == "settings" and mode == "dashboard":
                    controls = app.dashboard_settings_controls
                    check(all(key in controls for key in (
                        "mode_normal", "mode_mini", "mode_dashboard",
                        "extra_mini", "customize_launcher",
                        "change_hotkey", "change_convert_hotkey", "quick_search",
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
                if page == "links":
                    import copy
                    from types import SimpleNamespace
                    from pocket import shortcut_folders as sf
                    from pocket import shortcut_sections_ui as folders_ui
                    old_layout = copy.deepcopy(app.data["shortcut_folders"])
                    check(app.shortcut_add_button.cget("text") == "+ Add ▾",
                          f"{mode}: only one Add dropdown must be shown")
                    from unittest.mock import patch
                    with patch.object(folders_ui, "show_add_menu") as add_menu:
                        app.shortcut_add_button.invoke()
                        add_menu.assert_called_once_with(
                            app, app.shortcut_add_button)
                    sample = app.data["links"][0]
                    folder_id = sf.add_folder(app.data["shortcut_folders"],
                                              "Network tools")
                    # Put the folder first, within the Mini viewport.
                    # The factory shortcuts are now *inside* Ushpelo, so use
                    # its root-row folder key instead of a nested link.
                    first_row = app.data["shortcut_folders"]["root"][0]
                    check(sf.move(app.data["shortcut_folders"],
                                  sf.folder_key(folder_id),
                                  first_row, "before"),
                          f"{mode}: could not order new folder ahead of shortcuts")
                    app.refresh_links()
                    app.root.update()
                    check(folder_id in app.shortcut_folder_headers,
                          f"{mode}: shortcut folder header was not displayed")
                    heading = app.shortcut_folder_headers[folder_id]
                    sample_handle = app.shortcut_drag_handles[
                        sf.link_key(sample["id"])]
                    card = sample_handle.master
                    check(heading.winfo_height() < card.winfo_height(),
                          f"{mode}: folder heading must be shorter than shortcut cards")
                    folder_grip = app.shortcut_drag_handles[
                        sf.folder_key(folder_id)]
                    check(sample_handle.winfo_rootx() >
                          card.winfo_rootx() + card.winfo_width() // 2,
                          f"{mode}: shortcut drag grip must be on the right")
                    check(folder_grip.winfo_rootx() >
                          heading.winfo_rootx() + heading.winfo_width() // 2,
                          f"{mode}: folder drag grip must be on the right")
                    check(folder_id not in [item.get("id") for item in app.data["links"]],
                          f"{mode}: folders must not be treated as launchable links")
                    # Simulate the same dedicated drag grip callbacks that the
                    # real UI receives, from an unfiled card onto a folder heading.
                    x = sample_handle.winfo_rootx() + sample_handle.winfo_width() // 2
                    y = sample_handle.winfo_rooty() + sample_handle.winfo_height() // 2
                    destination_x = heading.winfo_rootx() + heading.winfo_width() // 2
                    destination_y = heading.winfo_rooty() + heading.winfo_height() // 2
                    folders_ui.begin_drag(
                        app, sf.link_key(sample["id"]),
                        SimpleNamespace(x_root=x, y_root=y))
                    folders_ui.drag_motion(
                        app, SimpleNamespace(x_root=destination_x,
                                             y_root=destination_y))
                    folders_ui.finish_drag(
                        app, SimpleNamespace(x_root=destination_x,
                                             y_root=destination_y))
                    app.root.update()
                    check(sf.link_folder(app.data["shortcut_folders"],
                                         sample["id"]) == folder_id,
                          f"{mode}: mouse drag failed to move a shortcut into folder")
                    check(sf.link_key(sample["id"]) in app.shortcut_drag_handles,
                          f"{mode}: moved shortcut is not visible in open folder")
                    before_drop = len(app.data["links"])
                    app._shortcut_dropped(
                        SimpleNamespace(data="https://example.org/pocket-drop-check"),
                        folder_id=folder_id)
                    app.root.update()
                    check(len(app.data["links"]) == before_drop + 1,
                          f"{mode}: external URL drop must create one shortcut")
                    imported = next(
                        link for link in app.data["links"]
                        if link["url"] == "https://example.org/pocket-drop-check")
                    check(sf.link_folder(app.data["shortcut_folders"],
                                         imported["id"]) == folder_id,
                          f"{mode}: external URL was not saved inside folder")
                    check(not app.form_holder.winfo_manager(),
                          f"{mode}: folder drop must not open a separate Add form")
                    check(sf.set_expanded(app.data["shortcut_folders"],
                                          folder_id, False),
                          f"{mode}: folder did not collapse")
                    app.refresh_links()
                    app.root.update()
                    check(sf.link_key(sample["id"]) not in app.shortcut_drag_handles,
                          f"{mode}: collapsed folder still renders its shortcut card")
                    check(sf.delete_folder(app.data["shortcut_folders"], folder_id),
                          f"{mode}: folder deletion was rejected")
                    check(sf.link_key(sample["id"]) in app.data["shortcut_folders"]["root"],
                          f"{mode}: deleting a folder must preserve its shortcut")
                    check(sf.link_key(imported["id"]) in app.data["shortcut_folders"]["root"],
                          f"{mode}: deleting a folder must preserve imported shortcuts")
                    app._delete_link(imported)
                    app.root.update()
                    app.data["shortcut_folders"] = old_layout
                    app.refresh_links()
                    app.root.update()
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
                    check(int(app.command_tree.cget("height")) >= 5,
                          "Normal Commands list should request five rows")
                    results = app.command_tree.get_children()
                    check(len(results) >= 4,
                          "Normal Command Helper has too few test commands")
                    # Treeview(height=5) alone does not guarantee visibility:
                    # the PanedWindow used to clip the fourth actual row.
                    fourth = app.command_tree.bbox(results[3])
                    check(bool(fourth) and
                          fourth[1] + fourth[3] <= app.command_tree.winfo_height(),
                          f"Normal Command Helper must display four FULL rows "
                          f"(fourth={fourth!r}, tree_height={app.command_tree.winfo_height()}, "
                          f"results_pane={app.command_panes.panes()[0] if app.command_panes.panes() else 'none'}, "
                          f"pane_height={app.command_panes.winfo_height()}, root_height={app.root.winfo_height()})")
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
