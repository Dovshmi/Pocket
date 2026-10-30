"""Mini editor click-away focus regression tests (headless)."""
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock

app = runpy.run_path(str(Path(__file__).with_name("app.pyw")), run_name="test_import")
PocketDesk = app["PocketDesk"]


class MiniFocusTests(TestCase):
    def test_clicking_noneditable_card_restores_navigation_focus(self):
        desk = SimpleNamespace(display_mode="mini", _modal=False,
                               current_tab="commands", root=SimpleNamespace(focus_set=Mock()))
        # Plain card label/frame widgets should release Text focus.
        PocketDesk._mini_click_outside_editor(desk, SimpleNamespace(widget=object()))
        desk.root.focus_set.assert_called_once()

    def test_native_notes_editor_releases_windows_focus(self):
        """Click-away must transfer the native HWND, not only Tk focus."""
        native = SimpleNamespace(has_focus=Mock(return_value=True),
                                 release_focus_to=Mock())
        root = SimpleNamespace(focus_set=Mock())
        desk = SimpleNamespace(display_mode="mini", _modal=False,
                               current_tab="notes", root=root, bidi_editor=native,
                               _bidi_active=Mock(return_value=True),
                               _flush_current_note=Mock())
        PocketDesk._mini_click_outside_editor(desk, SimpleNamespace(widget=object()))
        desk._flush_current_note.assert_called_once()
        native.release_focus_to.assert_called_once_with(root)
        root.focus_set.assert_called_once()

    def test_native_editor_is_not_forced_out_when_not_focused(self):
        native = SimpleNamespace(has_focus=Mock(return_value=False),
                                 release_focus_to=Mock())
        root = SimpleNamespace(focus_set=Mock())
        desk = SimpleNamespace(display_mode="mini", _modal=False,
                               current_tab="notes", root=root, bidi_editor=native,
                               _bidi_active=Mock(return_value=True),
                               _flush_current_note=Mock())
        PocketDesk._mini_click_outside_editor(desk, SimpleNamespace(widget=object()))
        native.release_focus_to.assert_not_called()
        root.focus_set.assert_called_once()

    def test_direction_change_clears_modal_guard_without_unmap(self):
        menu = SimpleNamespace(unpost=Mock(), winfo_exists=Mock(return_value=True))
        desk = SimpleNamespace(_note_context_menu=menu,
                               _note_context_menu_was_modal=False,
                               _modal=True)
        # Attach the same bound helper a real PocketDesk instance provides.
        # The bare SimpleNamespace fixture does not implement this method.
        desk._release_note_context_menu = lambda item: PocketDesk._release_note_context_menu(desk, item)
        # The selection callback closes and clears the modal guard even if
        # Win32 does not dispatch Tk's <Unmap> for the menu.
        PocketDesk._finish_note_context_menu_action(desk)
        self.assertFalse(desk._modal)
        self.assertIsNone(desk._note_context_menu)
        menu.unpost.assert_called_once()

    def test_prior_modal_state_is_preserved(self):
        menu = object()
        desk = SimpleNamespace(_note_context_menu=menu,
                               _note_context_menu_was_modal=True,
                               _modal=True)
        PocketDesk._release_note_context_menu(desk, menu)
        self.assertTrue(desk._modal)
        self.assertIsNone(desk._note_context_menu)

    def test_no_focus_change_in_normal_mode_or_other_tools(self):
        desk = SimpleNamespace(display_mode="normal", _modal=False,
                               current_tab="commands", root=SimpleNamespace(focus_set=Mock()))
        PocketDesk._mini_click_outside_editor(desk, SimpleNamespace(widget=object()))
        desk.display_mode = "mini"
        desk.current_tab = "ports"
        PocketDesk._mini_click_outside_editor(desk, SimpleNamespace(widget=object()))
        desk.root.focus_set.assert_not_called()

    def test_no_focus_change_while_modal_open(self):
        desk = SimpleNamespace(display_mode="mini", _modal=True,
                               current_tab="notes", root=SimpleNamespace(focus_set=Mock()))
        PocketDesk._mini_click_outside_editor(desk, SimpleNamespace(widget=object()))
        desk.root.focus_set.assert_not_called()


if __name__ == "__main__":
    import unittest
    unittest.main()
