"""Check full-size Pocket tools retain vertical scrolling on small displays."""
from pathlib import Path
import unittest

SOURCE = Path(__file__).with_name("app.pyw").read_text(encoding="utf-8")


class FullSizeScrollTests(unittest.TestCase):
    def test_scroll_wrappers_include_all_tall_normal_tools(self):
        start = SOURCE.index("    def show_tab(self, which):")
        end = SOURCE.index("    def _show_more_menu(self):", start)
        code = SOURCE[start:end]
        self.assertIn('self.display_mode == "normal"', code)
        self.assertIn('("ports", "mac", "commands", "subnet")', code)
        self.assertIn('self._scrolling_tool_body()', code)

    def test_wheel_bubbles_to_outer_canvas_without_stealing_text_editing(self):
        self.assertIn('self.root.bind("<MouseWheel>", self._scroll_tool_on_wheel', SOURCE)
        start = SOURCE.index('    def _scroll_tool_on_wheel(self, event):')
        end = SOURCE.index('    def _mini_click_outside_editor', start)
        code = SOURCE[start:end]
        self.assertIn('isinstance(widget, (tk.Text, tk.Listbox, tk.Entry', code)
        self.assertIn('isinstance(widget, ttk.Treeview)', code)
        self.assertIn('canvas.yview_scroll(steps, "units")', code)

    def test_tab_switch_clears_previous_scroll_target(self):
        start = SOURCE.index("    def show_tab(self, which):")
        end = SOURCE.index("    def _show_more_menu(self):", start)
        self.assertIn('self._tool_scroll_canvas = None', SOURCE[start:end])


if __name__ == "__main__":
    unittest.main()
