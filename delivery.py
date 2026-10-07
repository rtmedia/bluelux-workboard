"""Read-only delivery and cleanup evidence. No fetch, checkout, merge or deletion."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import logging
import re
import threading
import time
from urllib.parse import quote

NOW = lambda: datetime.now(timezone.utc).isoformat()
TTL = 300


def commit_refs(text):
    refs = []
    # Only explicit commit links / labelled hashes, never arbitrary prose numbers.
    for match in re.finditer(r'https://github\.com/([\w.-]+/[\w.-]+)/commit/([0-9a-f]{7,40})\b', text):
        refs.append({'sha': match[2], 'repo': match[1]})
    for match in re.finditer(r'\b(?:commit(?:ted)?(?:\s+as)?|sha)\s*[:=]?\s*[`\[]?([0-9a-f]{7,40})\b', text, re.I):
        if not any(r['sha'] == match[1] for r in refs):
            refs.append({'sha': match[1], 'repo': None})
    return refs[:12]


class Monitor:
    def __init__(self, run, git):
        self.run, self.git = run, git
        self.lock = threading.Lock()
        self.refreshing = False
        self.data = {'repositories': [], 'checkedAt': None}
        self.cache = {}
        self.proofs = {}
        self.error = None
        self.deadline = threading.local()

    def state(self):
        return {**self.data, 'refreshing': self.refreshing, 'error': self.error}

    def refresh(self, snapshot, force=False):
        if not snapshot:
            return
        with self.lock:
            if self.refreshing:
                return
            self.refreshing = True
        threading.Thread(target=self._refresh, args=(snapshot, force), daemon=True).start()

    def _refresh(self, snapshot, force):
        try:
            core = {p['id'] for p in snapshot['projects'] if p.get('core')}
            repos = [r for r in snapshot['repositories'] if r['id'] in core]
            results = {r['repoId']:r for r in self.data['repositories'] if r['repoId'] in core}
            with ThreadPoolExecutor(max_workers=3) as pool:
                pending = {pool.submit(self.inspect,r,snapshot,force):r for r in repos}
                for future in as_completed(pending):
                    result=future.result()
                    results[result['repoId']]=result
                    self.data = {'repositories': list(results.values()), 'checkedAt': NOW()}
            self.error = None
        except Exception:
            logging.getLogger('workboard').exception('Delivery scan failed')
            self.error = 'Delivery checks are unavailable. Previous evidence is retained with its original timestamps.'
        finally:
            self.refreshing = False

    def api(self, slug, path):
        if time.monotonic()>getattr(self.deadline,'until',float('inf')): return None
        raw, error = self.run(['gh', 'api', 'repos/' + slug + path], timeout=15)
        if error or raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    def remote(self, repo, force):
        slug = repo['remote'].removeprefix('https://github.com/')
        cached = self.cache.get(slug)
        if cached and not force and time.time() - cached['_at'] < TTL:
            return cached
        metadata = self.api(slug, '')
        branch = (metadata or {}).get('default_branch')
        result = {'_at': time.time(), 'checkedAt': NOW(), 'branch': branch, 'sha': None,
                  'prs': [], 'branches': [], 'error': None, 'limits': []}
        if not branch:
            result['error'] = 'GitHub unavailable; current main and remote branches are unknown.'
        else:
            commands = ['/commits/' + quote(branch, safe=''),
                        '/branches?per_page=100', '/pulls?state=all&sort=updated&direction=desc&per_page=100']
            with ThreadPoolExecutor(max_workers=3) as pool:
                commit, branches, prs = list(pool.map(lambda path: self.api(slug, path), commands))
            result.update(sha=(commit or {}).get('sha'), branches=branches if isinstance(branches,list) else None,
                          prs=prs if isinstance(prs,list) else [])
            if not result['sha'] or branches is None or prs is None:
                result['error'] = 'Some GitHub evidence is unavailable; missing results stay unknown.'
            if isinstance(branches,list) and len(branches) >= 100:
                result['limits'].append('Remote branch inventory limited to the first 100.')
            if isinstance(prs,list) and len(prs) >= 100:
                result['limits'].append('PR inventory limited to the latest 100; explicitly cited PRs are also checked (up to 20 extra).')
        result['deployment'] = {'state': 'unknown', 'label': 'Render deployment not reported through GitHub'}
        if result['sha']:
            with ThreadPoolExecutor(max_workers=2) as pool:
                checks, statuses = list(pool.map(lambda path: self.api(slug,path), [
                    '/commits/'+result['sha']+'/check-runs?per_page=100', '/commits/'+result['sha']+'/status']))
            render = [c for c in (checks or {}).get('check_runs',[]) if 'render' in (c.get('name','')+' '+c.get('app',{}).get('slug','')).lower()]
            render += [c for c in (statuses or {}).get('statuses',[]) if 'render' in c.get('context','').lower()]
            if render:
                failed=any(c.get('conclusion') in ('failure','timed_out','cancelled','action_required') or c.get('state') in ('failure','error') for c in render)
                pending=any(c.get('status') in ('queued','in_progress') or c.get('state')=='pending' for c in render)
                succeeded=all(c.get('conclusion')=='success' or c.get('state')=='success' for c in render)
                result['deployment']={'state':'failed' if failed else 'pending' if pending else 'success' if succeeded else 'unknown',
                    'label':'Render check failed' if failed else 'Render deployment pending' if pending else 'Render check passed' if succeeded else 'Render deployment outcome unknown'}
        self.cache[slug] = result
        return result

    def contains(self, repo, ancestor, tip):
        if not ancestor or not tip:
            return 'unknown'
        if ancestor == tip:
            return 'included'
        key = (repo['id'], ancestor, tip)
        if key in self.proofs and self.proofs[key] != 'unknown':
            return self.proofs[key]
        # Compare immutable objects already present locally; do not fetch or update refs.
        common, error = self.git(repo['root'], 'merge-base', ancestor, tip)
        if not error and common:
            state = 'included' if common.strip() == ancestor else 'outside'
        else:
            slug = repo['remote'].removeprefix('https://github.com/')
            response = self.api(slug, '/compare/' + quote(ancestor, safe='') + '...' + quote(tip, safe=''))
            status = (response or {}).get('status')
            state = 'included' if status in ('ahead','identical') else 'outside' if status in ('behind','diverged') else 'unknown'
        self.proofs[key] = state
        if len(self.proofs) > 4000:
            self.proofs = {key: state}
        return state

    def inspect(self, repo, snapshot, force=False):
        self.deadline.until=time.monotonic()+90
        rid = repo['id']
        workspaces = [w for w in snapshot['workspaces'] if w['repoId'] == rid]
        threads = [t for t in snapshot['threads'] if rid in t['projectIds'] and not t['archived']]
        out = {'repoId': rid, 'remote': repo.get('remote'), 'defaultBranch': None, 'defaultCommit': None,
               'checkedAt': NOW(), 'units': [], 'pullRequests': {}, 'commits': {}, 'error': None,
               'limits': [], 'deployment': {'state':'unknown','label':'Render deployment not checked'}, 'stashes': len(repo.get('stashes', []))}
        remote = self.remote(repo,force) if repo.get('remote') else {'branch':None,'sha':None,'branches':None,'prs':[], 'error':'No GitHub origin configured.', 'limits':[], 'checkedAt':NOW()}
        out['deployment'] = remote.get('deployment',out['deployment'])
        out.update(defaultBranch=remote['branch'], defaultCommit=remote['sha'], checkedAt=remote['checkedAt'], error=remote['error'], limits=list(remote['limits']))
        slug = (repo.get('remote') or '').removeprefix('https://github.com/')
        prs = {str(p['number']): p for p in remote['prs']}
        wanted = list(dict.fromkeys(url.rsplit('/',1)[-1] for t in threads for url in t.get('prs',[]) if url.startswith((repo.get('remote') or 'NO_REMOTE')+'/pull/')))
        missing = [n for n in wanted if n not in prs]
        if len(missing)>20:
            out['limits'].append('More than 20 older referenced PRs: additional references remain unverified.')
        # Cache explicit historical PRs along with the current remote inventory.
        extras = remote.setdefault('extraPRs', {})
        for number in missing[:20]:
            if number not in extras:
                extras[number] = self.api(slug,'/pulls/'+number)
            if extras[number]: prs[number] = extras[number]
        head_checks=remote.setdefault('headPRs',{})
        def landed(sha):
            state = self.contains(repo,sha,remote['sha']) if repo.get('remote') else 'unknown'
            if state == 'included': return state, None
            if sha and repo.get('remote') and remote['sha'] and not any(p.get('head',{}).get('sha')==sha for p in prs.values()):
                if sha not in head_checks and len(head_checks)<100:
                    head_checks[sha] = self.api(slug,'/commits/'+sha+'/pulls?per_page=20')
                for p in head_checks.get(sha) or []:
                    prs[str(p['number'])]=p
            # Squash/rebase landing: require exact PR head and a merge commit on current main.
            for p in prs.values():
                if p.get('merged_at') and p.get('base',{}).get('ref') == remote['branch'] and p.get('head',{}).get('sha') == sha and self.contains(repo,p.get('merge_commit_sha'),remote['sha']) == 'included':
                    return 'included', p.get('html_url')
            return state, None
        for number,p in prs.items():
            if number not in wanted: continue
            merged = bool(p.get('merged_at'))
            state = 'included' if merged and p.get('base',{}).get('ref') == remote['branch'] and self.contains(repo,p.get('merge_commit_sha'),remote['sha']) == 'included' else 'open' if p.get('state') == 'open' else 'closed' if not merged else 'unknown'
            out['pullRequests'][p['html_url']] = {'state':state,'branch':p.get('head',{}).get('ref'), 'sha':p.get('head',{}).get('sha'), 'mergedAt':p.get('merged_at'), 'title':p.get('title'), 'url':p['html_url']}
        refs = list(dict.fromkeys(r['sha'] for t in threads for r in t.get('commits',[]) if not r.get('repo') or r['repo']==slug))
        if len(refs)>60: out['limits'].append('Commit verification limited to 60 explicitly cited hashes per repository.')
        for ref in refs[:60]:
            # Resolve abbreviations in this exact repository first.
            value, error = self.git(repo['root'],'rev-parse','--verify',ref+'^{commit}')
            sha = value.strip() if not error and value else None
            if not sha and repo.get('remote'):
                value = self.api(slug,'/commits/'+ref)
                sha = (value or {}).get('sha')
            state,_ = landed(sha)
            out['commits'][ref] = {'state':state,'sha':sha}
        branches = {}
        for b in repo.get('branches', []):
            entry=branches.setdefault(b['name'],{'locals':[]})
            entry['local']=b
            entry['locals'].append(b)
        for b in remote['branches'] or []:
            branches.setdefault(b['name'],{})['remote'] = b
        for name,versions in branches.items():
            local, online = versions.get('local'), versions.get('remote')
            sha = (local or {}).get('sha') or (online or {}).get('commit',{}).get('sha')
            status,pr = landed(sha)
            linked = [w for w in workspaces if w['branch'] == name]
            protected = name == remote['branch'] or name in ('main','master') or bool((online or {}).get('protected'))
            remote_known = remote['branches'] is not None and len(remote['branches']) < 100
            published = self.contains(repo,sha,online['commit']['sha']) if online else 'absent' if remote_known else 'unknown'
            remote_state = landed(online['commit']['sha'])[0] if online else 'unknown'
            extra_heads={b.get('sha') for b in versions.get('locals',[]) if b.get('sha') and b.get('sha')!=sha}
            extra_heads.update(w.get('head') for w in linked if w.get('head') and w.get('head')!=sha)
            unique_local=any(landed(head)[0]!='included' for head in extra_heads)
            remote_unique = bool(online and remote_state != 'included' and online['commit']['sha'] != sha)
            blockers=[]
            if unique_local: blockers.append('Another local checkout/branch with this name has additional or unverified commits; retain its work.')
            if remote_unique: blockers.append('Remote branch contains additional or unverified work; retain it.')
            if local and not protected and any(w.get('primary',False) for w in linked): blockers.append('Branch is checked out in the primary workspace; retain that workspace and review before switching branches.')
            for w in linked:
                if w.get('error'): blockers.append('Workspace inspection unavailable: '+w['path'])
                if w.get('fileCount'): blockers.append(str(w['fileCount'])+' changed/untracked entries: '+w['path'])
                if w.get('ignoredCount') is None: blockers.append('Ignored-file inspection unavailable: '+w['path'])
                if w.get('ignoredCount'): blockers.append(str(w['ignoredCount'])+' ignored entries require inspection: '+w['path'])
                if w.get('locked'): blockers.append('Locked worktree: '+w['path'])
            dirty=any(w.get('error') or w.get('fileCount') for w in linked)
            # Main/primary workspaces are retained. Only non-primary extra worktrees are candidates.
            candidates=[w['path'] for w in linked if not w.get('primary',w.get('label')=='Primary checkout') and landed(w.get('head'))[0]=='included']
            cleanup = status == 'included' and (not protected or bool(candidates))
            pending = dirty or remote_unique or unique_local or (bool(local) and not repo.get('remote')) or status == 'outside' or (local is not None and published == 'absent' and status != 'included')
            if protected and not dirty and not candidates and status == 'included' and not remote_unique and not unique_local: continue
            out['units'].append({'id':rid+':'+name,'branch':name,'sha':sha,'state':status,'pr':pr,
                'local':bool(local),'remoteState':remote_state,'localCleanup':bool(local) and status=='included' and not protected and not unique_local,'remoteCleanup':bool(online) and remote_state=='included' and not protected,'remoteExists':True if online else False if remote_known else None,
                'published':published,'protected':protected,'cleanup':cleanup,'pending':pending,
                'paths':[w['path'] for w in linked], 'worktreeCandidates':candidates,'blockers':blockers,
                'primaryRetained':any(w.get('primary',w.get('label')=='Primary checkout') for w in linked),
                'openPRs':[p['html_url'] for p in prs.values() if p.get('state')=='open' and p.get('head',{}).get('ref')==name]})
        for w in workspaces:
            if w['branch']!='Detached HEAD':continue
            status,pr=landed(w.get('head'))
            blockers=[]
            if w.get('error'):blockers.append('Workspace inspection unavailable.')
            if w.get('fileCount'):blockers.append(str(w['fileCount'])+' changed/untracked entries must be preserved.')
            if w.get('ignoredCount'):blockers.append(str(w['ignoredCount'])+' ignored entries require inspection.')
            if w.get('locked'):blockers.append('Locked worktree.')
            primary=w.get('primary',False)
            out['units'].append({'id':rid+':'+w['path'],'branch':'Detached HEAD','sha':w.get('head'),'state':status,'pr':pr,'local':True,'remoteExists':None,'published':'unknown','protected':True,'cleanup':status=='included' and not primary,'pending':bool(w.get('fileCount')) or status=='outside','paths':[w['path']],'worktreeCandidates':[] if primary else [w['path']],'blockers':blockers,'primaryRetained':primary,'openPRs':[]})
        represented = {path for unit in out['units'] for path in unit['paths']}
        for w in workspaces:
            if w['path'] in represented or w['branch']=='Detached HEAD' or not (w.get('fileCount') or w.get('error')): continue
            out['units'].append({'id':rid+':'+w['path'],'branch':w['branch']+' · workspace changes','sha':w.get('head'),'state':'unknown','pr':None,'local':True,'remoteExists':None,'published':'unknown','protected':True,'cleanup':False,'pending':True,'paths':[w['path']],'worktreeCandidates':[],'blockers':['Uncommitted/untracked work or an unreadable checkout must be preserved.'],'primaryRetained':w.get('primary',False),'openPRs':[]})
        if time.monotonic()>self.deadline.until: out['limits'].append('The 90-second verification budget was reached; remaining proofs stay unknown. Check again to continue.')
        out['localCheckedAt'] = snapshot.get('checkedAt')
        return out
