"""v1.39.9 Mini More/Less planning without touching the 346px header layout."""
import unittest

from pocket import mini_nav


class MiniNavigationOverflowTests(unittest.TestCase):
    def setUp(self):
        self.previous = ["notes", "links", "ports", "mac",
                         "commands", "subnet", "clipboard"]

    def test_eight_menus_use_more_in_the_eighth_slot(self):
        first, extra = mini_nav.plan_mini_icons(self.previous)
        self.assertEqual(first, tuple(self.previous + ["more"]))
        self.assertEqual(extra, (("settings",),))
        first, extra = mini_nav.plan_mini_icons(self.previous[:6], add_available=True)
        self.assertEqual(first, tuple(self.previous[:6] + ["settings", "plus"]))
        self.assertEqual(extra, ())

    def test_reminders_uses_more_and_an_additional_row_with_settings(self):
        first, extra = mini_nav.plan_mini_icons(self.previous + ["reminders"])
        self.assertEqual(first, tuple(self.previous + ["more"]))
        self.assertEqual(extra, (("reminders", "settings"),))
        self.assertEqual(len(first), mini_nav.COLUMNS)

    def test_future_tools_fill_rows_of_eight_without_changing_first_row(self):
        more = self.previous + ["reminders"] + [f"future-{i}" for i in range(20)]
        first, extra = mini_nav.plan_mini_icons(more)
        self.assertEqual(first, tuple(self.previous + ["more"]))
        self.assertTrue(all(len(row) <= mini_nav.COLUMNS for row in extra))
        self.assertEqual([item for row in extra for item in row],
                         more[7:] + ["settings"])

    def test_hidden_items_and_duplicates_never_create_fake_icons(self):
        first, extra = mini_nav.plan_mini_icons(
            ["notes", "notes", "settings", "clipboard", "clipboard"])
        # Settings is now reorderable; an explicit position must be honored.
        self.assertEqual(first, ("notes", "settings", "clipboard"))
        self.assertEqual(extra, ())
        with self.assertRaises(ValueError):
            mini_nav.plan_mini_icons(self.previous, columns=1)


if __name__ == "__main__":
    unittest.main()
