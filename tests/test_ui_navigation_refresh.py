"""Regression checks for the dashboard navigation design refresh.

The tests validate that presentation changes retain all existing routes and
do not add fake features, network calls, or changes to data storage.
"""
from pathlib import Path
import runpy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from pocket import dashboard_ui as dashboard
from pocket import compact_dashboard as compact
from pocket import pocket_design as design
from pocket import mini_layout as layout
from pocket import normal_navigation as normal_nav

root=Path(__file__).resolve().parents[1]
app=runpy.run_path(str(root/"app.pyw"),run_name="ui_design_tests")


class NavigationPolishTests(unittest.TestCase):
    def test_dashboard_reaches_all_real_tools(self):
        all_keys={key for key,_ in app["VISIBLE_TABS"]}
        nav={key for key,_,_ in dashboard.NAVIGATION}
        self.assertEqual(nav,all_keys|{"home","settings"})
        self.assertEqual(set(dashboard.TITLES),nav)
        source=(root/"pocket"/"dashboard_ui.py").read_text(encoding="utf-8")
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
        headings=(root/"pocket"/"pocket_design.py").read_text(encoding="utf-8")
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

    def test_mini_native_note_focus_loss_hides_without_forcing_focus(self):
        root = Mock()
        root.state.return_value = "normal"
        # Tk still thinks the old child editor is active after activation
        # moves to another application.
        root.focus_displayof.return_value = object()
        editor = Mock()
        editor.foreground_is_external.return_value = True
        editor.has_focus.return_value = True
        desk = SimpleNamespace(
            preview=False, pinned=False, _modal=False,
            _dragging_window=False, root=root,
            bidi_editor=editor, _bidi_active=lambda: True,
            hide=Mock())
        app["PocketDesk"]._maybe_hide(desk)
        desk.hide.assert_called_once()
        editor.has_focus.assert_not_called()
        root.focus_displayof.assert_not_called()

    def test_native_editor_focus_watchdog_respects_pin_and_modal(self):
        root = Mock()
        root.state.return_value = "normal"
        root.focus_displayof.return_value = None
        editor = Mock()
        editor.foreground_is_external.return_value = True
        desk = SimpleNamespace(
            preview=False, pinned=True, _modal=False,
            _dragging_window=False, root=root, bidi_editor=editor,
            _bidi_active=lambda: True, hide=Mock())
        app["PocketDesk"]._maybe_hide(desk)
        desk.hide.assert_not_called()
        desk.pinned = False
        desk._modal = True
        app["PocketDesk"]._maybe_hide(desk)
        desk.hide.assert_not_called()
        desk._modal = False
        editor.foreground_is_external.return_value = False
        editor.has_focus.return_value = True
        app["PocketDesk"]._maybe_hide(desk)
        desk.hide.assert_not_called()

    def test_mini_editor_poll_detects_activation_without_tk_focusout(self):
        root = Mock()
        root.state.return_value = "normal"
        editor = Mock()
        editor.get_text.return_value = "unchanged text"
        editor.foreground_is_external.return_value = True
        note = {"body": "unchanged text"}
        desk = SimpleNamespace(
            display_mode="mini", preview=False, root=root,
            bidi_editor=editor, _loading_note=False,
            _bidi_active=lambda: True, active_note=lambda: note,
            _edit_dirty=Mock(), _maybe_hide=Mock())
        app["PocketDesk"]._bidi_poll(desk)
        desk._maybe_hide.assert_called_once()
        desk._edit_dirty.assert_not_called()
        desk.display_mode = "normal"
        desk._maybe_hide.reset_mock()
        app["PocketDesk"]._bidi_poll(desk)
        desk._maybe_hide.assert_not_called()
        desk.display_mode = "mini"
        desk.preview = True
        app["PocketDesk"]._bidi_poll(desk)
        desk._maybe_hide.assert_not_called()

    def test_extra_mini_tiles_remain_configurable(self):
        source=(root/"pocket"/"compact_dashboard.py").read_text(encoding="utf-8")
        self.assertIn("design.Tooltip(remove,",source)
        self.assertIn("design.Tooltip(add,",source)
        self.assertIn('tile.bind("<Return>"',source)
        self.assertEqual(len(compact.display_slots(
            [key for key,_ in app["VISIBLE_TABS"]],compact.FEATURED)),4)

    def test_tooltip_is_presentational_only(self):
        source=(root/"pocket"/"pocket_design.py").read_text(encoding="utf-8")
        self.assertIn('class Tooltip:',source)
        self.assertIn('widget.bind("<FocusOut>", self._hide, add="+")',source)
        self.assertIn('widget.bind("<Destroy>", self._hide, add="+")',source)
        self.assertTrue(callable(design.tool_button))


if __name__=="__main__":
    unittest.main()
