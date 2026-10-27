"""Custom command persistence / safety / lookup regression tests."""
from pathlib import Path
import runpy
import tempfile
import unittest
import command_helper as ch

ROOT = Path(__file__).resolve().parent
APP = runpy.run_path(str(ROOT/'app.pyw'), run_name='test_import_custom')


class CustomCommandTests(unittest.TestCase):
    def test_create_and_search_by_machine_description_or_command(self):
        item = ch.validate_custom_command('Cisco', 'Interfaces', 'Check current link state',
                                           'show interfaces GigabitEthernet0/0/1')
        self.assertTrue(item['id'].startswith('user:'))
        library = ch.merged_commands([], [item])
        self.assertEqual(ch.find_commands(library, 'link state', machine='Cisco')[0]['id'], item['id'])
        self.assertEqual(ch.find_commands(library, 'gigabitethernet', machine='Cisco')[0]['id'], item['id'])
        self.assertEqual(ch.find_commands(library, 'link', machine='Juniper'), [])

    def test_custom_save_survives_restart_and_migration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'data.json'
            data = APP['default_data']()
            custom = ch.validate_custom_command('My Switch', 'Custom', 'Find the port',
                                                'show interface <PORT>')
            data['custom_commands'] = [custom]
            data['command_state']['machine'] = custom['machine']
            data['command_state']['favorites'] = [custom['id']]
            APP['save_data'](path, data)
            loaded = APP['load_data'](path)
            self.assertEqual(loaded['custom_commands'], [custom])
            self.assertEqual(loaded['command_state']['favorites'], [custom['id']])
            self.assertIn('My Switch', ch.machines_for(ch.merged_commands([], loaded['custom_commands'])))
            # Old settings (v1.7) gain a new custom_commands list automatically.
            del data['custom_commands']
            APP['save_data'](path, data)
            self.assertEqual(APP['load_data'](path)['custom_commands'], [])

    def test_edit_preserves_identity_and_favorites(self):
        old = ch.validate_custom_command('Cisco', 'Routing', 'Old purpose', 'show ip route')
        updated = ch.validate_custom_command('Cisco', 'Routing', 'New purpose',
                                              'show route vrf <VRF>', identifier=old['id'])
        self.assertEqual(updated['id'], old['id'])
        self.assertNotEqual(updated['command'], old['command'])
        self.assertEqual(ch.find_commands([updated], 'new purpose')[0], updated)

    def test_input_validation(self):
        for machine, description, category, command in (
            ('', 'test', 'General', 'show version'),
            (ch.ALL_MACHINES, 'test', 'General', 'show version'),
            ('Cisco', '', 'General', 'show version'),
            ('Cisco', 'test', '', 'show version'),
            ('Cisco', 'test', 'General', ''),
            ('Cisco', 'test', 'General', 'X'*6001),
        ):
            with self.subTest(machine=machine, description=description):
                with self.assertRaises(ValueError):
                    ch.validate_custom_command(machine, category, description, command)

    def test_invalid_local_records_ignored(self):
        item = ch.validate_custom_command('Cisco', 'Custom', 'port status', 'show interfaces status')
        malformed = dict(item, id='packaged-collision')
        self.assertEqual(ch.safe_custom_commands([item, malformed, item, 'junk']), [item])
        self.assertEqual(ch.safe_custom_commands(None), [])

    def test_not_written_into_private_pack(self):
        custom = ch.validate_custom_command('Cisco', 'Custom', 'My new test command', 'show fake custom')
        packaged = ch.load_library(ROOT/'commands'/'commands.json')
        self.assertNotIn(custom['id'], [x['id'] for x in packaged])
        self.assertEqual(len(ch.merged_commands(packaged, [custom])), len(packaged)+1)


if __name__ == '__main__':
    unittest.main()
