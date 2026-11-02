"""Tests for the context-aware right-click editor menu and tab integration."""
from pathlib import Path
import runpy
import unittest

m = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app.pyw"), run_name="test_import")

class NoteContextHelpersTests(unittest.TestCase):
    def test_ip_requires_exact_ip_literal(self):
        valid = m['note_selection_ip']
        self.assertEqual(valid(' 192.168.1.25 '), '192.168.1.25')
        self.assertEqual(valid('2001:db8::1'), '2001:db8::1')
        for value in ('', 'invalid', '192.168.5.999', 'ping 192.168.1.1',
                      'https://192.168.1.1', '192.168.1.1/24'):
            with self.subTest(value=value):
                self.assertIsNone(valid(value))

    def test_commands_query_collapses_whitespace(self):
        q = m['note_command_query']
        self.assertEqual(q(' show  ip route\n'), 'show ip route')
        self.assertEqual(q('  \t\n '), '')
        self.assertLessEqual(len(q('x'*400)), 250)

if __name__ == "__main__":
    unittest.main()
