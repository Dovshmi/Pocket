"""Real Tk smoke: reorder Pocket's actual menu icons by click and mouse drag.

Uses disposable APPDATA and no workbooks/network. Operates the same widget
bindings used by a person in Settings -> Visible tools -> Menu Order.
"""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import tempfile

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT))

from pocket import menu_order


def check(condition, message):
    if not condition:
        raise AssertionError(message)


with tempfile.TemporaryDirectory(prefix="pocket-v140-order-") as temp:
    os.environ["APPDATA"] = temp
    mod = runpy.run_path(str(ROOT / "app.pyw"), run_name="menu_order_smoke")
    app = mod["PocketDesk"](preview=True)
    try:
        app.root.update()
        check(app.display_mode == "mini", "Must start with original Mini layout")
        app.show_tab("settings")
        app.root.update()
        app.settings_controls["settings_group_tools"].invoke()
        app.root.update()
        check(app._settings_sections["tools"]["body"].winfo_ismapped(),
              "Visible Tools category failed to expand")

        original = app.settings["menu_order"][:]
        check(original == list(menu_order.DEFAULT_ORDER), "Original order changed")

        def tile(key):
            return app.menu_order_editor_cells[key]

        # Actual mouse press/release on the icon frame, not a direct call
        # into the implementation, exercises click-select/click-target.
        def click_icon(key):
            icon = tile(key)
            icon.event_generate("<ButtonPress-1>", x=9, y=9)
            icon.event_generate("<ButtonRelease-1>", x=9, y=9)
            app.root.update()
        click_icon("extra")
        click_icon("notes")
        check(app.settings["menu_order"][0] == "extra",
              "Click-select / click-target did not reorder Extra")

        # Bring back the Tools category after the shell redraw.
        if app._settings_open_group != "tools":
            app.settings_controls["settings_group_tools"].invoke()
        app.root.update()
        src = tile("settings")
        dst = tile("extra")
        start_x, start_y = src.winfo_rootx() + 8, src.winfo_rooty() + 8
        goal_x, goal_y = dst.winfo_rootx() + 8, dst.winfo_rooty() + 8
        src.event_generate("<ButtonPress-1>", x=8, y=8)
        src.event_generate("<B1-Motion>",
                           x=goal_x - src.winfo_rootx(),
                           y=goal_y - src.winfo_rooty())
        src.event_generate("<ButtonRelease-1>",
                           x=goal_x - src.winfo_rootx(),
                           y=goal_y - src.winfo_rooty())
        app.root.update()
        check(app.settings["menu_order"][0] == "settings",
              "Mouse drag did not place Settings before Extra")
        check(set(app.settings["menu_order"]) == set(menu_order.DEFAULT_ORDER),
              "Dragging deleted or duplicated an icon")

        # Rebuilding Pocket must reflect the saved Settings placement and
        # not alter the fixed More/Less overflow behavior.
        check(app.mini_icon_tabs.get("settings") is not None,
              "Settings icon missing in Mini after drag")
        check(app.mini_icon_tabs.get("more") is not None,
              "More/Less tile missing with all tools visible")
        check(app.mini_icon_tabs["settings"][0].winfo_exists(),
              "Dragged Settings icon is not displayed")

        app._set_visible_tab("extra", False)
        app.root.update()
        check(app.settings["menu_order"][1] == "extra",
              "Hiding Extra lost its saved position")
        app._set_visible_tab("extra", True)
        app.root.update()
        check(app.settings["menu_order"][1] == "extra",
              "Re-enabling Extra moved it to the end")

        # Settings displays the version and all original controls still exist.
        app.show_tab("settings")
        app.root.update()
        check(app.settings_footer_version.cget("text") == "Version v1.40",
              "Settings version drifted")
        check("create_pocket_backup" in app.settings_controls,
              "Backup action was lost by Settings reorder")

        print("PASS: real icon click and drag, hidden icon persistence, Mini More, Settings backup")
    finally:
        try:
            app.root.destroy()
        except Exception:
            pass
