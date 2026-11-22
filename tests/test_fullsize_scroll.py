"""Check full-size Pocket tools retain vertical scrolling on small displays."""
from pathlib import Path
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / "app.pyw").read_text(encoding="utf-8")


class FullSizeScrollTests(unittest.TestCase):
    def test_scroll_wrappers_include_all_tall_normal_tools(self):
        start = SOURCE.index("    def show_tab(self, which):")
        end = SOURCE.index("    def _show_more_menu(self):", start)
        code = SOURCE[start:end]
        self.assertIn('self.display_mode in ("normal", "compact")', code)
        self.assertIn('self.display_mode in ("normal", "dashboard")', code)
        self.assertIn('("ports", "mac", "commands", "subnet", "settings", "extra")', code)
        self.assertIn('self._scrolling_tool_body()', code)

    def test_wheel_bubbles_to_outer_canvas_without_stealing_text_editing(self):
        self.assertIn('self.root.bind("<MouseWheel>", self._scroll_tool_on_wheel', SOURCE)
        start = SOURCE.index('    def _scroll_tool_on_wheel(self, event, *, from_picker=False):')
        end = SOURCE.index('    def _mini_click_outside_editor', start)
        code = SOURCE[start:end]
        self.assertIn('elif isinstance(widget, (tk.Text, tk.Listbox)):', code)
        self.assertIn('isinstance(widget, ttk.Treeview)', code)
        self.assertIn('canvas.yview_scroll(steps, "units")', code)

    def test_extra_mini_has_only_thin_matches_rail(self):
        # Outer page rail remains hidden, but the user explicitly wants a
        # narrow dark Matches scrollbar; its wheel goes to the parent page.
        scrolling = SOURCE.split("    def _scrolling_tool_body(self):", 1)[1].split(
            "    def _mini_scrolling_body(self):", 1)[0]
        wheel = SOURCE.split("    def _scroll_tool_on_wheel(self, event, *, from_picker=False):",
                             1)[1].split("    def _command_picker_on_wheel", 1)[0]
        self.assertIn('self.current_tab == "extra" and self.display_mode == "mini"',
                      scrolling)
        self.assertIn('"extra"):', wheel)
        extra_ui = (Path(__file__).resolve().parents[1] /
                    "pocket" / "extra_excel_ui.py").read_text(encoding="utf-8")
        self.assertIn('list_scroll.pack(side="right", fill="y"', extra_ui)
        self.assertIn('width=8 if compact else 12', extra_ui)
        self.assertIn('scroll_outer_instead_of_matches', extra_ui)
        self.assertIn('if not compact:\n        detail_scroll.pack(', extra_ui)

    def test_cli_combobox_never_calls_vertical_yview(self):
        start = SOURCE.index("    def _scroll_tool_on_wheel(self, event, *, from_picker=False):")
        end = SOURCE.index("    def _command_picker_on_wheel(self, event):", start)
        code = SOURCE[start:end]
        combobox = code.index("if isinstance(widget, ttk.Combobox):")
        text_branch = code.index("elif isinstance(widget, (tk.Text, tk.Listbox)):")
        self.assertLess(combobox, text_branch)
        self.assertNotIn("widget.yview()", code[combobox:text_branch])

    def test_normal_commands_title_is_outside_scroll_region(self):
        start = SOURCE.index("    def show_tab(self, which):")
        end = SOURCE.index("    def _show_more_menu(self):", start)
        code = SOURCE[start:end]
        self.assertLess(code.index("self._build_normal_commands_header()"),
                        code.index("self._scrolling_tool_body()"))

    def test_page_scroll_rail_is_hidden_in_both_modes(self):
        start = SOURCE.index("    def _scrolling_tool_body(self):")
        end = SOURCE.index("    def _mini_scrolling_body(self):", start)
        code = SOURCE[start:end]
        self.assertNotIn("scrollbar.pack(", code)
        self.assertIn("canvas.pack(", code)

    def test_command_pickers_block_wheel_selection_changes(self):
        self.assertIn('def _command_picker_on_wheel(self, event):', SOURCE)
        self.assertIn('return "break"\n\n    def _protect_command_picker', SOURCE)
        self.assertIn("self._protect_command_picker(self.machine_picker)", SOURCE)
        self.assertIn("self._protect_command_picker(self.command_category_picker)", SOURCE)

    def test_tab_switch_clears_previous_scroll_target(self):
        start = SOURCE.index("    def show_tab(self, which):")
        end = SOURCE.index("    def _show_more_menu(self):", start)
        self.assertIn('self._tool_scroll_canvas = None', SOURCE[start:end])


if __name__ == "__main__":
    unittest.main()
