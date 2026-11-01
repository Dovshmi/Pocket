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
        self.assertIn('design.Tooltip(more_button, "Open additional enabled tools"',source)
        self.assertIn('tile.bind("<Return>", lambda _event, tool=key: self.show_tab(tool))',source)
        self.assertIn('tile.bind("<space>", lambda _event, tool=key: self.show_tab(tool))',source)
        self.assertEqual(layout.view_dimensions("normal"),(480,850))
        self.assertEqual(layout.view_dimensions("mini"),(346,530))
        self.assertEqual(layout.view_dimensions("dashboard"),(1160,800))
        self.assertEqual(layout.view_dimensions("compact"),(322,256))

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
