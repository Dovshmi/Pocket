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
