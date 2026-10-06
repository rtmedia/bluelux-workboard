from pathlib import Path
import tempfile
import unittest
import roadmaps


class ParserTests(unittest.TestCase):
    def test_explicit_status_owns_checklist_and_completion_text_does_not_override(self):
        text = '## AUTH9 — Recover sign in\n- **Status**: IN_PROGRESS\n- [x] Deploy\n- [ ] Verify device\n- Release is DONE, device pending\n'
        tasks = roadmaps.parse_tasks(text)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['status'], 'active')
        self.assertEqual([c['done'] for c in tasks[0]['checks']], [True, False])

    def test_table_link_and_detailed_item_deduplicate(self):
        text = '## Summary\n| Work | Status |\n|---|---|\n| [SAMPLE3](#sample3) | TODO |\n## SAMPLE3 — Migration\n- **Status**: IN_PROGRESS\n- [ ] Verify source\n'
        tasks = roadmaps.parse_tasks(text)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['key'], 'SAMPLE3')
        self.assertEqual(tasks[0]['status'], 'active')

    def test_leading_table_status_not_later_done(self):
        tasks = roadmaps.parse_tasks('## Milestones\n| Milestone | Status |\n|---|---|\n| COMMS-2 — Routing | IN_PROGRESS — bounded repair DONE |\n')
        self.assertEqual(tasks[0]['status'], 'active')

    def test_archived_sections_and_code_samples_are_not_open_tasks(self):
        text = '## Archived Completed Work\n### OLD1 — Old\n- **Status**: TODO\n- [ ] Old\n## Active\n```md\n## FAKE1\n- [ ] sample\n```\n- [ ] Real next step\n'
        tasks = roadmaps.parse_tasks(text)
        self.assertEqual([t['title'] for t in tasks], ['Real next step'])

    def test_standalone_checklists_and_wrapped_text(self):
        text = '## Release\n- [x] Ship\n## Next\n- [ ] Define freshness\n  and confidence.\n\n- [ ] **P0-1 · Failure**\n  Longer detail here.\n'
        tasks = roadmaps.parse_tasks(text)
        self.assertEqual([t['status'] for t in tasks], ['done','next','next'])
        self.assertEqual(tasks[1]['title'], 'Define freshness and confidence.')
        self.assertEqual(tasks[2]['title'], 'P0-1 · Failure')

    def test_unrecognized_status_is_not_invented(self):
        self.assertIsNone(roadmaps.status('Maybe complete later'))
        self.assertEqual(roadmaps.status('DEFERRED — waiting'), 'deferred')


class DiscoveryTests(unittest.TestCase):
    def test_only_relevant_bounded_paths(self):
        self.assertTrue(roadmaps.candidate('tasks.md'))
        for path in ['AGENTS.md','DESIGN.md','tasks/lessons.md','docs/README.md','frontend/package.json','vite.config.ts','.github/workflows/test.yml']:
            self.assertTrue(roadmaps.candidate(path),path)
        self.assertTrue(roadmaps.candidate('docs/audits/REPAIR_PLAN.md'))
        for path in ['work/old/TASKS.md','node_modules/a/plan.md','archive/roadmap.md','auth.json','.env.example','docs/credentials.md','private-key.pem']:
            self.assertFalse(roadmaps.candidate(path), path)

    def test_symlink_and_traversal_cannot_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)/'repo';base.mkdir()
            external=Path(tmp)/'plan.md';external.write_text('outside')
            (base/'plan.md').symlink_to(external)
            self.assertIsNone(roadmaps.read_safe(base,'plan.md'))
            self.assertIsNone(roadmaps.read_safe(base,'../plan.md'))

    def test_cache_reuses_unchanged_files_and_invalidates_repo_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, 'AGENTS.md').write_text('# Instructions\nRead as project context.')
            calls=[]
            def git(root,*args):
                calls.append(args)
                return ('AGENTS.md\0',None) if args[0]=='ls-files' else ('',None)
            w={'path':tmp,'repoId':'local','branch':'main','label':'Primary checkout','files':[]}
            p={'id':'local','name':'workboard','remote':None}
            first=roadmaps.collect([p],[w],git)[2]
            calls.clear()
            self.assertEqual(roadmaps.collect([p],[w],git)[2],first)
            self.assertEqual(len(calls),1)
            w['repoId']='github';p['id']='github'
            changed=roadmaps.collect([p],[w],git)[2]
            self.assertNotEqual(set(first),set(changed))
            self.assertEqual(next(iter(changed.values()))['projectId'],'github')

    def test_identical_copies_collapse_and_newest_commit_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for folder,content in [('one','## Item\n- [ ] Next'),('two','## Item\n- [ ] Next'),('three','## Item\n- [x] Next')]:
                p=Path(tmp)/folder;p.mkdir();(p/'tasks.md').write_text(content);paths.append(str(p))
            def git(root,*args):
                return ('tasks.md\0',None) if args[0]=='ls-files' else ('200' if root==paths[2] else '100',None)
            ws=[{'path':p,'repoId':'r','branch':str(i),'label':str(i),'files':[]} for i,p in enumerate(paths)]
            projects=[{'id':'r','name':'example-project','remote':'https://github.com/a/example-project'}]
            maps,summaries,docs=roadmaps.collect(projects,ws,git)
            self.assertTrue(projects[0]['core'])
            self.assertEqual(len(docs),2)
            self.assertEqual(maps[0]['tasks'][0]['status'],'done')
            self.assertEqual(sorted(len(d['sources']) for d in docs.values()),[1,2])

if __name__=='__main__':unittest.main()
