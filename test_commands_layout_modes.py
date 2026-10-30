"""Prevent normal Commands view from regressing into Mini's single-card layout."""
from pathlib import Path
import unittest


class CommandsLayoutRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(__file__).with_name("app.pyw").read_text(encoding="utf-8")

    def test_normal_view_has_scrollable_results_above_editor(self):
        begin = self.source.index("    def _build_commands(self):")
        end = self.source.index("    def _show_command_backup_menu(self):", begin)
        block = self.source[begin:end]
        self.assertIn('if self.display_mode == "mini":', block)
        self.assertIn('return self._build_mini_commands()', block)
        self.assertIn('orient=tk.VERTICAL', block)
        self.assertIn('command_panes.add(results_panel, minsize=150', block)
        self.assertIn("self.command_tree = self._tree(results_panel,", block)
        self.assertIn("(230, 185), rows=4", block)
        self.assertIn('action_label(heading, "Backup ▾"', block)
        self.assertIn('action_label(heading, "+ New"', block)
        self.assertIn("self.command_tree.bind('<<TreeviewSelect>>'", block)
        self.assertIn('command_panes.add(details, minsize=195', block)

    def test_mini_remains_single_card_without_visible_table(self):
        begin = self.source.index("    def _build_mini_commands(self):")
        end = self.source.index("    def _update_mini_command_pager(self):", begin)
        block = self.source[begin:end]
        self.assertIn("self.mini_command_page", block)
        self.assertIn("self._move_mini_command", block)


if __name__ == "__main__":
    unittest.main()
