"""v1.14 timestamp, legacy migration and selected-note Notepad export tests."""
from datetime import datetime, timezone
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

m = runpy.run_path(str(Path(__file__).parent / 'app.pyw'), run_name='test_import')


class NewNotesTests(unittest.TestCase):
    def test_created_at_is_real_utc_instant_and_survives_reload(self):
        before = datetime.now(timezone.utc)
        note = m['new_note']('Test', 'sample')
        after = datetime.now(timezone.utc)
        saved_at = datetime.fromisoformat(note['created_at'])
        self.assertTrue(before.replace(microsecond=0) <= saved_at <= after)
        with tempfile.TemporaryDirectory() as home:
            filename = Path(home) / 'data.json'
            data = m['default_data']()
            data['notes'] = [note]
            data['active_note'] = note['id']
            m['save_data'](filename, data)
            self.assertEqual(m['load_data'](filename)['notes'][0]['created_at'], note['created_at'])

    def test_legacy_notes_do_not_get_fake_created_at(self):
        with tempfile.TemporaryDirectory() as home:
            filename = Path(home) / 'data.json'
            data = m['default_data']()
            data['notes'][0].pop('created_at')
            m['save_data'](filename, data)
            loaded = m['load_data'](filename)
            self.assertEqual(loaded['notes'][0]['created_at'], '')
            self.assertIn('unknown', m['display_created_at'](loaded['notes'][0]['created_at']))

    def test_notepad_snapshots_preserve_unicode_and_keep_previous_edits(self):
        note = m['new_note']('My note: / test', 'עבודה\nSecond line\n🙏')
        with tempfile.TemporaryDirectory() as home:
            first = m['export_note_for_notepad'](note, Path(home))
            self.assertNotIn(':', first.name)
            self.assertEqual(first.read_text(encoding='utf-8-sig'), note['body'])
            first.write_text('Changed outside PocketDesk', encoding='utf-8-sig')
            second = m['export_note_for_notepad'](note, Path(home))
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(encoding='utf-8-sig'), 'Changed outside PocketDesk')
            self.assertEqual(second.read_text(encoding='utf-8-sig'), note['body'])

    def test_invalid_dates_are_unknown(self):
        self.assertIn('unknown', m['display_created_at']('not a date'))
        self.assertIn('unknown', m['display_created_at']('2026-10-27T11:00:00'))


if __name__ == '__main__':
    unittest.main()
