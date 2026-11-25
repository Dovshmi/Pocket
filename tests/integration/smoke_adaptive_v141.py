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
        check((app.root.winfo_width(), app.root.winfo_height()) ==
              mini.view_dimensions("normal"), "Normal preset size mismatch")
        check(len(app._resize_handles) == 8, "grips missing after layout rebuild")
        print("PASS: Settings size presets continue to work")
    finally:
        app.root.destroy()
