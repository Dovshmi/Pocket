import json
from pathlib import Path
import runpy
import tempfile
import unittest
import command_helper as ch

ROOT = Path(__file__).resolve().parent
run_app = runpy.run_path(str(ROOT / 'app.pyw'), run_name='test_import_command')

class CommandHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = ch.load_library(ROOT / 'commands' / 'sample_commands.json')

    def test_bundle_exists_and_excludes_original_workbook(self):
        self.assertGreaterEqual(len(self.entries), 10)
        self.assertGreaterEqual(len(ch.machines_for(self.entries)), 3)
        self.assertFalse(list(ROOT.glob('*.xls*')))

    def test_finds_commands_by_description_and_command(self):
        self.assertTrue(ch.find_commands(self.entries, 'show ip route', machine='Cisco'))
        self.assertTrue(ch.find_commands(self.entries, 'routing table', machine='Cisco'))
        self.assertEqual(ch.find_commands(self.entries, 'no-such-cmd-998'), [])

    def test_machine_filter(self):
        found = ch.find_commands(self.entries, 'show', machine='FortiGate')
        self.assertTrue(found)
        self.assertTrue(all(x['machine']=='FortiGate' for x in found))

    def test_category_filter(self):
        found = ch.find_commands(self.entries, category='Routing')
        self.assertTrue(found)
        self.assertTrue(all(x['category']=='Routing' for x in found))

    def test_favorites_and_recent(self):
        one=self.entries[0]['id'];two=self.entries[1]['id']
        self.assertEqual(ch.updated_recent([one],two),[two,one])
        self.assertEqual([e['id'] for e in ch.find_commands(self.entries,mode='favorites',favorites=[one])],[one])
        self.assertEqual([e['id'] for e in ch.find_commands(self.entries,mode='recent',recent=[two,one])],[two,one])

    def test_old_data_migrates_without_loss(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.json'
            orig=run_app['default_data']()
            del orig['command_state']
            run_app['save_data'](p,orig)
            loaded=run_app['load_data'](p)
            self.assertEqual(loaded['notes'],orig['notes'])
            self.assertEqual(loaded['links'],orig['links'])
            self.assertEqual(loaded['command_state']['favorites'],[])

    def test_sensitive_content_scan(self):
        import re
        for row in self.entries:
            data=row['description']+' '+row['command']
            with self.subTest(machine=row['machine'],id=row['id']):
                self.assertNotRegex(data,r'(?i)password|passwd|secret|bearer|api.?key|credential|token|סיסמ|סיסמא')
                self.assertNotRegex(data,r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])')
                self.assertNotRegex(data,r'https?://[^\s]+')
                self.assertNotRegex(data,r'[\w.-]+@[\w.-]+')

if __name__=='__main__':unittest.main()
