"""External shortcut drop routes directly into a Pocket organizer folder."""
import runpy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from pocket import shortcut_folders as sf

APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"),
                     run_name="test_import_shortcut_folder_drop")
Desk = APP["PocketDesk"]


def app_stub():
    link = {"id": "old", "title": "Existing", "url": "https://example.com",
            "kind": "url"}
    layout = sf.normalize(None, [link])
    group = sf.add_folder(layout, "Work")
    fake = SimpleNamespace()
    fake.current_tab = "links"
    fake.data = {"links": [link], "shortcut_folders": layout}
    fake._drop_leave = Mock()
    fake._warning = Mock()
    fake._toggle_link_form = Mock()
    fake.schedule_save = Mock()
    fake.refresh_links = Mock()
    fake.root = SimpleNamespace(
        tk=SimpleNamespace(splitlist=lambda x: (x,)),
        after_idle=Mock())
    return fake, group


class ExternalFolderDropTests(unittest.TestCase):
    def test_dragged_url_saves_directly_to_folder(self):
        app, group = app_stub()
        result = Desk._shortcut_dropped(
            app, SimpleNamespace(data="https://github.com/example/repo"),
            folder_id=group)
        self.assertEqual(result, "copy")
        self.assertEqual(len(app.data["links"]), 2)
        item = app.data["links"][0]
        self.assertEqual(item["url"], "https://github.com/example/repo")
        self.assertEqual(sf.link_folder(app.data["shortcut_folders"],
                                        item["id"]), group)
        self.assertTrue(app.data["shortcut_folders"]["folders"][0]["expanded"])
        app.schedule_save.assert_called_once()
        app.root.after_idle.assert_called_once()
        app._toggle_link_form.assert_not_called()
        app._warning.assert_not_called()

    def test_folder_drop_never_opens_existing_shortcut(self):
        app, group = app_stub()
        app.open_shortcut = Mock()
        Desk._shortcut_dropped(
            app, SimpleNamespace(data="https://www.youtube.com"), folder_id=group)
        app.open_shortcut.assert_not_called()
        app._toggle_link_form.assert_not_called()

    def test_invalid_folder_ref_refuses_to_write(self):
        app, _ = app_stub()
        answer = Desk._shortcut_dropped(
            app, SimpleNamespace(data="https://example.org"), folder_id="unknown")
        self.assertEqual(answer, "refuse_drop")
        self.assertEqual(len(app.data["links"]), 1)
        app.schedule_save.assert_not_called()

    def test_malformed_external_drop_keeps_existing_items(self):
        app, group = app_stub()
        answer = Desk._shortcut_dropped(
            app, SimpleNamespace(data="javascript:alert(1)"), folder_id=group)
        self.assertEqual(answer, "refuse_drop")
        self.assertEqual(len(app.data["links"]), 1)
        app.schedule_save.assert_not_called()
        app._warning.assert_called_once()

    def test_root_drop_still_requires_explicit_editable_form(self):
        app, _ = app_stub()
        app.drop_title = SimpleNamespace(config=Mock())
        app.drop_hint = SimpleNamespace(config=Mock())
        app._scroll_canvas = None
        result = Desk._shortcut_dropped(
            app, SimpleNamespace(data="https://example.org"), folder_id=None)
        self.assertEqual(result, "copy")
        self.assertEqual(len(app.data["links"]), 1)
        app._toggle_link_form.assert_called_once()
        kwargs = app._toggle_link_form.call_args.kwargs
        self.assertEqual(kwargs["draft"]["url"], "https://example.org")
        app.schedule_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
