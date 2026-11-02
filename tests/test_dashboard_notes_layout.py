"""Dashboard Notes should own its layout without altering Mini or Normal."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.pyw").read_text(encoding="utf-8")
DASHBOARD = (ROOT / "pocket" / "dashboard_notes_ui.py").read_text(encoding="utf-8")


class DashboardNotesLayoutTests(unittest.TestCase):
    def test_notes_mode_dispatch_remains_isolated(self):
        start = APP.index("    def _build_notes(self):")
        end = APP.index("    def _flush_current_note(self):", start)
        source = APP[start:end]
        self.assertIn('if self.display_mode == "dashboard":', source)
        self.assertIn("return dashboard_notes.build(self)", source)
        self.assertIn('if self.display_mode == "mini":', source)
        self.assertIn("return self._build_mini_notes()", source)
        self.assertLess(source.index("return dashboard_notes.build(self)"),
                        source.index("return self._build_mini_notes()"))
        self.assertIn("self._section_title(", source)

    def test_editor_expands_below_compact_title_and_phone(self):
        self.assertIn("fields.grid_columnconfigure(0, weight=3)", DASHBOARD)
        self.assertIn("fields.grid_columnconfigure(1, weight=2", DASHBOARD)
        self.assertIn("editor.grid(row=1, column=0, sticky=\"nsew\")", DASHBOARD)
        self.assertIn("right.grid_rowconfigure(1, weight=1)", DASHBOARD)
        self.assertIn('app.note_body.pack(fill="both", expand=True', DASHBOARD)
        self.assertIn("app.note_list = tk.Listbox(", DASHBOARD)

    def test_existing_editing_and_reminder_callbacks_are_reused(self):
        for name in ("_note_focus_field", "_select_from_list",
                     "_show_note_list_menu", "_change_note_title",
                     "_change_note_phone", "_change_note_body",
                     "_toggle_active_note_reminder", "_edit_active_note_reminder",
                     "_copy_phone", "open_notepad", "_show_note_context_menu",
                     "refresh_note_list", "_load_selected_note", "delete_note"):
            self.assertIn("app." + name, DASHBOARD)
        self.assertIn("native_bidi.NativeBidiEditor(", DASHBOARD)
        self.assertIn("app.note_body.tag_configure(", DASHBOARD)
        self.assertIn("app.note_body.bind(\"<<Modified>>\", app._change_note_body)", DASHBOARD)


if __name__ == "__main__":
    unittest.main()
