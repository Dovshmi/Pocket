"""Regression checks for the dashboard navigation design refresh.

The tests validate that presentation changes retain all existing routes and
do not add fake features, network calls, or changes to data storage.
"""
from pathlib import Path
import runpy
import unittest

import dashboard_ui as dashboard
import compact_dashboard as compact
import pocket_design as design
import mini_layout as layout
import normal_navigation as normal_nav

root=Path(__file__).resolve().parent
app=runpy.run_path(str(root/"app.pyw"),run_name="ui_design_tests")


class NavigationPolishTests(unittest.TestCase):
    def test_dashboard_reaches_all_real_tools(self):
        all_keys={key for key,_ in app["VISIBLE_TABS"]}
        nav={key for key,_,_ in dashboard.NAVIGATION}
        self.assertEqual(nav,all_keys|{"home","settings"})
        self.assertEqual(set(dashboard.TITLES),nav)
        source=(root/"dashboard_ui.py").read_text(encoding="utf-8")
        self.assertIn('for index, (icon, title, detail, key) in enumerate(visible):',source)
        for key in sorted(all_keys):
            self.assertIn(f'"{key}"),',source)
        self.assertIn('app._open_global_search',source)

    def test_mini_and_normal_keep_existing_tabs_and_search(self):
        source=(root/"app.pyw").read_text(encoding="utf-8")
        self.assertNotIn('design.tool_button(header, "⌕", self._open_global_search',source)
        self.assertIn('self.root.bind("<Control-k>", self._open_global_search)',source)
        self.assertIn("normal_navigation.install(self, tabs", source)
        self.assertIn("self._normal_nav_refresh(which)", source)
        self.assertIn('tile.bind("<Return>", lambda _event, tool=key: self.show_tab(tool))',source)
        self.assertIn('tile.bind("<space>", lambda _event, tool=key: self.show_tab(tool))',source)
        self.assertEqual(layout.view_dimensions("normal"),(480,850))
        self.assertEqual(layout.view_dimensions("mini"),(346,530))
        self.assertEqual(layout.view_dimensions("dashboard"),(1160,800))
        self.assertEqual(layout.view_dimensions("compact"),(322,256))

    def test_normal_nav_all_tools_fit_and_selected_tool_survives_overflow(self):
        enabled = [key for key, _ in app["VISIBLE_TABS"]]
        visible, hidden = normal_nav.plan_tabs(enabled, "notes", 440)
        self.assertEqual(visible, tuple(enabled))
        self.assertEqual(hidden, ())
        visible, hidden = normal_nav.plan_tabs(enabled, "clipboard", 280)
        self.assertIn("clipboard", visible)
        self.assertEqual(set(visible) | set(hidden), set(enabled))
        self.assertFalse(set(visible) & set(hidden))

    def test_normal_workspace_density_is_mode_specific(self):
        source=(root/"app.pyw").read_text(encoding="utf-8")
        headings=(root/"pocket_design.py").read_text(encoding="utf-8")
        self.assertIn('balanced=self.display_mode == "normal"',source)
        self.assertIn('self.display_mode == "normal" else 10',source)
        self.assertIn('if self.display_mode == "normal":\n            facts.columnconfigure(3, weight=1)',source)
        self.assertIn('if self.display_mode == "normal":\n            self.mac_input.config(height=4)',source)
        self.assertIn('balanced=False',headings)
        self.assertIn('if self.display_mode == "mini":\n            return self._build_mini_notes()',source)
        self.assertIn('if self.display_mode == "mini":\n            return self._build_mini_commands()',source)

    def test_shortcut_scrollbar_keeps_mini_unchanged(self):
        source=(root/"app.pyw").read_text(encoding="utf-8")
        self.assertIn('if self.display_mode == "mini":\n            scroll = tk.Scrollbar(', source)
        self.assertIn('scroll = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview,', source)
        self.assertIn('style="Pocket.Vertical.TScrollbar"', source)

    def test_note_focus_bridge_preserves_mini_arrow_paging(self):
        source=(root/"app.pyw").read_text(encoding="utf-8")
        self.assertIn('self.root.bind("<Button-1>", self._note_click_focus, add="+")', source)
        self.assertIn('self.root.bind(f"<{key}>", lambda event, delta=step: self._mini_keyboard_step(event, delta))', source)
        self.assertIn('self.mini_note_picker.bind("<ButtonPress-1>", self._note_focus_field, add="+")', source)
        self.assertEqual(source.count('self.title_entry.bind("<ButtonPress-1>", self._note_focus_field'), 2)
        self.assertEqual(source.count('self.phone_entry.bind("<ButtonPress-1>", self._note_focus_field'), 2)
        self.assertIn('self.bidi_editor.release_focus_to(destination)', source)
        self.assertIn('self._move_mini_note(step)', source)

    def test_extra_mini_tiles_remain_configurable(self):
        source=(root/"compact_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("design.Tooltip(remove,",source)
        self.assertIn("design.Tooltip(add,",source)
        self.assertIn('tile.bind("<Return>"',source)
        self.assertEqual(len(compact.display_slots(
            [key for key,_ in app["VISIBLE_TABS"]],compact.FEATURED)),4)

    def test_tooltip_is_presentational_only(self):
        source=(root/"pocket_design.py").read_text(encoding="utf-8")
        self.assertIn('class Tooltip:',source)
        self.assertIn('widget.bind("<FocusOut>", self._hide, add="+")',source)
        self.assertIn('widget.bind("<Destroy>", self._hide, add="+")',source)
        self.assertTrue(callable(design.tool_button))


if __name__=="__main__":
    unittest.main()
