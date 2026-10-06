import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import server


def event(kind, payload, stamp='2026-10-05T12:00:00Z'):
    return json.dumps({'type': kind, 'timestamp': stamp, 'payload': payload})


class ConversationTests(unittest.TestCase):
    def test_reads_messages_and_actual_workdir_but_not_reasoning_or_tool_output(self):
        lines = [
            event('event_msg', {'type': 'user_message', 'message': '## My request:\nTrack my work'}),
            event('response_item', {'type': 'reasoning', 'summary': ['PRIVATE REASONING']}),
            event('response_item', {'type': 'function_call_output', 'output': 'PRIVATE OUTPUT'}),
            event('event_msg', {'type': 'item_completed', 'item': {'type': 'CommandExecution', 'cwd': 'file:///tmp/a%20folder', 'stdout': 'PRIVATE OUTPUT'}}),
            event('response_item', {'type': 'message', 'role': 'assistant', 'phase': 'final_answer', 'content': [{'text': 'Saved [PR](https://github.com/org/repo/pull/12).'}]}),
            event('event_msg', {'type': 'task_complete', 'last_agent_message': 'Saved [PR](https://github.com/org/repo/pull/12).'}),
        ]
        result = server.parse_events(lines)
        self.assertEqual(result['request'], 'Track my work')
        self.assertEqual(result['workdirs'], ['/tmp/a folder'])
        self.assertEqual(result['turnState'], 'finished')
        self.assertEqual(result['prs'], ['https://github.com/org/repo/pull/12'])
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_new_request_remains_distinct_from_previous_completed_response(self):
        result = server.parse_events([
            event('event_msg', {'type': 'task_complete', 'last_agent_message': 'The earlier fix was shipped.'}, '2026-10-04T12:00:00Z'),
            event('event_msg', {'type': 'task_started'}, '2026-10-05T12:00:00Z'),
            event('event_msg', {'type': 'user_message', 'message': 'Build a new dashboard.'}, '2026-10-05T12:00:01Z'),
        ])
        self.assertEqual(result['turnState'], 'started')
        self.assertGreater(result['requestAt'], result['responseAt'])
        self.assertEqual(result['response'], 'The earlier fix was shipped.')

    def test_broken_tail_line_is_skipped(self):
        result = server.parse_events(['not json', event('event_msg', {'type': 'turn_aborted'})])
        self.assertEqual(result['turnState'], 'interrupted')

    def test_choice_reply_is_readable_context(self):
        text = '<send_user_message_question_reply>[{"question":"Where?","answer":"On my Mac"}]</send_user_message_question_reply>'
        self.assertEqual(server.request_text(text), 'Where?\nOn my Mac')

    def test_cannot_read_index_referenced_files_outside_sessions(self):
        with tempfile.TemporaryDirectory() as tmp:
            secret = Path(tmp) / 'auth.json'
            secret.write_text('not a session')
            result = server.CodexReader(tmp).context({'rollout_path': str(secret)})
            self.assertIn('outside', result['contextError'])
            self.assertEqual(result['response'], '')


class GitTests(unittest.TestCase):
    def test_rename_source_is_not_miscounted_as_another_file(self):
        result = server.parse_status('R  new name.py\0old name.py\0 M modified.py\0?? work/\0')
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {'code': 'R ', 'path': 'new name.py'})

    def test_remote_normalization_deduplicates_ssh_and_https_without_exposing_credentials(self):
        expected = 'https://github.com/owner/project'
        self.assertEqual(server.normalize_remote('git@github.com:owner/project.git'), expected)
        self.assertEqual(server.normalize_remote('https://token@github.com/owner/project.git'), expected)
        self.assertIsNone(server.normalize_remote('https://github.com.attacker.test/owner/project'))

    def test_nested_project_checkout_is_not_attributed_to_parent(self):
        workspaces = [{'path': '/repos/parent'}, {'path': '/repos/parent/work/child'}]
        result = server.linked_workspaces(['/repos/parent/work/child/backend'], workspaces,
                                         {'/repos/parent/work/child/backend': {'root': '/repos/parent/work/child'}})
        self.assertEqual(result, ['/repos/parent/work/child'])

    def test_shared_checkout_and_second_checkout_are_both_linked(self):
        workspaces = [{'path': '/repo'}, {'path': '/worktrees/fix'}]
        result = server.linked_workspaces(['/repo', '/worktrees/fix/frontend'], workspaces, {})
        self.assertEqual(result, ['/repo', '/worktrees/fix'])

    def test_failed_git_status_is_not_a_clean_checkout(self):
        with patch.object(server, 'git', return_value=(None, 'Missing folder')):
            result = server.scan_checkout({'path': '/missing', 'repoId': 'id', 'label': 'Missing'})
        self.assertTrue(result['error'])
        self.assertIsNone(result['upstreamComparison'])


class SourceTests(unittest.TestCase):
    def test_unsupported_codex_schema_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = sqlite3.connect(Path(tmp) / 'state_5.sqlite')
            c.execute('CREATE TABLE threads (id TEXT)')
            c.close()
            with self.assertRaisesRegex(RuntimeError, 'format changed'):
                server.CodexReader(tmp).index()

    def test_github_failure_is_not_zero_open_prs(self):
        board = server.Board()
        board.snapshot = {'repositories': [{'id': 'r', 'remote': 'https://github.com/a/b'}]}
        with patch.object(server, 'run', return_value=(None, 'offline')):
            result = board.github_status('r')
        self.assertTrue(result['error'])
        self.assertNotIn('openPRs', result)

    def test_http_host_and_origin_restrictions(self):
        handler = server.Handler.__new__(server.Handler)
        handler.server = type('Server', (), {'server_port': 8080})()
        responses = []
        handler.send = lambda code, body: responses.append(code)
        for headers, expected in [
            ({'Host': '127.0.0.1:8080'}, True),
            ({'Host': 'evil.test:8080'}, False),
            ({'Host': '127.0.0.1:8080', 'Origin': 'https://evil.test'}, False),
            ({'Host': '127.0.0.1:8080', 'Sec-Fetch-Site': 'cross-site'}, False),
        ]:
            handler.headers = headers
            self.assertEqual(handler.allowed(), expected)


if __name__ == '__main__':
    unittest.main()
