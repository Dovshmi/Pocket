"""Pocket v1.41 real Tk resize/reflow smoke, Windows or Xvfb.

Uses an isolated temporary profile, with no user data or network operations.
"""
from __future__ import annotations

import os
from pathlib import Path
import runpy
from types import SimpleNamespace
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pocket import adaptive_window as adaptive
from pocket import mini_layout as mini


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def check_filled_rows(tiles):
    rows = {}
    for tile in tiles:
        if tile.winfo_ismapped():
            rows.setdefault(tile.master, []).append(tile)
    check(bool(rows), "no visible navigation rows")
    for row, children in rows.items():
        left = min(tile.winfo_x() for tile in children)
        right = max(tile.winfo_x() + tile.winfo_width() for tile in children)
        check(left <= 2 and row.winfo_width() - right <= 2,
              f"navigation row has unused edges: {left}, {row.winfo_width() - right}")


with tempfile.TemporaryDirectory(prefix="pocket-adaptive-") as profile:
    os.environ["APPDATA"] = profile
    appmod = runpy.run_path(str(ROOT / "app.pyw"), run_name="adaptive_smoke")
    app = appmod["PocketDesk"](preview=True)
    try:
        app.root.geometry("346x530+20+20")
        app.root.update()
        check(app.display_mode == "mini", "expected Mini at startup")
        check(len(app._resize_handles) == 1, "only one visible corner grip required")
        check(app._resize_handles[0].cget("text") == "◢", "bottom-right triangle missing")
        check(app._resize_tag in app.root.bindtags(), "invisible resize hit testing missing")
        for px, py, sides in ((0, 200, "w"), (345, 200, "e"), (150, 0, "n"), (150, 529, "s"), (0, 0, "nw"), (345, 0, "ne"), (0, 529, "sw"), (345, 529, "se")):
            event = SimpleNamespace(widget=app.root, x_root=app.root.winfo_rootx()+px, y_root=app.root.winfo_rooty()+py)
            check(app._resize_edges_at(event) == sides, f"invisible edge {sides} missing")
        original_note_ids = [note["id"] for note in app.data["notes"]]
        original_links = [(item["id"], item["url"]) for item in app.data["links"]]

        area = app._screen_work_area(30, 30)
        target_width = min(1100, area[2] - 28)
        target_height = min(760, area[3] - 28)
        check(target_width >= adaptive.NORMAL_WIDTH,
              "test display is too small for Normal layout")

        x, y = app.root.winfo_x(), app.root.winfo_y()
        width, height = app.root.winfo_width(), app.root.winfo_height()
        start = SimpleNamespace(x_root=x + width, y_root=y + height)
        finish = SimpleNamespace(x_root=start.x_root + target_width - width,
                                 y_root=start.y_root + target_height - height)
        app._begin_window_resize(start, "se")
        app._finish_window_resize(finish)
        app.root.update()

        expected = adaptive.layout_for(target_width, target_height)
        check(app.display_mode == expected,
              f"responsive layout mismatch: {app.display_mode} != {expected}")
        check(app.root.winfo_width() == target_width, "width not applied")
        check(app.root.winfo_height() == target_height, "height not applied")
        check(app.data["window_size"] == {
            "width": target_width, "height": target_height}, "size not saved")
        check([note["id"] for note in app.data["notes"]] == original_note_ids,
              "Notes changed during resize")
        check([(item["id"], item["url"]) for item in app.data["links"]] == original_links,
              "Shortcuts changed during resize")
        print("PASS: live resize, responsive layout, no lost records")

        # Extra Mini is never entered by a width threshold.
        app._set_extra_mini_enabled(True)
        app.root.update()
        app._return_to_compact()
        app.root.update()
        check(app.display_mode == "compact", "Extra Mini launcher did not open")
        check((app.root.winfo_width(), app.root.winfo_height()) ==
              mini.view_dimensions("compact"), "Extra Mini size changed")
        check(not app._resize_handles, "Extra Mini must not have resize grips")
        app._expand_from_extra_mini()
        app.root.update()
        check(app.display_mode == expected, "working layout was not restored")
        check((app.root.winfo_width(), app.root.winfo_height()) ==
              (target_width, target_height), "working size was not restored")
        print("PASS: Extra Mini remains fixed and restores the last work size")

        # User-selected Settings presets still work and can be resized again.
        app._set_display_mode("normal")
        app.root.update()
        check(app.display_mode == "normal", "Normal preset not selected")
        preset_width, preset_height = mini.view_dimensions("normal")
        preset_width = min(preset_width, max(240, area[2] - area[0] - 12))
        preset_height = min(preset_height, max(240, area[3] - area[1] - 12))
        check((app.root.winfo_width(), app.root.winfo_height()) ==
              (preset_width, preset_height), "Normal preset must fit work area")
        check(len(app._resize_handles) == 1, "single grip missing after layout rebuild")
        print("PASS: Settings size presets continue to work")

        # Normal More uses inline rows, keeps selection stable, and reclaims
        # unused overflow as width increases without rebuilding the tool page.
        for key in ("notes", "links", "ports", "mac", "commands", "subnet",
                    "clipboard", "reminders", "extra"):
            app._set_visible_tab(key, True)
        app.root.update()
        check("more" in app.normal_icon_tabs, "Normal overflow missing")
        from pocket import icon_themes
        palette = icon_themes.palette(app.theme)
        app.show_tab("commands")
        app.root.update()
        old_tile = app.normal_icon_tabs["commands"]
        old_tile.focus_force()
        app.show_tab("subnet")
        app.root.update()
        active_tile = app.normal_icon_tabs["subnet"]
        check(active_tile.cget("bg") == palette["ACCENT_DARK"],
              "Normal active tile must match Mini fill")
        check(old_tile.cget("bg") == palette["BG"],
              "Previous menu retained selected styling")
        check(all(int(tile.cget("highlightthickness")) == 0
                  for tile in app.normal_icon_tabs.values()),
              "Normal menu retained an unwanted focus outline")
        check(active_tile.master.winfo_height() == 45,
              "Normal tile should match Mini height")
        check_filled_rows([tile.master for tile in app.normal_icon_tabs.values()])
        hidden = app.normal_overflow_keys
        app.normal_icon_tabs["more"].invoke()
        app.root.update()
        check(app.normal_icon_tabs["more"].cget("text") == "Less", "More did not expand")
        check(all(app.normal_icon_tabs[k].winfo_ismapped() for k in hidden),
              "Normal overflow tiles must be inline and visible")
        check_filled_rows([tile.master for tile in app.normal_icon_tabs.values()])
        app.show_tab(hidden[0])
        app.root.update()
        check(app.normal_overflow_keys == hidden, "selection changed menu order")
        app.normal_icon_tabs["more"].invoke()
        app.root.update()
        check(not any(app.normal_icon_tabs[k].winfo_ismapped() for k in hidden),
              "Less did not hide overflow")
        app.root.geometry("660x550+20+20")
        app.root.update()
        check(not app.normal_overflow_keys, "wider Normal should fit all tools")
        check("more" not in app.normal_icon_tabs, "unnecessary More remains")
        check_filled_rows([tile.master for tile in app.normal_icon_tabs.values()])
        app._set_display_mode("mini")
        app.root.update()
        original = len(app._mini_overflow_keys)
        check_filled_rows([parts[0] for parts in app.mini_icon_tabs.values()])
        app._toggle_mini_more()
        app.root.update()
        check_filled_rows([parts[0] for parts in app.mini_icon_tabs.values()])
        app.root.geometry("445x530+20+20")
        app.root.update()
        check(len(app._mini_overflow_keys) < original, "Mini did not reclaim slots")
        check_filled_rows([parts[0] for parts in app.mini_icon_tabs.values()])
        for key in ("clipboard", "reminders", "extra", "mac"):
            app._set_visible_tab(key, False)
        app.root.update()
        check_filled_rows([parts[0] for parts in app.mini_icon_tabs.values()])
        print("PASS: responsive Mini and Normal fill each visible row")

        def drag_icon(source, target, after=False):
            tx = target.winfo_rootx() + (target.winfo_width() - 5 if after else 5)
            ty = target.winfo_rooty() + 8
            source.event_generate("<ButtonPress-1>", x=8, y=8)
            source.event_generate("<B1-Motion>", x=tx - source.winfo_rootx(),
                                  y=ty - source.winfo_rooty())
            source.event_generate("<ButtonRelease-1>", x=tx - source.winfo_rootx(),
                                  y=ty - source.winfo_rooty())
            app.root.update()

        for key in ("clipboard", "reminders", "extra", "mac"):
            app._set_visible_tab(key, True)
        app._set_display_mode("normal")
        app.root.update()
        if app.normal_icon_tabs["more"].cget("text") == "More":
            app.normal_icon_tabs["more"].invoke()
            app.root.update()
        source = app.normal_overflow_keys[-1]
        first = next(k for k in app.normal_icon_tabs if k != "more")
        drag_icon(app.normal_icon_tabs[source], app.normal_icon_tabs[first])
        check(app.settings["menu_order"][0] == source, "Normal drag did not save order")
        check(next(iter(app.normal_icon_tabs)) == source, "Normal drag did not reflow")
        drag_icon(app.normal_icon_tabs["settings"], app.normal_icon_tabs[source])
        check(app.settings["menu_order"][0] == "settings", "Settings drag failed")
        app._set_display_mode("mini")
        app.root.update()
        check(next(iter(app.mini_icon_tabs)) == "settings", "Mini did not reuse order")
        print("PASS: real menu drag and shared ordering")

        app._set_display_mode("normal")
        app.show_tab("clipboard")
        from pocket import clipboard_gallery
        clipboard_gallery.show_page(app, "text")
        for width in (480, 660):
            app.root.geometry(f"{width}x600+20+20")
            app.root.update()
            check(app.clipboard_pause_button.winfo_ismapped(), "Pause not visible")
            check(app.clipboard_text_actions.pack_info()["side"] == "bottom",
                  "Clipboard actions must stay below history")
            check(app.clipboard_query_entry.winfo_width() > 120, "Search did not expand")
            check(app.clipboard_list.winfo_height() > 80, "History too short")
        clipboard_gallery.show_page(app, "images")
        app.root.update()
        check(app.clipboard_image_pause_button.winfo_ismapped(), "Image Pause missing")
        app.show_tab("mac")
        app.root.update()

        def widget_texts(parent):
            for child in parent.winfo_children():
                if "text" in child.keys():
                    yield str(child.cget("text"))
                yield from widget_texts(child)

        labels = list(widget_texts(app.body))
        check("Update IEEE DB" in labels, "MAC update button missing")
        check("Import CSV" not in labels and "Get CSV ↗" not in labels,
              "MAC CSV actions still visible")
        app.mac_results = [
            {"mac": "00:11:22:33:44:01", "vendor": "Cisco", "registry": "MA-L"},
            {"mac": "00:11:22:33:44:02", "vendor": "Cisco", "registry": "MA-L"},
            {"mac": "00:11:22:33:44:03", "vendor": "Juniper", "registry": "MA-L"},
            {"mac": "00:11:22:33:44:04", "vendor": "Unknown / unregistered", "registry": "—"},
        ]
        app._show_mac_results("Local")
        app.root.update()
        check(not app.mac_summary_panel.winfo_ismapped(), "Vendor summary must start collapsed")
        app._toggle_mac_summary()
        app.root.update()
        check(app.mac_summary_panel.winfo_ismapped(), "Summary did not expand")
        check(app.mac_summary_list.size() == 3, "Vendor count groups missing")
        app._set_mac_vendor_filter("Cisco")
        check(len(app.mac_tree.get_children()) == 2, "Vendor include filter failed")
        app._set_mac_vendor_filter("Cisco", exclude=True)
        check(len(app.mac_tree.get_children()) == 2, "Vendor exclude filter failed")
        check(all(app.mac_tree.set(i, "Vendor / result") != "Cisco"
                  for i in app.mac_tree.get_children()), "Excluded vendor still visible")
        app._set_mac_vendor_filter(None)
        check(len(app.mac_tree.get_children()) == 4, "All results not restored")
        app._toggle_mac_summary()
        app.mac_results = []
        print("PASS: responsive Clipboard and simplified MAC actions, vendor summary filters")

        from unittest.mock import patch
        app.show_tab("settings")
        app.root.geometry("620x640+20+20")
        app.root.update()
        with patch("tkinter.simpledialog.askstring", return_value="Work"):
            app.settings_controls["window_profile_save"].invoke()
        app.root.update()
        check(app.settings["window_profiles"]["Work"] == {"width": 620, "height": 640},
              "Save profile did not capture actual dimensions")
        picker = app.settings_controls["window_profile"]
        label = next(value for value in picker["values"] if value.startswith("Mini "))
        picker.set(label)
        picker.event_generate("<<ComboboxSelected>>")
        app.root.update()
        check(app.display_mode == "mini", "Factory Mini selection failed")
        picker = app.settings_controls["window_profile"]
        label = next(value for value in picker["values"] if value.startswith("Work "))
        picker.set(label)
        picker.event_generate("<<ComboboxSelected>>")
        app.root.update()
        check(app.display_mode == "normal", "Custom size did not reflow")
        check((app.root.winfo_width(), app.root.winfo_height()) == (620, 640),
              "Custom profile dimensions not restored")
        with patch("tkinter.messagebox.askyesno", return_value=True):
            app.settings_controls["window_profile_delete"].invoke()
        check("Work" not in app.settings["window_profiles"], "Profile deletion failed")
        check(app.settings["window_profile"] == adaptive.CURRENT_PROFILE,
              "Deleting active profile must preserve current size")
        print("PASS: Settings profile Save, dropdown switch and Delete")

        # The Extra list must settle after an actual viewport change, without
        # scheduling itself again when its own requested height changes.
        import tkinter as tk
        app._set_display_mode("mini")
        app.show_tab("extra")
        check(app._extra_excel_mode == "database", "Extra must default to Database")

        def settle():
            done = tk.BooleanVar(master=app.root, value=False)
            app.root.after(180, lambda: done.set(True))
            app.root.wait_variable(done)
            app.root.update()

        def listboxes(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Listbox):
                    yield child
                yield from listboxes(child)

        tall_height = min(900, area[3] - area[1] - 30)
        app.root.geometry("410x530+20+20")
        settle()
        matches = next(listboxes(app.body))
        short = int(matches.cget("height"))
        app.root.geometry(f"410x{tall_height}+20+20")
        settle()
        tall = int(matches.cget("height"))
        check(short == 5 and 5 <= tall <= 14, "Extranet matches exceeded bounds")
        if app._tool_scroll_canvas.winfo_height() >= 550:
            check(tall > short, "Tall Extranet did not reveal additional matches")
        changes = []
        matches.bind("<Configure>", lambda event: changes.append(event.height), add="+")
        settle()
        settle()
        check(not changes, "Extranet layout keeps changing at a fixed window size")
        app.show_tab("notes")
        settle()
        print("PASS: Extra viewport settles and pending resize is cancelled on exit")

        for name, attr in (("mac", "mac_tree"), ("ports", "port_tree")):
            app.show_tab(name)
            app.root.geometry("410x530+20+20")
            settle()
            short = getattr(app, attr).winfo_height()
            canvas = app._tool_scroll_canvas
            short_view = canvas.winfo_height()
            app.root.geometry(f"410x{tall_height}+20+20")
            settle()
            tree = getattr(app, attr)
            growth = canvas.winfo_height() - short_view
            # A short profile may already have a minimum content height
            # larger than its viewport. Measure actual available geometry.
            if growth >= 100:
                check(tree.winfo_height() > short,
                      f"{name}: result table did not grow with tall Mini")
            bottom_gap = canvas.winfo_rooty() + canvas.winfo_height() - (
                tree.winfo_rooty() + tree.winfo_height())
            check(bottom_gap <= 6, f"{name}: unused space below results")
            app.root.geometry("410x450+20+20")
            settle()
            check(canvas.yview()[1] < 1, f"{name}: short window cannot scroll")
        print("PASS: tall Mini network tables fill viewport")

        # Inject synthetic TCP results; never contact Local or DashDash.
        for mode in ("mini", "normal", "dashboard"):
            app._set_display_mode(mode)
            app.show_tab("ports")
            app.ports_var.set("80,554,2079-2084,22,21")
            app.root.update()
            check(app.port_count.cget("text") == "10/16", "Range count incorrect")
            app.scan_requested_ports = [80, 22, 21, 443]
            app.port_results = []
            for port, service, status in ((22, "SSH", "TIMEOUT"),
                                          (80, "HTTP", "OPEN"),
                                          (21, "FTP", "CLOSED")):
                row = {"port": port, "service": service, "status": status, "ms": 5}
                app.port_results.append(row)
                app._add_port_result(row)
            app._refresh_port_progress()
            app.root.update()
            check(app.port_progress_label.cget("text") == "3/4 completed",
                  "Progress must count completed checks only")
            tree = app.port_tree
            children = tree.get_children()
            check(tree.set(children[0], "TCP status") == "OPEN", "OPEN sort changed")
            check(tree.item(children[0], "tags") == ("port_open",), "OPEN color missing")
            check(all(tree.item(i, "tags") == ("port_failed",) for i in children[1:]),
                  "Failure colors missing")
            fills = [app.port_progress.itemcget(i, "fill")
                     for i in app.port_progress.find_all()]
            check("#54C58A" in fills and "#F87171" in fills,
                  "Progress bar missing result segments")
            app.port_results = []
        print("PASS: range input and TCP result styling in all working layouts")

        # Drive the palette through real entry/selection widgets without network.
        from pocket import command_palette
        from unittest.mock import patch
        def palette_run(query):
            app._open_global_search()
            app.root.update()
            dialog = app._quick_search_dialog
            check(dialog.winfo_exists(), "Command palette did not open")
            app._palette_entry.insert(0, query)
            app.root.update()
            def children(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from children(child)
            buttons = [w for w in children(dialog)
                       if isinstance(w, tk.Button) and w.cget("text") == "Open"]
            check(buttons, "Palette action button missing")
            buttons[0].invoke()
            app.root.update()
            check(app._quick_search_dialog is None, "Palette did not close")

        app._set_display_mode("normal")
        palette_run("> subnet 192.168.10.0/26")
        check(app.current_tab == "subnet" and app.subnet_prefix_var.get() == "26",
              "Palette subnet calculation failed")
        with patch.object(app, "_start_scan", side_effect=AssertionError("Must not scan")):
            palette_run("> port 192.168.1.1 80,554,2079-2084")
        check(app.current_tab == "ports" and app.ports_var.get() == "80,554,2079-2084",
              "Palette port prefill failed")
        with patch.object(app, "_run_mac_lookup", side_effect=AssertionError("Must not query")):
            palette_run("mac 00:00:0C:12:34:56")
        check(app.current_tab == "mac" and app.mac_input.get("1.0", "end-1c") == "00:00:0C:12:34:56",
              "Palette MAC prefill failed")
        palette_run("> note Palette test note")
        check(app.current_tab == "notes" and app.title_var.get() == "Palette test note",
              "Palette note creation failed")
        palette_run("> theme black")
        check(app.theme == "black", "Palette theme change failed")
        palette_run("> size mini")
        check(app.display_mode == "mini", "Palette size change failed")
        print("PASS: command palette dispatches real internal actions without network")

        # Reopen with the actual keyboard binding, not a direct function call.
        # The owner must regain focus after Escape, Close and action dispatch.
        app.root.attributes("-topmost", True)
        app.root.focus_force()
        app.root.update()
        def reopen_with_key():
            focused = app.root.focus_get()
            check(focused is not None and focused.winfo_toplevel() == app.root,
                  "Pocket must regain keyboard focus before reopening")
            focused.event_generate("<Control-k>")
            app.root.update()
            dialog = app._quick_search_dialog
            check(dialog is not None and dialog.winfo_viewable(),
                  "Ctrl+K did not reopen the palette")
            if sys.platform == "win32":
                check(bool(dialog.attributes("-topmost")), "Palette must remain topmost")
            check(dialog.focus_get() == app._palette_entry, "Palette entry must receive focus")
            return dialog

        for cycle in range(3):
            dialog = reopen_with_key()
            app._palette_entry.insert(0, "notes")
            app._palette_entry.event_generate("<Escape>")
            app.root.update()
            check(app._quick_search_dialog is None and not app._modal,
                  "Escape did not close palette and clear modal state")
        dialog = reopen_with_key()
        app._palette_entry.insert(0, "notes")
        app._palette_entry.selection_range(0, "end")
        app._palette_entry.event_generate("<Control-x>")
        app.root.update()
        check(app._quick_search_dialog is dialog, "Ctrl+X must not dismiss palette")
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        close_buttons = [w for w in descendants(dialog)
                         if isinstance(w, tk.Button) and w.cget("text") == "Close"]
        check(close_buttons, "Close button missing")
        close_buttons[0].invoke()
        app.root.update()
        dialog = reopen_with_key()
        app._palette_entry.insert(0, "> open notes")
        app._palette_entry.event_generate("<Return>")
        app.root.update()
        check(app.current_tab == "notes" and app._quick_search_dialog is None,
              "Enter did not run the selected action")
        dialog = reopen_with_key()
        app._palette_entry.event_generate("<Escape>")
        app.root.update()
        print("PASS: repeated Ctrl+K, Escape, Close, Enter, topmost and normal Ctrl+X")
    finally:
        app.root.destroy()
