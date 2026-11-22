"""Real Pocket Mini navigation smoke: direct drag, right-click Hide, and smart Add.

No duplicate editor exists in Settings. Uses disposable APPDATA and synthetic
GUI actions; never reads a corporate workbook or connects to the Internet.
"""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pocket import menu_order


def check(ok, message):
    if not ok:
        raise AssertionError(message)


class MenuStub:
    calls = []
    choose = None

    def __init__(self, *args, **kwargs):
        self.commands = []
        self.images = []

    def add_command(self, **kwargs):
        self.commands.append(kwargs)
        MenuStub.calls.append(kwargs)

    def tk_popup(self, *_args, **_kwargs):
        if MenuStub.choose:
            action = next((c["command"] for c in self.commands
                           if MenuStub.choose in c["label"]), None)
            if action:
                action()

    def grab_release(self):
        pass


with tempfile.TemporaryDirectory(prefix="pocket-v140-direct-menus-") as home:
    os.environ["APPDATA"] = home
    mod = runpy.run_path(str(ROOT / "app.pyw"), run_name="direct_menu_smoke")
    app = mod["PocketDesk"](preview=True)
    try:
        root = app.root
        root.update()
        check(app.display_mode == "mini", "Expected Mini navigation")
        check("more" in app.mini_icon_tabs, "10 visible menus should have More")
        check("plus" not in app.mini_icon_tabs, "Plus is redundant when all are visible")
        check(app.mini_icon_tabs["more"][0].winfo_exists(), "More tile missing")
        check(app.settings["menu_order"] == list(menu_order.DEFAULT_ORDER),
              "New account did not keep original icon ordering")
        app._toggle_mini_more()
        root.update()

        def tile(key):
            return app.mini_icon_tabs[key][0]

        # Drag the actual Extra icon from the open overflow row onto Notes.
        src, dst = tile("extra"), tile("notes")
        tx, ty = dst.winfo_rootx() + 8, dst.winfo_rooty() + 8
        src.event_generate("<ButtonPress-1>", x=8, y=8)
        src.event_generate("<B1-Motion>",
                           x=tx - src.winfo_rootx(),
                           y=ty - src.winfo_rooty())
        src.event_generate("<ButtonRelease-1>",
                           x=tx - src.winfo_rootx(),
                           y=ty - src.winfo_rooty())
        root.update()
        check(app.settings["menu_order"][0] == "extra",
              "Dragging in the real navigation did not save icon order")
        check("extra" in app.mini_icon_tabs, "Dragged icon vanished")
        check(app.mini_icon_tabs["extra"][0].winfo_ismapped(),
              "Dragged Extra icon is not visible in the first row")

        # Right-click a real tile. The user-facing Hide menu is invoked by the
        # stubbed Windows popup, rather than navigating Settings.
        with patch.object(mod["menu_style"], "Menu", MenuStub):
            MenuStub.calls.clear()
            MenuStub.choose = "Hide Links"
            tile("links").event_generate("<Button-3>", x=10, y=10)
            root.update()
            check("links" not in app.settings["visible_tabs"],
                  "Right-click Hide did not deactivate Links")
            check(any("Hide Links" == c.get("label") for c in MenuStub.calls),
                  "Right-click should offer Hide Links")

            # Reduce to exactly 7 including Settings: Plus replaces More at
            # the last slot and is green without an extra toolbar row.
            app._set_visible_tab("ports", False)
            app._set_visible_tab("mac", False)
            root.update()
            check("more" not in app.mini_icon_tabs,
                  "At seven menus More should turn into Plus")
            check("plus" in app.mini_icon_tabs, "Plus missing at seven menus")
            check(len(app.mini_icon_tabs) == 8,
                  "Seven real menus plus one Add should fill eight positions")
            check(app.mini_icon_tabs["plus"][0].winfo_ismapped(),
                  "Plus not visible in last slot")

            # Clicking the real Plus shows only hidden menus and restores one.
            MenuStub.calls.clear()
            MenuStub.choose = "Links"
            plus = tile("plus")
            plus.event_generate("<ButtonPress-1>", x=8, y=8)
            root.update()
            plus.event_generate("<ButtonRelease-1>", x=8, y=8)
            root.update()
            check(any("Links" in command.get("label", "")
                      for command in MenuStub.calls),
                  "Clicking Plus did not open the list of hidden menus")
            check("links" in app.settings["visible_tabs"],
                  "Plus failed to restore the hidden Links menu")
            check("more" in app.mini_icon_tabs,
                  "Eight menus must use More as eighth icon")
            check(app._mini_overflow_keys[-1] == "plus",
                  "Plus must be the very last overflow icon")
            check(app.settings["menu_order"][0] == "extra",
                  "Restoring a menu modified the user-selected icon order")

            # Settings may be reordered, never hidden.
            original = app.settings["visible_tabs"][:]
            MenuStub.calls.clear()
            app._mini_nav_context_menu(
                type("Pointer", (), {"x_root": 8, "y_root": 8})(), "settings")
            root.update()
            check(app.settings["visible_tabs"] == original,
                  "Settings could be hidden from the navigation")
            check(not MenuStub.calls, "Settings should not offer Hide")

        app.show_tab("settings")
        root.update()
        check("settings_group_tools" not in app.settings_controls,
              "Old duplicate Settings menu editor must be removed")
        check("create_pocket_backup" in app.settings_controls,
              "Settings backup control was lost")
        check(app.settings_footer_version.cget("text") == "Version v1.40",
              "Version must remain v1.40")
        check("menu_order" in app.settings,
              "Reordered icon positions must be stored in Settings backup")

        print("PASS: real Mini drag, context Hide, automatic Plus/More, "
              "hidden restore, Settings always visible and backup")
    finally:
        try:
            app.root.destroy()
        except Exception:
            pass
