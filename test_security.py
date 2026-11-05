"""Adversarial local-source regression tests; synthetic data only."""
import os
import io
from unittest.mock import patch, Mock
from pathlib import Path
import subprocess
import tempfile
import unittest

import roadmaps
import server


class SourceSecurityTests(unittest.TestCase):
    def test_check_command_does_not_start_remote_background_work(self):
        board = Mock(error=None, snapshot={'threads': [], 'projects': [], 'workspaces': [], 'coverage': {}})
        with patch.object(server, 'BOARD', board), patch('sys.argv', ['server.py', '--check']), patch('sys.stdout', io.StringIO()):
            server.main()
        board._refresh.assert_called_once_with(remote=False)

    def test_git_scan_does_not_execute_repository_monitor(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q', folder], check=True)
            marker = root / 'executed'
            helper = root / 'monitor.sh'
            helper.write_text('#!/bin/sh\nprintf unsafe > "' + str(marker) + '"\n')
            helper.chmod(0o700)
            subprocess.run(['git', '-C', folder, 'config', 'core.fsmonitor', str(helper)], check=True)
            result, error = server.git(root, 'status', '--porcelain')
            self.assertIsNone(error)
            self.assertIsNotNone(result)
            self.assertFalse(marker.exists())

    def test_git_filters_make_status_unknown_without_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            subprocess.run(['git', 'init', '-q', folder], check=True)
            marker = root / 'filter-executed'
            helper = root / 'filter.sh'
            helper.write_text('#!/bin/sh\nprintf unsafe > "' + str(marker) + '"\n')
            helper.chmod(0o700)
            subprocess.run(['git', '-C', folder, 'config', 'filter.example.clean', str(helper)], check=True)
            (root / '.gitattributes').write_text('*.txt filter=example\n')
            (root / 'sample.txt').write_text('synthetic content')
            blob = subprocess.check_output(['git', '-C', folder, 'hash-object', '-w', '--stdin'], input=b'synthetic content').decode().strip()
            subprocess.run(['git', '-C', folder, 'update-index', '--add', '--cacheinfo', '100644,' + blob + ',sample.txt'], check=True)
            result, error = server.git(root, 'status', '--porcelain')
            self.assertIsNone(result)
            self.assertIn('External Git filters', error)
            self.assertFalse(marker.exists())

    def test_documents_reject_symlinks_traversal_and_special_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / '.env').write_text('SYNTHETIC_PRIVATE_VALUE=example')
            (root / 'README.md').symlink_to('.env')
            self.assertIsNone(roadmaps.read_safe(root, 'README.md'))
            (root / 'real').mkdir()
            (root / 'real' / 'guide.md').write_text('safe content')
            (root / 'docs').symlink_to('real', target_is_directory=True)
            self.assertIsNone(roadmaps.read_safe(root, 'docs/guide.md'))
            self.assertIsNone(roadmaps.read_safe(root, '../outside.md'))
            self.assertIsNone(roadmaps.read_safe(root, str(root / '.env')))
            os.mkfifo(root / 'pipe.md')
            self.assertIsNone(roadmaps.read_safe(root, 'pipe.md'))
            self.assertEqual(roadmaps.read_safe(root, 'real/guide.md'), 'safe content')

    def test_documents_are_bounded_and_blob_uses_exact_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = b'line\r\n\xff'
            (root / 'README.md').write_bytes(data)
            self.assertEqual(roadmaps.read_safe_bytes(root, 'README.md'), data)
            (root / 'README.md').write_bytes(b'x' * (roadmaps.LIMIT + 1))
            self.assertIsNone(roadmaps.read_safe(root, 'README.md'))

    def test_session_fifo_is_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'sessions').mkdir()
            path = root / 'sessions' / 'session.jsonl'
            os.mkfifo(path)
            result = server.CodexReader(root).context({'rollout_path': str(path)})
            self.assertTrue(result['contextError'])


if __name__ == '__main__':
    unittest.main()
