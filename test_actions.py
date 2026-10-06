from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import server

class FinderTests(unittest.TestCase):
    def test_unindexed_path_is_rejected_without_launch(self):
        b=server.Board();b.snapshot={'workspaces':[{'path':'/known'}]}
        with patch.object(server,'run') as run:
            self.assertIn('error',b.reveal_workspace('/etc'))
            self.assertIn('error',b.reveal_workspace(['/known']))
            run.assert_not_called()

    def test_indexed_folder_uses_literal_argument_array(self):
        with tempfile.TemporaryDirectory(prefix='workboard space ') as root:
            b=server.Board();b.snapshot={'workspaces':[{'path':root}]}
            with patch.object(server.sys,'platform','darwin'), patch.object(server,'run',return_value=('',None)) as run:
                self.assertEqual(b.reveal_workspace(root),{'revealed':root})
                run.assert_called_once_with(['/usr/bin/open','-R',root],timeout=8)

    def test_removed_folder_returns_an_error(self):
        b=server.Board();b.snapshot={'workspaces':[{'path':'/missing/workboard-test-9823'}]}
        self.assertIn('error',b.reveal_workspace('/missing/workboard-test-9823'))

class TaskGitHubTests(unittest.TestCase):
    def board(self):
        b=server.Board();b.snapshot={'repositories':[{'id':'r','remote':'https://github.com/a/b'}]}
        b.documents={'one':{'id':'one','projectId':'r','kind':'tasks','relative':'TASKS.md','blob':'blob-one','sources':[{'commit':'abc','committedBlob':'blob-one'}]},'two':{'id':'two','projectId':'r','kind':'tasks','relative':'TASKS.md','blob':'uncommitted-content','sources':[{'commit':'abc','committedBlob':'blob-one'}]}}
        return b

    def test_only_exact_content_matches_default_branch(self):
        b=self.board()
        def run(args,**kw):
            endpoint=args[2]
            if endpoint=='repos/a/b':return ('{"default_branch":"main"}',None)
            if endpoint.endswith('/commits/main'):return ('tip',None)
            if '/git/trees/' in endpoint:return ('{"tree":[{"type":"blob","path":"TASKS.md","sha":"blob-one"}]}',None)
            return ('abc',None)
        with patch.object(server,'run',side_effect=run):r=b.task_github_status('r')
        self.assertEqual(r['versions']['one']['state'],'default')
        self.assertEqual(r['versions']['two']['state'],'unverified')

    def test_historical_commit_is_not_called_current_on_main(self):
        b=self.board()
        def run(args,**kw):
            endpoint=args[2]
            if endpoint=='repos/a/b':return ('{"default_branch":"main"}',None)
            if endpoint.endswith('/commits/main'):return ('tip',None)
            if '/git/trees/' in endpoint:return ('{"tree":[]}',None)
            return ('abc',None)
        with patch.object(server,'run',side_effect=run):r=b.task_github_status('r')
        self.assertEqual(r['versions']['one']['state'],'commit')
        self.assertEqual(r['versions']['two']['state'],'unverified')

    def test_github_failure_stays_unknown(self):
        with patch.object(server,'run',return_value=(None,'offline')):
            result=self.board().task_github_status('r')
        self.assertTrue(result['error']);self.assertEqual(result['versions'],{})

    def test_missing_origin_is_explicit(self):
        b=self.board();b.snapshot['repositories'][0]['remote']=None
        with patch.object(server,'run') as run:
            result=b.task_github_status('r');run.assert_not_called()
        self.assertIn('No GitHub origin',result['error'])

if __name__=='__main__':unittest.main()
