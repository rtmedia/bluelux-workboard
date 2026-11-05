import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import doctor
import server
import service


class SetupTests(unittest.TestCase):
    def test_demo_does_not_read_private_sources_or_check_login(self):
        with patch.object(doctor, 'port_status', return_value=('ok', 'available')), patch.object(server.CodexReader, 'index') as index, patch('configuration.load') as config, patch.object(doctor.subprocess, 'run') as run:
            checks = doctor.inspect(demo=True, github=True)
            index.assert_not_called()
            config.assert_not_called()
            run.assert_not_called()
            self.assertTrue(any(c['check'] == 'Sources' for c in checks))

    def test_fresh_missing_index_is_an_error_without_installing_anything(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'CODEX_HOME': folder}), patch.object(doctor, 'port_status', return_value=('ok', 'available')), patch.object(doctor.shutil, 'which', return_value=None), patch.object(doctor.subprocess, 'run') as run:
            checks = doctor.inspect(config=Path(folder)/'absent.json')
            by_name = {c['check']: c for c in checks}
            self.assertEqual(by_name['Codex']['status'], 'error')
            self.assertEqual(by_name['Git']['status'], 'error')
            self.assertEqual(by_name['GitHub CLI']['status'], 'warning')
            run.assert_not_called()

    def test_valid_empty_index_is_not_claimed_as_complete_discovery(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {'CODEX_HOME': folder}), patch.object(doctor, 'port_status', return_value=('ok', 'available')):
            conn = sqlite3.connect(Path(folder)/'state_5.sqlite')
            conn.execute('CREATE TABLE threads (id TEXT, cwd TEXT, title TEXT, rollout_path TEXT, updated_at INTEGER, source TEXT, archived INTEGER)')
            conn.close()
            checks = doctor.inspect(config=Path(folder)/'absent.json')
            by_name = {c['check']: c for c in checks}
            self.assertEqual(by_name['Codex']['status'], 'ok')
            self.assertEqual(by_name['Discovery']['status'], 'warning')
            self.assertIn('not validated', by_name['Codex']['detail'])

    def test_auth_is_optional_and_does_not_echo_credentials(self):
        with patch.object(doctor, 'port_status', return_value=('ok', 'available')), patch.object(doctor.shutil, 'which', return_value='/example/bin/tool'), patch.object(server.CodexReader, 'index', return_value=([], [], 'state_5.sqlite')), patch('configuration.load', return_value=None), patch.object(doctor.subprocess, 'run', return_value=Mock(returncode=0, stdout=b'SYNTHETIC_SECRET', stderr=b'SYNTHETIC_SECRET')) as run:
            doctor.inspect()
            run.assert_not_called()
            checks = doctor.inspect(github=True)
            self.assertEqual(run.call_args.args[0][1:], ['auth', 'status', '--hostname', 'github.com'])
            self.assertNotIn('SYNTHETIC_SECRET', json.dumps(checks))

    def test_other_checkout_on_port_is_not_success(self):
        response = Mock(status=200)
        response.read.return_value = json.dumps({'app': 'workboard', 'root': '/another/checkout', 'status': 'ready'}).encode()
        with patch.object(doctor.socket, 'socket') as sock, patch.object(doctor.http.client, 'HTTPConnection') as connection:
            sock.return_value.__enter__.return_value.bind.side_effect = OSError('occupied')
            connection.return_value.getresponse.return_value = response
            self.assertEqual(doctor.port_status(43127)[0], 'error')
            response.read.return_value = json.dumps({'app': 'workboard', 'root': str(doctor.ROOT), 'status': 'starting'}).encode()
            status, detail = doctor.port_status(43127)
            self.assertEqual(status, 'ok')
            self.assertIn('starting', detail)

    def test_service_carries_selected_paths_but_not_token_environment(self):
        with patch.dict(os.environ, {'PATH': '/custom/bin:/usr/bin', 'CODEX_HOME': '/custom/codex', 'GH_CONFIG_DIR': '/custom/gh', 'GH_TOKEN': 'SYNTHETIC_SECRET'}, clear=True):
            config = service.configuration(Path('/app'), '/custom/python3')
        env = config['EnvironmentVariables']
        self.assertEqual(env['PATH'], '/custom/bin:/usr/bin')
        self.assertEqual(env['CODEX_HOME'], '/custom/codex')
        self.assertEqual(env['GH_CONFIG_DIR'], '/custom/gh')
        self.assertNotIn('GH_TOKEN', env)
        self.assertEqual(config['ProgramArguments'][0], '/custom/python3')


if __name__ == '__main__':
    unittest.main()
