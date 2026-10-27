"""Notes ordering, backward compatibility, and duplicate identity."""
from datetime import datetime, timezone
from pathlib import Path
import runpy
import tempfile
import unittest

api = runpy.run_path(str(Path(__file__).parent / 'app.pyw'), run_name='test_api')


class NotePinAndDuplicateTests(unittest.TestCase):
    def test_pinned_order_is_stable(self):
        notes = [{'id': 'a', 'pinned': False}, {'id': 'b', 'pinned': True},
                 {'id': 'c', 'pinned': False}, {'id': 'd', 'pinned': True}]
        result = api['ordered_notes'](notes)
        self.assertEqual([r['id'] for r in result], ['b', 'd', 'a', 'c'])
        self.assertEqual([r['id'] for r in notes], ['a', 'b', 'c', 'd'])

    def test_duplicate_preserves_fields_without_copying_id_or_timestamp(self):
        original = api['new_note']('Router', 'show ip route', '+972 50 1234567')
        original['pinned'] = True
        copy = api['duplicate_note'](original)
        self.assertNotEqual(original['id'], copy['id'])
        self.assertEqual(copy['title'], 'Router (copy)')
        self.assertEqual(copy['body'], original['body'])
        self.assertEqual(copy['phone'], original['phone'])
        self.assertFalse(copy['pinned'])
        self.assertIsNotNone(datetime.fromisoformat(copy['created_at']).tzinfo)

    def test_existing_notes_load_unpinned_and_pinned_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'data.json'
            data = api['default_data']()
            data['notes'][0].pop('pinned')
            api['save_data'](path, data)
            loaded = api['load_data'](path)
            self.assertFalse(loaded['notes'][0]['pinned'])
            loaded['notes'][0]['pinned'] = True
            api['save_data'](path, loaded)
            self.assertTrue(api['load_data'](path)['notes'][0]['pinned'])

    def test_non_boolean_pinned_value_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'data.json'
            data = api['default_data']()
            data['notes'][0]['pinned'] = 'false'
            api['save_data'](path, data)
            self.assertFalse(api['load_data'](path)['notes'][0]['pinned'])


if __name__ == '__main__':
    unittest.main()
