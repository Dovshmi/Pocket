"""Persistence, legacy migration and monitor clamping for draggable PocketDesk."""
from pathlib import Path
import runpy
import tempfile
import unittest

m = runpy.run_path(str(Path(__file__).parent / 'app.pyw'), run_name='test_import')


class WindowPositionTests(unittest.TestCase):
    def test_normalize_optional_position(self):
        normalize = m['normalize_window_position']
        self.assertEqual(normalize({'x': -450, 'y': 110}), {'x': -450, 'y': 110})
        for invalid in (None, '', [], {}, {'x': True, 'y': 3}, {'x': 2.0, 'y': 3},
                        {'x': '3', 'y': 4}, {'x': 250000, 'y': 0}):
            with self.subTest(invalid=invalid):
                self.assertIsNone(normalize(invalid))

    def test_clamp_to_monitor_with_negative_offsets(self):
        clamp = m['clamp_window_position']
        self.assertEqual(clamp(300, 400, 480, 850, (0, 0, 1920, 1080)), (300, 230))
        self.assertEqual(clamp(-900, 70, 480, 850, (-1600, 0, 0, 1000)), (-900, 70))
        self.assertEqual(clamp(5000, 5000, 480, 850, (-1600, 0, 0, 1000)), (-480, 150))

    def test_roundtrip_and_old_data_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'data.json'
            data = m['default_data']()
            self.assertIsNone(data['window_position'])
            data['window_position'] = {'x': 315, 'y': 72}
            m['save_data'](path, data)
            self.assertEqual(m['load_data'](path)['window_position'], {'x': 315, 'y': 72})
            del data['window_position']
            m['save_data'](path, data)
            self.assertIsNone(m['load_data'](path)['window_position'])


if __name__ == '__main__':
    unittest.main()
