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
        check(len(app._resize_handles) == 8, "eight edge/corner grips required")
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
        check(len(app._resize_handles) == 8, "grips missing after layout rebuild")
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
        print("PASS: responsive Clipboard and simplified MAC actions")

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

        # A tall but narrow Mini profile must spend its extra height on
        # result rows, not blank space after fixed-size tables.
        import tkinter as tk
        app._set_display_mode("mini")
        for name, attr in (("mac", "mac_tree"), ("ports", "port_tree")):
            app.show_tab(name)
            app.root.geometry("410x530+20+20")
            app.root.update()
            short = getattr(app, attr).winfo_height()
            app.root.geometry("410x900+20+20")
            app.root.update()
            tree = getattr(app, attr)
            check(tree.winfo_height() >= short + 200,
                  f"{name}: result table did not grow with tall Mini")
            canvas = app._tool_scroll_canvas
            bottom_gap = canvas.winfo_rooty() + canvas.winfo_height() - (
                tree.winfo_rooty() + tree.winfo_height())
            check(abs(bottom_gap) <= 6, f"{name}: unused space below results")
            app.root.geometry("410x450+20+20")
            app.root.update()
            check(canvas.yview()[1] < 1, f"{name}: short window cannot scroll")
        app.show_tab("extra")
        def listboxes(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Listbox):
                    yield child
                yield from listboxes(child)
        app.root.geometry("410x530+20+20")
        app.root.update()
        matches = next(listboxes(app.body))
        short = int(matches.cget("height"))
        app.root.geometry("410x900+20+20")
        app.root.update()
        tall = int(matches.cget("height"))
        check(short == 5 and 5 < tall <= 14, "Extranet matches must grow within bounds")
        print("PASS: tall Mini network tables fill viewport; Extranet preserves output space")
    finally:
        app.root.destroy()
