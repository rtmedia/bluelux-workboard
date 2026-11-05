import unittest
from unittest.mock import Mock
import delivery

class DeliveryTests(unittest.TestCase):
    def setup_scan(self, sha='head', dirty=0, remote_head='head', protected=False):
        monitor=delivery.Monitor(Mock(return_value=(None,'offline')),Mock(return_value=(None,'unknown object')))
        repo={'id':'r','root':'/repo','remote':'https://github.com/a/b','branches':[{'name':'fix','sha':sha}], 'stashes':[]}
        workspace={'repoId':'r','path':'/worktree','branch':'fix','head':sha,'primary':False,'fileCount':dirty,'ignoredCount':0,'error':None}
        snapshot={'threads':[],'workspaces':[workspace]}
        remote={'branch':'main','sha':'main-sha','checkedAt':delivery.NOW(),'error':None,'limits':[], 'prs':[], 'branches':[{'name':'fix','commit':{'sha':remote_head},'protected':protected}]}
        monitor.remote=Mock(return_value=remote)
        return monitor,repo,snapshot,remote

    def test_uncited_open_pr_is_visible_without_claiming_delivery(self):
        m,r,s,remote=self.setup_scan()
        remote['prs']=[{'number':2,'state':'open','html_url':'https://github.com/a/b/pull/2','head':{'ref':'fix','sha':'head'},'title':'Uncited PR'}]
        m.contains=Mock(return_value='outside')
        out=m.inspect(r,s)
        self.assertEqual(out['pullRequests']['https://github.com/a/b/pull/2']['state'],'open')
        self.assertEqual(out['prInventory'][0]['state'],'open')

    def test_empty_or_missing_checks_never_mean_pass(self):
        m=delivery.Monitor(Mock(),Mock())
        def api(slug,path):
            if path=='':return {'default_branch':'main'}
            if path=='/commits/main':return {'sha':'head'}
            if path.endswith('/status'):return {'statuses':[]}
            if 'check-runs' in path:return {'check_runs':[],'total_count':0}
            return []
        m.api=api
        self.assertEqual(m.remote({'remote':'https://github.com/a/b'},True)['checks']['state'],'unknown')
        def failing(slug,path):
            return {'check_runs':[{'conclusion':'failure'}],'total_count':1} if 'check-runs' in path else api(slug,path)
        m.api=failing
        self.assertEqual(m.remote({'remote':'https://github.com/a/b'},True)['checks']['state'],'failed')

    def test_only_explicit_commit_identifiers_are_extracted(self):
        self.assertEqual(delivery.commit_refs('TASK abcdef0 and number 1234567'),[])
        self.assertEqual(delivery.commit_refs('Commit: `abcdef0`')[0]['sha'],'abcdef0')
        self.assertEqual(delivery.commit_refs('https://github.com/a/b/commit/abcdef0123')[0]['repo'],'a/b')

    def test_main_ancestry_makes_cleanup_candidate(self):
        m,r,s,_=self.setup_scan();m.contains=Mock(return_value='included')
        unit=m.inspect(r,s)['units'][0]
        self.assertTrue(unit['cleanup']);self.assertFalse(unit['pending'])
        self.assertEqual(unit['worktreeCandidates'],['/worktree'])

    def test_dirty_landed_checkout_is_completed_but_not_disposable(self):
        m,r,s,_=self.setup_scan(dirty=3);m.contains=Mock(return_value='included')
        unit=m.inspect(r,s)['units'][0]
        self.assertTrue(unit['cleanup']);self.assertTrue(unit['pending'])
        self.assertIn('3 changed/untracked',unit['blockers'][0])

    def test_pushed_feature_branch_is_not_completed(self):
        m,r,s,_=self.setup_scan();m.contains=Mock(side_effect=lambda r,a,b:'included' if a==b else 'outside')
        unit=m.inspect(r,s)['units'][0]
        self.assertFalse(unit['cleanup']);self.assertTrue(unit['pending'])
        self.assertEqual(unit['published'],'included')

    def test_squash_merge_requires_exact_head_and_merge_on_main(self):
        m,r,s,remote=self.setup_scan()
        remote['prs']=[{'number':1,'merged_at':'2026-01-01','state':'closed','base':{'ref':'main'},'head':{'sha':'head','ref':'fix'},'merge_commit_sha':'squash','html_url':'https://github.com/a/b/pull/1'}]
        m.contains=Mock(side_effect=lambda r,a,b:'included' if a=='squash' else 'outside')
        self.assertTrue(m.inspect(r,s)['units'][0]['cleanup'])
        r['branches'][0]['sha']='new-commit'
        self.assertFalse(m.inspect(r,s)['units'][0]['cleanup'])
        m.contains=Mock(return_value='outside')
        r['branches'][0]['sha']='head'
        self.assertFalse(m.inspect(r,s)['units'][0]['cleanup'])

    def test_older_squash_merge_can_be_found_by_commit(self):
        m,r,s,_=self.setup_scan()
        pr={'number':1,'merged_at':'2026-01-01','state':'closed','base':{'ref':'main'},'head':{'sha':'head','ref':'fix'},'merge_commit_sha':'squash','html_url':'https://github.com/a/b/pull/1'}
        m.api=Mock(return_value=[pr])
        m.contains=Mock(side_effect=lambda r,a,b:'included' if a=='squash' else 'outside')
        self.assertTrue(m.inspect(r,s)['units'][0]['cleanup'])

    def test_failed_remote_inventory_does_not_prove_remote_deleted(self):
        m,r,s,remote=self.setup_scan();remote.update(sha=None,branches=None,error='offline')
        m.contains=Mock(return_value='unknown')
        unit=m.inspect(r,s)['units'][0]
        self.assertIsNone(unit['remoteExists']);self.assertFalse(unit['cleanup'])

    def test_primary_and_protected_main_are_retained(self):
        m,r,s,remote=self.setup_scan();r['branches'][0]['name']='main';s['workspaces'][0].update(branch='main',primary=True)
        remote['branches']=[{'name':'main','commit':{'sha':'head'},'protected':True}]
        m.contains=Mock(return_value='included')
        self.assertEqual(m.inspect(r,s)['units'],[])

    def test_new_remote_commits_are_preserved_after_local_head_landed(self):
        m,r,s,_=self.setup_scan(remote_head='new-remote')
        m.contains=Mock(side_effect=lambda r,a,b:'outside' if a=='new-remote' else 'included')
        unit=m.inspect(r,s)['units'][0]
        self.assertTrue(unit['localCleanup']);self.assertFalse(unit['remoteCleanup'])
        self.assertTrue(unit['pending']);self.assertIn('retain it',unit['blockers'][0])

    def test_other_checkout_with_same_branch_and_new_commits_is_preserved(self):
        m,r,s,_=self.setup_scan();s['workspaces'].append({**s['workspaces'][0],'path':'/other','head':'new'})
        m.contains=Mock(side_effect=lambda r,a,b:'outside' if a=='new' else 'included')
        unit=m.inspect(r,s)['units'][0]
        self.assertTrue(unit['pending']);self.assertFalse(unit['localCleanup'])
        self.assertNotIn('/other',unit['worktreeCandidates'])

    def test_unborn_dirty_checkout_is_not_lost(self):
        m,r,s,remote=self.setup_scan(dirty=4);r['branches']=[];remote['branches']=[]
        unit=m.inspect(r,s)['units'][0]
        self.assertTrue(unit['pending']);self.assertFalse(unit['cleanup'])

    def test_ignored_files_and_lock_are_explicit_blockers(self):
        m,r,s,_=self.setup_scan();s['workspaces'][0].update(ignoredCount=2,locked=True)
        m.contains=Mock(return_value='included')
        blockers=m.inspect(r,s)['units'][0]['blockers']
        self.assertEqual(len(blockers),2)

    def test_pr_into_nondefault_branch_does_not_complete(self):
        m,r,s,remote=self.setup_scan()
        url='https://github.com/a/b/pull/1'
        s['threads']=[{'projectIds':['r'],'archived':False,'prs':[url],'commits':[]}]
        remote['prs']=[{'number':1,'merged_at':'2026-01-01','state':'closed','base':{'ref':'staging'},'head':{'sha':'head','ref':'fix'},'merge_commit_sha':'squash','html_url':url}]
        m.contains=Mock(return_value='included')
        self.assertEqual(m.inspect(r,s)['pullRequests'][url]['state'],'unknown')

    def test_compare_orientation_and_unknown_failure(self):
        m,r,_,_=self.setup_scan()
        m.api=Mock(return_value={'status':'ahead'})
        self.assertEqual(m.contains(r,'feature','main-tip'),'included')
        m.api.assert_called_with('a/b','/compare/feature...main-tip')
        m.api=Mock(return_value={'status':'behind'})
        self.assertEqual(m.contains(r,'newer','main-tip'),'outside')
        m.api=Mock(return_value=None)
        self.assertEqual(m.contains(r,'missing','main-tip'),'unknown')

if __name__=='__main__':unittest.main()
