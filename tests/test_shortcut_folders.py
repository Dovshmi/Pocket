"""Organizer migration, folder operations and deterministic mouse reorder semantics."""
import copy
import unittest

from pocket import shortcut_folders as sf


def links():
    return [
        {"id": "a", "title": "YouTube", "url": "https://youtube.com", "kind": "url"},
        {"id": "b", "title": "Gmail", "url": "https://mail.google.com", "kind": "url"},
        {"id": "c", "title": "Router", "url": "https://router.example", "kind": "url"},
        {"id": "d", "title": "File", "url": "C:/example", "kind": "file"},
    ]


class ShortcutFoldersTests(unittest.TestCase):
    def make_layout(self):
        return sf.normalize(None, links())

    def test_legacy_migration_preserves_order_and_targets(self):
        before = copy.deepcopy(links())
        layout = sf.normalize(None, before)
        self.assertEqual(layout["root"], ["l:a", "l:b", "l:c", "l:d"])
        self.assertEqual(layout["folders"], [])
        self.assertEqual(before, links())
        self.assertEqual(sf.normalize(layout, before), layout)

    def test_folder_creation_does_not_change_disk_folder_shortcuts(self):
        layout = self.make_layout()
        folder = sf.add_folder(layout, " My   sites ")
        self.assertEqual(layout["folders"][0]["title"], "My sites")
        self.assertIn("f:" + folder, layout["root"])
        self.assertEqual(layout["root"][:4], ["l:a", "l:b", "l:c", "l:d"])

    def test_organize_and_reorder_inside_folder(self):
        layout = self.make_layout()
        group = sf.add_folder(layout, "Sites")
        self.assertTrue(sf.move(layout, "l:a", "f:" + group, "inside"))
        self.assertTrue(sf.move(layout, "l:c", "f:" + group, "inside"))
        self.assertTrue(sf.move(layout, "l:c", "l:a", "before"))
        self.assertEqual(layout["children"][group], ["c", "a"])
        self.assertFalse(sf.move(layout, "l:c", "l:a", "before"))
        self.assertEqual(sf.link_folder(layout, "a"), group)
        self.assertEqual(sf.link_folder(layout, "b"), None)

    def test_move_between_folders_and_unfile_again(self):
        layout = self.make_layout()
        first = sf.add_folder(layout, "First")
        second = sf.add_folder(layout, "Second")
        self.assertTrue(sf.move(layout, "l:a", "f:" + first, "inside"))
        self.assertTrue(sf.move(layout, "l:a", "f:" + second, "inside"))
        self.assertEqual(layout["children"][first], [])
        self.assertEqual(layout["children"][second], ["a"])
        self.assertTrue(sf.move(layout, "l:a", "root"))
        self.assertEqual(layout["root"][0], "l:a")
        self.assertEqual(layout["children"][second], [])

    def test_reorder_folder_headers_and_root_shortcuts(self):
        layout = self.make_layout()
        first = sf.add_folder(layout, "One")
        second = sf.add_folder(layout, "Two")
        self.assertTrue(sf.move(layout, sf.folder_key(second), sf.folder_key(first),
                                "before"))
        self.assertEqual(layout["root"][-2:],
                         [sf.folder_key(second), sf.folder_key(first)])
        self.assertTrue(sf.move(layout, "l:d", sf.folder_key(second), "after"))
        self.assertEqual(layout["root"][-3:],
                         [sf.folder_key(second), "l:d", sf.folder_key(first)])

    def test_delete_folder_keeps_all_shortcuts(self):
        layout = self.make_layout()
        group = sf.add_folder(layout, "Temporary")
        sf.move(layout, "l:b", "f:" + group, "inside")
        sf.move(layout, "l:a", "f:" + group, "inside")
        self.assertTrue(sf.delete_folder(layout, group))
        self.assertEqual(layout["root"], ["l:c", "l:d", "l:b", "l:a"])
        self.assertNotIn(group, layout["children"])
        self.assertEqual(layout["folders"], [])

    def test_remove_link_and_new_link_do_not_change_other_items(self):
        layout = self.make_layout()
        group = sf.add_folder(layout, "Misc")
        sf.move(layout, "l:b", "f:" + group, "inside")
        self.assertTrue(sf.remove_link(layout, "b"))
        self.assertEqual(layout["children"][group], [])
        self.assertTrue(sf.add_link(layout, "new"))
        self.assertEqual(layout["root"][0], "l:new")
        self.assertFalse(sf.add_link(layout, "new"))

    def test_collapse_and_search_temporarily_expands(self):
        layout = self.make_layout()
        group = sf.add_folder(layout, "Network")
        sf.move(layout, "l:c", "f:" + group, "inside")
        self.assertTrue(sf.set_expanded(layout, group, False))
        all_rows = sf.visible_rows(layout, links())
        folder_row = next(r for r in all_rows if r["type"] == "folder")
        self.assertFalse(folder_row["expanded"])
        self.assertEqual(folder_row["total"], 1)
        searched = sf.visible_rows(layout, links(), query="Router")
        folder_row = next(r for r in searched if r["type"] == "folder")
        self.assertTrue(folder_row["expanded"])
        self.assertEqual([x["id"] for x in folder_row["links"]], ["c"])
        self.assertFalse(layout["folders"][0]["expanded"])
        searched_title = sf.visible_rows(layout, links(), query="Network")
        self.assertEqual(searched_title[0]["links"][0]["id"], "c")

    def test_kind_filters_keep_organizer_without_folders_as_links(self):
        layout = self.make_layout()
        fid = sf.add_folder(layout, "Web")
        sf.move(layout, "l:a", "f:" + fid, "inside")
        self.assertEqual(len([r for r in sf.visible_rows(
            layout, links(), kind="file") if r["type"] == "link"]), 1)
        self.assertFalse(any(r["type"] == "folder" for r in sf.visible_rows(
            layout, links(), kind="file")))

    def test_malformed_profile_deduplicates_and_keeps_orphans(self):
        raw = {
            "folders": [
                {"id": "x", "title": "OK", "expanded": False},
                {"id": "x", "title": "Duplicate"},
                {"id": "bad", "title": ""},
            ],
            "root": ["f:x", "f:x", "l:b", "l:b", "l:unknown"],
            "children": {"x": ["a", "a", "b", "unknown"]},
        }
        layout = sf.normalize(raw, links())
        self.assertEqual(len(layout["folders"]), 1)
        self.assertEqual(layout["root"], ["f:x", "l:b", "l:c", "l:d"])
        self.assertEqual(layout["children"], {"x": ["a"]})
        self.assertEqual(sf.normalize(layout, links()), layout)

    def test_invalid_drag_does_not_modify_data(self):
        layout = self.make_layout()
        fid = sf.add_folder(layout, "Folder")
        original = copy.deepcopy(layout)
        self.assertFalse(sf.move(layout, "f:" + fid, "f:" + fid, "inside"))
        self.assertFalse(sf.move(layout, "f:" + fid, "root"))
        self.assertFalse(sf.move(layout, "l:a", "l:invalid"))
        self.assertFalse(sf.move(layout, "f:" + fid, "l:invalid", "before"))
        self.assertEqual(layout, original)

    def test_folder_rename_validation(self):
        layout = self.make_layout()
        fid = sf.add_folder(layout, "Initial")
        self.assertTrue(sf.rename_folder(layout, fid, "Work"))
        self.assertFalse(sf.rename_folder(layout, fid, "Work"))
        with self.assertRaises(ValueError):
            sf.rename_folder(layout, fid, "   ")
        self.assertEqual(layout["folders"][0]["title"], "Work")


if __name__ == "__main__":
    unittest.main()
