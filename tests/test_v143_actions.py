"""v1.43 regressions: explicit actions and in-memory state."""
import unittest
from types import SimpleNamespace
from pocket import command_palette as cp, extra_excel_ui

class V143Tests(unittest.TestCase):
    def test_action_alias(self):
        for marker in (">", "<"):
            hits = cp.results({}, [], marker + " extra cofix", ["extra"], {})
            self.assertEqual(hits[0]["id"], "extra")
            self.assertEqual(hits[0]["args"], ("cofix",))
        self.assertFalse(cp.results({}, [], "< extra cofix", ["notes"], {}))

    def test_completion(self):
        self.assertIn("> extra ", cp.completions("> ex", ["extra"]))
        self.assertNotIn("> extra ", cp.completions("> ex", ["notes"]))
        self.assertIn("< extra ", cp.completions("< ex", ["extra"]))
        self.assertFalse(cp.completions("ex", ["extra"]))

    def test_session_is_per_app(self):
        a, b = SimpleNamespace(), SimpleNamespace()
        state = extra_excel_ui.session(a)
        state["query"] = "sample"
        state["busy"] = True
        extra_excel_ui.detach(a)
        self.assertIs(extra_excel_ui.session(a), state)
        self.assertTrue(state["busy"])
        self.assertEqual(extra_excel_ui.session(b)["query"], "")

if __name__ == "__main__":
    unittest.main()
