import http.client
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import instructions
import roadmaps
import server


class InstructionSourcesTests(unittest.TestCase):
    def test_product_playbooks_are_not_agent_instructions(self):
        self.assertEqual(roadmaps.category('docs/PLAYBOOK_CONTENT_PLAN.md'), 'plans')
        self.assertEqual(roadmaps.category('docs/PLAYBOOK_ARCHITECTURE.md'), 'design')
        self.assertEqual(roadmaps.category('ENGINEERING_PLAYBOOK.md'), 'instructions')
        self.assertEqual(roadmaps.category('AGENTS.override.md'), 'instructions')
        self.assertEqual(roadmaps.category('CHARTER.md'), 'design')
        self.assertEqual(roadmaps.category('vite.config.ts'), 'configuration')

    def test_override_selection_and_fresh_reads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'AGENTS.md').write_text('standard')
            (root / 'AGENTS.override.md').write_text('  \n')
            first = instructions.snapshot(root, root)
            self.assertEqual(first['selectedGlobalFile'], 'global')
            (root / 'AGENTS.override.md').write_text('override')
            self.assertEqual(instructions.snapshot(root, root)['selectedGlobalFile'], 'override')
            (root / 'AGENTS.md').write_text('changed')
            updated = instructions.snapshot(root, root)
            self.assertNotEqual(first['sources'][0]['sha256'], updated['sources'][0]['sha256'])
            self.assertEqual(updated['sources'][0]['content'], 'changed')

    def test_missing_symlink_large_file_and_invalid_text_are_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertIsNone(instructions.snapshot(root, root)['selectedGlobalFile'])
            (root / 'private').write_text('DO NOT READ')
            (root / 'AGENTS.override.md').symlink_to(root / 'private')
            result = instructions.snapshot(root, root)
            self.assertEqual(result['selectedGlobalFile'], 'unknown')
            self.assertNotIn('DO NOT READ', str(result))
            (root / 'AGENTS.md').write_bytes(b'a' * (instructions.LIMIT + 1))
            self.assertEqual(instructions.snapshot(root, root)['sources'][0]['status'], 'unavailable')
            (root / 'AGENTS.md').write_bytes(b'\xff')
            self.assertEqual(instructions.snapshot(root, root)['sources'][0]['status'], 'unavailable')

    def test_http_is_fixed_path_read_only_same_origin_and_no_store(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / 'AGENTS.md'
            file.write_text('instructions')
            with patch.object(server, 'CODEX_HOME', root), patch.object(server, 'ROOT', root):
                httpd = server.LocalServer(('127.0.0.1', 0), server.Handler)
                thread = threading.Thread(target=httpd.serve_forever, daemon=True)
                thread.start()
                def request(method, path, headers=None):
                    conn = http.client.HTTPConnection('127.0.0.1', httpd.server_port)
                    conn.request(method, path, headers=headers or {})
                    response = conn.getresponse()
                    result = response.status, dict(response.getheaders()), response.read()
                    conn.close()
                    return result
                try:
                    status, headers, body = request('GET', '/api/instructions')
                    self.assertEqual(status, 200)
                    self.assertEqual(headers['Cache-Control'], 'no-store')
                    self.assertIn(b'instructions', body)
                    self.assertEqual(request('GET', '/api/instructions?path=/etc/passwd')[0], 400)
                    self.assertEqual(request('POST', '/api/instructions')[0], 405)
                    self.assertEqual(request('GET', '/api/instructions', {'Origin': 'https://example.com'})[0], 403)
                    self.assertEqual(file.read_text(), 'instructions')
                finally:
                    httpd.shutdown()
                    httpd.server_close()
                    thread.join()


if __name__ == '__main__':
    unittest.main()
