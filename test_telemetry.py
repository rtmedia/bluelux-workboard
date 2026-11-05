import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import configuration
import demo
import server
import telemetry

class CompanionTests(unittest.TestCase):
    def test_allowlist_and_malformed_values(self):
        out = telemetry.snapshot({'info':{'last_token_usage':{'total_tokens':80},'total_token_usage':{'total_tokens':900},'model_context_window':100},'rate_limits':{'primary':{'used_percent':150,'resets_at':float('nan')},'credits':{'secret':'private'}},'secret':'private'}, 'date')
        self.assertEqual(out['lastTokens'],80)
        self.assertEqual(out['totalTokens'],900)
        self.assertIsNone(out['windows'][0]['usedPercent'])
        self.assertIsNone(out['windows'][0]['resetsAt'])
        self.assertNotIn('private',json.dumps(out))
        self.assertIsNone(telemetry.snapshot({'info':[],'rate_limits':None},None)['contextWindow'])
        self.assertIsNone(telemetry.number(True))

    def test_bounded_events_include_telemetry_and_compactions(self):
        lines=[json.dumps(v) for v in [[],{'type':'compacted','payload':{}},{'type':'turn_context','payload':{'model':'test'}},{'type':'event_msg','timestamp':'now','payload':{'type':'token_count','info':{'model_context_window':100}}}]]
        out=server.parse_events(lines)
        self.assertEqual(out['compactionsObserved'],1)
        self.assertEqual(out['model'],'test')
        self.assertEqual(out['telemetry']['contextWindow'],100)
        self.assertEqual(out['lastActivityAt'],'now')

    def test_generic_default_and_explicit_scope(self):
        projects=[{'name':'Example','kind':'git','remote':'https://github.com/any/example'}, {'name':'Other conversations','kind':'chats'}]
        configuration.apply(projects,None)
        self.assertTrue(projects[0]['core']);self.assertFalse(projects[1]['core'])
        configuration.apply(projects,{'example':'My project'})
        self.assertEqual(projects[0]['displayName'],'My project')
        configuration.apply(projects,{})
        self.assertFalse(projects[0]['core'])
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'config.json'
            self.assertIsNone(configuration.load(p))
            p.write_text('{"projects":[]}')
            with self.assertRaises(ValueError):configuration.load(p)

    def test_demo_never_reads_host_sources(self):
        board=server.Board();board.demo=True
        with patch.object(board.reader,'index',side_effect=AssertionError('host read')), patch.object(board.delivery,'refresh',side_effect=AssertionError('GitHub read')), patch.object(server,'git',side_effect=AssertionError('Git read')):
            board._refresh()
        self.assertIsNone(board.error)
        self.assertTrue(board.snapshot['demo'])
        self.assertIn('error',board.reveal_workspace('/demo/atlas'))
        self.assertEqual(board.detail('demo-approval')['id'],'demo-approval')
        before=board.snapshot['threads'];board._refresh()
        self.assertEqual(before,board.snapshot['threads'])

if __name__=='__main__':unittest.main()
