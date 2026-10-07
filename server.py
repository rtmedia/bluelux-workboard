#!/usr/bin/env python3
"""Workboard: local, read-only Codex / Git / GitHub inventory. No third-party packages."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import threading
import time
from urllib.parse import unquote, urlsplit, parse_qs
import webbrowser
import sys
import roadmaps
import reliability
import triage
import logging

ROOT = Path(__file__).resolve().parent
STARTED = time.monotonic()
LOGGER = logging.getLogger('workboard')
CODEX_HOME = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
MAX_TAIL = 1024 * 1024
NOW = lambda: datetime.now(timezone.utc).isoformat()
ENV = {**os.environ, 'GIT_OPTIONAL_LOCKS': '0', 'GIT_TERMINAL_PROMPT': '0', 'GH_PROMPT_DISABLED': '1'}


def run(args, cwd=None, timeout=12):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           errors='replace', timeout=timeout, env=ENV)
        if p.returncode:
            return None, (p.stderr.strip() or 'Command unavailable')[:260]
        return p.stdout, None
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)[:260]


def git(path, *args):
    return run(['git', '-C', str(path), *args])


def plain(text, limit=6000):
    text = str(text or '')
    # Keep user-visible prose only; never render raw markup or execute embedded links.
    text = re.sub(r'<[^>]{1,200}>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\n]+?\)', r'\1', text)
    text = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})\b', '[redacted]', text)
    return text.strip()[:limit]


def request_text(text):
    if '<send_user_message_question_reply>' in text:
        try:
            raw = text.split('<send_user_message_question_reply>', 1)[1].split('</send_user_message_question_reply>', 1)[0]
            answers = json.loads(raw)
            return plain('\n\n'.join(str(a.get('question', '')) + '\n' + str(a.get('answer', '')) for a in answers))
        except (ValueError, TypeError, AttributeError):
            pass
    if '## My request:' in text:
        text = text.rsplit('## My request:', 1)[1]
    return plain(text)


def local_path(value):
    if not isinstance(value, str):
        return None
    if value.startswith('file://'):
        value = unquote(urlsplit(value).path)
    return value if value.startswith('/') else None


def parse_events(lines):
    """Read only public message/event types, never reasoning or command output."""
    out = {'request': '', 'response': '', 'workdirs': [], 'turnState': 'unknown',
           'lastEventAt': None, 'lastMessageAt': None, 'requestAt': None, 'responseAt': None, 'prs': []}
    for line in lines:
        try:
            d = json.loads(line)
        except (ValueError, TypeError):
            continue
        p = d.get('payload', {})
        if not isinstance(p, dict):
            continue
        typ = p.get('type')
        kind = d.get('type')
        stamp = d.get('timestamp')
        if kind == 'event_msg':
            if typ == 'user_message':
                out['request'] = request_text(p.get('message', ''))
                out['lastMessageAt'] = stamp
                out['requestAt'] = stamp
            elif typ in ('task_started', 'task_complete', 'turn_aborted'):
                out['turnState'] = {'task_started': 'started', 'task_complete': 'finished', 'turn_aborted': 'interrupted'}[typ]
                out['lastEventAt'] = stamp
                if typ == 'task_complete' and p.get('last_agent_message'):
                    out['response'] = plain(p['last_agent_message'])
                    out['lastMessageAt'] = stamp
                    out['responseAt'] = stamp
                    out['prs'] = list(dict.fromkeys(re.findall(r'https://github\.com/[\w.-]+/[\w.-]+/pull/\d+', p['last_agent_message'])))
            elif typ == 'item_completed':
                item = p.get('item', {})
                if isinstance(item, dict) and item.get('type') in ('CommandExecution', 'commandExecution'):
                    cwd = local_path(item.get('cwd'))
                    if cwd:
                        if cwd in out['workdirs']:
                            out['workdirs'].remove(cwd)
                        out['workdirs'].append(cwd)
        elif kind == 'response_item' and typ == 'message':
            role = p.get('role')
            content = '\n'.join(c.get('text', '') for c in p.get('content', []) if isinstance(c, dict))
            if role == 'user' and not content.startswith(('# AGENTS.md instructions', '<environment_context>')):
                out['request'] = request_text(content)
                out['lastMessageAt'] = stamp
                out['requestAt'] = stamp
            elif role == 'assistant' and p.get('phase') in ('final_answer', 'final'):
                out['response'] = plain(content)
                out['lastMessageAt'] = stamp
                out['responseAt'] = stamp
                out['prs'] = list(dict.fromkeys(re.findall(r'https://github\.com/[\w.-]+/[\w.-]+/pull/\d+', content)))
    out['workdirs'] = out['workdirs'][-12:]
    return out


class CodexReader:
    def __init__(self, home=CODEX_HOME):
        self.home = Path(home)
        self.cache = {}

    def index(self):
        dbs = sorted(self.home.glob('state_*.sqlite'), key=lambda p: int(re.search(r'(\d+)\.sqlite$', p.name)[1]), reverse=True)
        if not dbs:
            raise RuntimeError('No local Codex index found. Open Codex on this Mac, then refresh.')
        with sqlite3.connect(dbs[0].as_uri() + '?mode=ro', uri=True, timeout=3) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA query_only=ON')
            columns = {r['name'] for r in conn.execute('PRAGMA table_info(threads)')}
            required = {'id', 'cwd', 'title', 'rollout_path', 'updated_at', 'source', 'archived'}
            if not required <= columns:
                raise RuntimeError('Codex index format changed. This adapter needs an update; no source files were changed.')
            rows = [dict(r) for r in conn.execute('SELECT * FROM threads ORDER BY updated_at DESC')
                    if r['source'] in ('cli', 'vscode', 'appServer', 'exec', 'unknown')]
            projects = []
            try:
                projects = [dict(r) for r in conn.execute('SELECT p.id,p.name,r.path FROM projects p JOIN project_roots r ON p.id=r.project_id')]
            except sqlite3.DatabaseError:
                pass
        return rows, projects, dbs[0].name

    def context(self, row, deep=False):
        path = Path(row['rollout_path'])
        # Index references must stay inside Codex's local session directories.
        try:
            resolved = path.resolve()
            if not any(resolved.is_relative_to((self.home / d).resolve()) for d in ('sessions', 'archived_sessions')):
                raise ValueError('Conversation history is outside the supported local session folders.')
            stat = resolved.stat()
            budget = MAX_TAIL * (8 if deep else 1)
            key = (str(path), stat.st_mtime_ns, stat.st_size, budget)
            if key in self.cache:
                return dict(self.cache[key])
            with resolved.open('rb') as f:
                start = max(0, stat.st_size - budget)
                f.seek(start)
                if start:
                    f.readline()
                info = parse_events(f)
                # Long command outputs can push the latest discussion out of the first window.
                # Expand only when needed, and retain an explicit limit rather than reading a huge log.
                if not deep and start and (not info['request'] or not info['response']):
                    start = max(0, stat.st_size - 8 * MAX_TAIL)
                    f.seek(start)
                    if start:
                        f.readline()
                    info = parse_events(f)
            info['historyLimited'] = start > 0
            info['contextError'] = None
            if len(self.cache) > 1500:
                self.cache.clear()
            self.cache[key] = info
            return dict(info)
        except (OSError, ValueError) as exc:
            return {'request': '', 'response': '', 'workdirs': [], 'turnState': 'unknown',
                    'lastEventAt': None, 'lastMessageAt': None, 'prs': [], 'historyLimited': False,
                    'contextError': str(exc)[:160]}


def normalize_remote(remote):
    remote = remote.strip()
    m = re.fullmatch(r'(?:git@github\.com:|https://(?:[^/@]+@)?github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?', remote)
    return 'https://github.com/' + m[1] if m else None


def identify_repo(path):
    if not Path(path).is_dir():
        return None
    data, err = git(path, 'rev-parse', '--show-toplevel', '--git-common-dir')
    if err:
        return None
    lines = data.strip().splitlines()
    if len(lines) < 2:
        return None
    root = str(Path(lines[0]).resolve())
    common = str((Path(path) / lines[1]).resolve())
    remote, _ = git(root, 'remote', 'get-url', 'origin')
    remote = normalize_remote(remote or '')
    return {'root': root, 'common': common, 'remote': remote,
            'key': remote or common, 'id': hashlib.sha256((remote or common).encode()).hexdigest()[:16]}


def parse_status(raw):
    parts = raw.split('\0')
    files = []
    i = 0
    while i < len(parts):
        part = parts[i]
        i += 1
        if not part:
            continue
        code, path = part[:2], part[3:]
        files.append({'code': code, 'path': path})
        if 'R' in code or 'C' in code:
            i += 1
    return files


def linked_workspaces(paths, workspaces, identified):
    """Prefer actual Git roots over containing folders (nested worktrees are common)."""
    result = []
    known_paths = {w['path'] for w in workspaces}
    for path in paths:
        repo = identified.get(path)
        if repo:
            root = repo['root']
            if root in known_paths and root not in result:
                result.append(root)
            continue
        candidates = [w['path'] for w in workspaces if path == w['path'] or path.startswith(w['path'].rstrip('/') + '/')]
        if candidates:
            root = max(candidates, key=len)
            if root not in result:
                result.append(root)
    return result


def scan_checkout(w):
    path = w['path']
    raw, error = git(path, 'status', '--porcelain=v1', '-z', '--untracked-files=normal')
    files = parse_status(raw or '')
    branch, _ = git(path, 'symbolic-ref', '--short', '-q', 'HEAD')
    tip, _ = git(path, 'log', '-1', '--format=%h%x00%cs%x00%s')
    upstream, _ = git(path, 'rev-parse', '--abbrev-ref', '@{upstream}')
    counts = None
    if upstream:
        value, e = git(path, 'rev-list', '--left-right', '--count', '@{upstream}...HEAD')
        if not e:
            behind, ahead = map(int, value.split())
            counts = {'ahead': ahead, 'behind': behind}
    tracked = sum(f['code'] != '??' for f in files)
    untracked = sum(f['code'] == '??' for f in files)
    conflicts = sum(f['code'] in ('DD', 'AU', 'UD', 'UA', 'DU', 'AA', 'UU') for f in files)
    return {**w, 'branch': (branch or '').strip() or 'Detached HEAD', 'files': files[:150],
            'fileCount': len(files), 'tracked': tracked, 'untracked': untracked,
            'conflicts': conflicts, 'upstream': (upstream or '').strip() or None,
            'upstreamComparison': counts, 'tip': (tip or '').strip().split('\0'),
            'error': error, 'checkedAt': NOW(), 'chatIds': []}


def scan_repo(repo):
    raw, err = git(repo['root'], 'worktree', 'list', '--porcelain')
    checkouts = []
    for block in (raw or '').strip().split('\n\n'):
        fields = block.splitlines()
        if not fields or not fields[0].startswith('worktree '):
            continue
        path = fields[0][9:]
        label = Path(path).parent.name if '/worktrees/' in path else Path(path).name
        if not checkouts:
            label = 'Primary checkout'
        elif '/work/' in path:
            label = path.split('/work/', 1)[1]
        checkouts.append({'path': path, 'repoId': repo['id'], 'label': label,
                          'head': next((l[5:] for l in fields if l.startswith('HEAD ')), None)})
    stash, _ = git(repo['root'], 'stash', 'list', '--format=%gd%x09%cs%x09%gs')
    branches, _ = git(repo['root'], 'for-each-ref', '--format=%(refname:short)%09%(upstream:short)%09%(committerdate:short)', 'refs/heads')
    return {**repo, 'error': err, 'checkouts': checkouts,
            'stashes': [dict(zip(('name', 'date', 'subject'), line.split('\t', 2))) for line in (stash or '').splitlines()],
            'branches': [dict(zip(('name', 'upstream', 'date'), line.split('\t', 2))) for line in (branches or '').splitlines()]}


class Board:
    def __init__(self):
        self.reader = CodexReader()
        self.triage = triage.Store(ROOT / ".runtime" / "triage.json")
        self.lock = threading.Lock()
        self.snapshot = None
        self.refreshing = False
        self.error = None
        self.rows = {}
        self.github = {}
        self.documents = {}
        self.task_github = {}
        self.scan_started = None
        self.scan_duration = None

    def refresh(self):
        with self.lock:
            if self.refreshing:
                return
            self.refreshing = True
            self.scan_started = time.monotonic()
        threading.Thread(target=self._refresh, daemon=True).start()

    def _refresh(self):
        self.scan_started = time.monotonic()
        try:
            rows, saved, schema = self.reader.index()
            contexts = {}
            # Archived chats remain searchable; recent excerpts are loaded on demand for them.
            active = [r for r in rows if not r['archived']]
            with ThreadPoolExecutor(max_workers=8) as pool:
                for row, context in zip(active, pool.map(self.reader.context, active)):
                    contexts[row['id']] = context
            paths = {r['cwd'] for r in active if local_path(r['cwd'])}
            paths.add(str(ROOT))
            paths.update(p['path'] for p in saved if local_path(p['path']))
            for ctx in contexts.values():
                paths.update(ctx['workdirs'])
            with ThreadPoolExecutor(max_workers=8) as pool:
                identified = list(pool.map(identify_repo, sorted(paths)))
            by_path = {p: r for p, r in zip(sorted(paths), identified) if r}
            by_common = {}
            for r in by_path.values():
                by_common[r['common']] = r
            with ThreadPoolExecutor(max_workers=6) as pool:
                scanned = list(pool.map(scan_repo, by_common.values()))
            repos = {}
            for repo in scanned:
                if repo['id'] in repos:
                    existing = repos[repo['id']]
                    existing['checkouts'].extend(repo['checkouts'])
                    existing['stashes'].extend(repo['stashes'])
                    existing['branches'].extend(repo['branches'])
                else:
                    repo['name'] = (repo['remote'] or repo['root']).rstrip('/').split('/')[-1]
                    repos[repo['id']] = repo
            all_checkouts = {w['path']: w for r in repos.values() for w in r['checkouts']}
            with ThreadPoolExecutor(max_workers=8) as pool:
                workspaces = list(pool.map(scan_checkout, all_checkouts.values()))
            # A nested worktree belongs to its Git repo, not to its parent project's folder.
            def match_project(path):
                actual = by_path.get(path)
                if actual:
                    return actual['id']
                matches = [p for p in saved if path == p['path'] or path.startswith(p['path'].rstrip('/') + '/')]
                if matches:
                    match = max(matches, key=lambda p: len(p['path']))
                    known = by_path.get(match['path'])
                    return known['id'] if known else 'local:' + match['id']
                return 'other'
            projects = {r['id']: {'id': r['id'], 'name': r['name'], 'path': r['root'], 'remote': r['remote'], 'kind': 'git'} for r in repos.values()}
            for p in saved:
                k = match_project(p['path'])
                if k not in projects and k != 'other':
                    projects[k] = {'id': k, 'name': p['name'], 'path': p['path'], 'remote': None, 'kind': 'folder'}
                elif k in projects:
                    projects[k]['name'] = p['name']
            projects['other'] = {'id': 'other', 'name': 'Other conversations', 'path': None, 'remote': None, 'kind': 'chats'}
            threads = []
            for row in rows:
                ctx = contexts.get(row['id'], {})
                observed = ctx.get('workdirs', [])
                project_ids = list(dict.fromkeys([match_project(row['cwd'])] + [match_project(p) for p in observed]))
                if len(project_ids) > 1 and 'other' in project_ids:
                    project_ids.remove('other')
                title = row.get('name') or request_text(row.get('title', '')).split('\n')[0][:100] or 'Untitled chat'
                t = {'id': row['id'], 'title': title, 'cwd': row['cwd'], 'archived': bool(row['archived']),
                     'pinned': bool(row.get('is_pinned')), 'updatedAt': row['updated_at'], 'projectIds': project_ids,
                     'request': ctx.get('request') or request_text(row.get('first_user_message') or row.get('preview', '')),
                     'requestIsRecent': bool(ctx.get('request')), 'response': ctx.get('response', ''),
                     'turnState': ctx.get('turnState', 'unknown'), 'lastEventAt': ctx.get('lastEventAt'),
                     'lastMessageAt': ctx.get('lastMessageAt'), 'historyLimited': ctx.get('historyLimited', False),
                     'requestAt': ctx.get('requestAt'), 'responseAt': ctx.get('responseAt'),
                     'contextError': ctx.get('contextError'), 'observedPaths': observed, 'prs': ctx.get('prs', []),
                     'workspacePaths': [], 'link': 'codex://threads/' + row['id']}
                t['workspacePaths'] = linked_workspaces([row['cwd']] + observed, workspaces, by_path)
                for w in workspaces:
                    if w['path'] in t['workspacePaths'] and not t['archived']:
                        w['chatIds'].append(t['id'])
                threads.append(t)
            for repo in repos.values():
                repo.pop('checkouts', None)
            roadmap_data, document_summaries, documents = roadmaps.collect(list(projects.values()), workspaces, git)
            self.rows = {r['id']: r for r in rows}
            snapshot = {'checkedAt': NOW(), 'threads': threads, 'projects': list(projects.values()),
                        'repositories': list(repos.values()), 'workspaces': workspaces,
                        'roadmaps': roadmap_data, 'documents': document_summaries,
                        'source': {'codex': 'Local Codex index + recent saved conversation events', 'schema': schema,
                                   'mode': 'read-only compatibility adapter', 'cloudCoverage': False},
                        'coverage': {'chats': len(rows), 'archived': len(rows)-len(active), 'missingHistory': sum(bool(t['contextError']) for t in threads)},
                        'github': self.github, 'taskGitHub': self.task_github}
            with self.lock:
                self.documents = documents
                self.snapshot = snapshot
                self.error = None
        except Exception as exc:
            self.error = str(exc)[:300]
            LOGGER.error('Local inventory failed: %s', type(exc).__name__)
        finally:
            self.scan_duration = round(time.monotonic()-self.scan_started,2)
            self.refreshing = False

    def state(self):
        if not self.snapshot and not self.refreshing:
            self.refresh()
        try:
            choices, choice_error = self.triage.read(), None
        except (OSError, ValueError):
            choices, choice_error = {}, 'Saved Workboard choices are unavailable. They have not been overwritten.'
        return {'data': self.snapshot, 'refreshing': self.refreshing, 'error': self.error,
                'choices': choices, 'choiceError': choice_error}

    def detail(self, thread_id):
        row = self.rows.get(thread_id)
        if not row:
            return None
        context = self.reader.context(row, deep=True)
        return {**context, 'requestIsRecent': bool(context['request']),
                'request': context['request'] or request_text(row.get('first_user_message') or row.get('preview', ''))}

    def reveal_workspace(self, path):
        known = {w['path'] for w in (self.snapshot or {}).get('workspaces', [])}
        if not isinstance(path, str) or path not in known:
            return {'error': 'Choose an indexed workspace folder.'}
        if not Path(path).is_dir():
            return {'error': 'This workspace folder is no longer available.'}
        if sys.platform != 'darwin':
            return {'error': 'Finder reveal is available on macOS only.'}
        _, error = run(['/usr/bin/open', '-R', path], timeout=8)
        return {'error': 'Finder could not reveal this folder.'} if error else {'revealed': path}

    def task_github_status(self, repo_id):
        repo = next((r for r in (self.snapshot or {}).get('repositories', []) if r['id']==repo_id), None)
        docs = [d for d in self.documents.values() if d['projectId']==repo_id and d['kind']=='tasks']
        fingerprint = sorted(d['id'] for d in docs)
        cached = self.task_github.get(repo_id)
        if cached and cached.get('documentIds')==fingerprint and time.time()-cached.get('_at',0)<60:
            return cached
        result = {'checkedAt': NOW(), '_at': time.time(), 'documentIds':fingerprint, 'versions':{}}
        if not repo or not repo.get('remote'):
            result['error'] = 'No GitHub origin is configured for this repository.'
        elif not docs:
            result['error'] = 'No task file was found in the scanned checkouts.'
        else:
            slug = repo['remote'].removeprefix('https://github.com/')
            raw, error = run(['gh','api','repos/'+slug], timeout=15)
            if error:
                result['error'] = 'GitHub could not be reached with the current gh sign-in.'
            else:
                branch = json.loads(raw)['default_branch']
                # Pin the tree to a checked commit so links and comparisons describe one snapshot.
                from urllib.parse import quote
                raw, error = run(['gh','api','repos/'+slug+'/commits/'+quote(branch,safe=''), '--jq','.sha'], timeout=15)
                tip = (raw or '').strip()
                tree_raw, tree_error = run(['gh','api','repos/'+slug+'/git/trees/'+tip+'?recursive=1'], timeout=20) if tip else (None,error)
                tree = json.loads(tree_raw) if tree_raw else {}
                entries = {e['path']: e['sha'] for e in tree.get('tree',[]) if e['type']=='blob'}
                commits = sorted({s['commit'] for d in docs for s in d['sources'] if s.get('commit') and s.get('committedBlob')==d['blob']})
                def check_commit(sha):
                    raw, err = run(['gh','api','repos/'+slug+'/commits/'+sha,'--jq','.sha'],timeout=15)
                    return sha, (raw or '').strip()==sha, bool(err)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    checked = {sha:(present,failed) for sha,present,failed in pool.map(check_commit,commits[:40])}
                result.update(defaultBranch=branch, defaultCommit=tip, treeComplete=not tree_error and not tree.get('truncated',False))
                if tree_error:
                    result['warning'] = 'Default-branch content could not be checked; commit checks are shown separately.'
                elif tree.get('truncated'):
                    result['warning'] = 'GitHub returned a partial tree. Missing paths remain unknown.'
                for d in docs:
                    same = entries.get(d['relative'])==d['blob']
                    # Case differs between macOS and the repository index; only use an unambiguous match.
                    matching = [(p,sha) for p,sha in entries.items() if p.lower()==d['relative'].lower()]
                    if len(matching)==1:
                        same = matching[0][1]==d['blob']
                    present = [s['commit'] for s in d['sources'] if s.get('committedBlob')==d['blob'] and checked.get(s.get('commit'),(False,False))[0]]
                    state = 'default' if same else 'commit' if present else 'unverified'
                    result['versions'][d['id']] = {'state':state, 'commit':tip if same else present[0] if present else None,
                        'url': repo['remote']+'/blob/'+(tip if same else present[0])+'/'+quote(d['relative'],safe='/') if same or present else None}
        self.task_github[repo_id] = result
        return result

    def github_status(self, repo_id):
        repo = next((r for r in (self.snapshot or {}).get('repositories', []) if r['id'] == repo_id), None)
        if not repo or not repo['remote']:
            return {'error': 'This repository has no supported GitHub origin.', 'checkedAt': NOW()}
        cached = self.github.get(repo_id)
        if cached and time.time() - cached.get('_at', 0) < 60:
            return cached
        slug = repo['remote'].removeprefix('https://github.com/')
        raw, err = run(['gh', 'api', 'repos/' + slug], timeout=15)
        if err:
            result = {'error': 'GitHub unavailable. Check your connection and gh authentication.', 'checkedAt': NOW(), '_at': time.time()}
        else:
            metadata = json.loads(raw)
            branch = metadata['default_branch']
            commands = [
                ['gh', 'api', 'repos/' + slug + '/commits/' + branch],
                ['gh', 'pr', 'list', '--repo', slug, '--state', 'open', '--limit', '100', '--json', 'number,title,url,headRefName,isDraft,updatedAt'],
                ['gh', 'pr', 'list', '--repo', slug, '--state', 'merged', '--limit', '10', '--json', 'number,title,url,headRefName,mergedAt'],
            ]
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(lambda cmd: run(cmd, timeout=20), commands))
            parsed = [json.loads(raw) if raw is not None else None for raw, _ in results]
            errors = [e for _, e in results if e]
            commit, prs, merged = parsed
            result = {'checkedAt': NOW(), '_at': time.time(), 'defaultBranch': branch,
                      'defaultCommit': commit.get('sha') if commit else None,
                      'openPRs': prs, 'recentMerged': merged,
                      'error': 'Some GitHub details could not be loaded.' if errors else None}
        self.github[repo_id] = result
        return result


BOARD = Board()


class LocalServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        LOGGER.error('HTTP request failed', exc_info=True)



class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def send(self, code, body, mime='application/json'):
        if mime == 'application/json':
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith(('text/', 'application/json', 'application/javascript')) else ''))
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def allowed(self):
        host = self.headers.get('Host', '')
        expected = {'127.0.0.1:' + str(self.server.server_port), 'localhost:' + str(self.server.server_port)}
        if host not in expected:
            self.send(403, {'error': 'Local access only.'})
            return False
        origin = self.headers.get('Origin')
        if (origin and origin not in {'http://' + h for h in expected}) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.send(403, {'error': 'Cross-site requests are not accepted.'})
            return False
        return True

    def do_GET(self):
        if not self.allowed():
            return
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        if url.path == '/api/health':
            return self.send(200, reliability.health(BOARD, STARTED, ROOT))
        if url.path == '/api/ready':
            report = reliability.health(BOARD, STARTED, ROOT)
            return self.send(200 if report['status']=='ready' else 503, report)
        if url.path == '/api/documents/search':
            text = query.get('q',[''])[0][:200].strip().lower()
            scope = query.get('project',['all'])[0]
            category = query.get('category',['all'])[0]
            results=[]
            if len(text)>=2:
                for document in BOARD.documents.values():
                    if scope!='all' and document['projectId']!=scope: continue
                    if scope=='all' and not any(p['id']==document['projectId'] and p.get('core') for p in (BOARD.snapshot or {}).get('projects',[])): continue
                    if category!='all' and document.get('category')!=category: continue
                    position=document['content'].lower().find(text)
                    if position<0: continue
                    results.append({'id':document['id'],'projectId':document['projectId'],'title':document['title'],
                        'relative':document['relative'],'line':document['content'][:position].count('\n')+1,
                        'excerpt':document['content'][max(0,position-90):position+210]})
                    if len(results)>=60: break
            return self.send(200, {'results':results,'limited':len(results)>=60})
        if url.path == '/api/state':
            return self.send(200, BOARD.state())
        if url.path == '/api/thread':
            detail = BOARD.detail(query.get('id', [''])[0])
            return self.send(200 if detail else 404, detail or {'error': 'Chat not found in the local index.'})
        if url.path == '/api/document':
            document = BOARD.documents.get(query.get('id', [''])[0])
            return self.send(200 if document else 404, document or {'error': 'Document not found in this scan.'})
        if url.path == '/api/task-github':
            try:
                return self.send(200, BOARD.task_github_status(query.get('repo',[''])[0]))
            except Exception:
                return self.send(502, {'error': 'Task-file GitHub check unavailable.'})
        if url.path == '/api/github':
            try:
                return self.send(200, BOARD.github_status(query.get('repo', [''])[0]))
            except Exception:
                return self.send(502, {'error': 'GitHub details are unavailable. Local data is still available.'})
        assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'application/javascript'),
                  '/focus.js': ('focus.js', 'application/javascript'),
                  '/style.css': ('style.css', 'text/css'), '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
                  '/manifest.webmanifest': ('manifest.webmanifest', 'application/manifest+json'),
                  '/pwa.js': ('pwa.js', 'application/javascript'), '/sw.js': ('sw.js', 'application/javascript'),
                  '/offline.html': ('offline.html', 'text/html'), '/offline.css': ('offline.css', 'text/css'),
                  '/offline.js': ('offline.js', 'application/javascript'),
                  '/icon-192.png': ('icon-192.png', 'image/png'), '/icon-512.png': ('icon-512.png', 'image/png')}
        if url.path in assets:
            name, mime = assets[url.path]
            return self.send(200, (ROOT / 'static' / name).read_bytes(), mime)
        self.send(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.allowed():
            return
        if self.path == '/api/triage':
            if self.headers.get('X-Workboard-Action') != 'triage' or self.headers.get('Content-Type') != 'application/json':
                return self.send(403, {'error': 'Use the Workboard discussion controls.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 8192:
                    return self.send(400, {'error': 'Invalid request size.'})
                data = json.loads(self.rfile.read(length))
                thread = next((t for t in (BOARD.snapshot or {}).get('threads', []) if t['id'] == data.get('id')), None)
                if not thread:
                    return self.send(404, {'error': 'Refresh to load this discussion first.'})
                if data.get('requestToken') != triage.request_token(thread):
                    return self.send(409, {'error': 'This discussion changed. Refresh and review its latest request.'})
                items = BOARD.triage.update(thread, data.get('status'), data.get('note', ''))
                return self.send(200, {'choices': items})
            except (ValueError, AttributeError, TypeError):
                return self.send(400, {'error': 'Invalid choice or unreadable saved choices. No choices were overwritten.'})
            except OSError:
                return self.send(500, {'error': 'Could not save your choice. Try again; source projects are unchanged.'})
        if self.path == '/api/reveal':
            if self.headers.get('X-Workboard-Action')!='reveal' or self.headers.get('Content-Type')!='application/json':
                return self.send(403, {'error': 'Use the Workboard Finder button.'})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 16384:
                    return self.send(400, {'error': 'Invalid request size.'})
                data=json.loads(self.rfile.read(length))
                result=BOARD.reveal_workspace(data.get('path'))
                return self.send(400 if result.get('error') else 200,result)
            except (ValueError, AttributeError):
                return self.send(400, {'error': 'Invalid request.'})
        if self.path == '/api/refresh':
            BOARD.refresh()
            return self.send(202, {'refreshing': True})
        self.send(405, {'error': 'Workboard does not modify chats or repositories.'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=43127)
    parser.add_argument('--open', action='store_true')
    parser.add_argument('--check', action='store_true', help='Run one local inventory and print counts, without serving')
    args = parser.parse_args()
    if args.check:
        BOARD._refresh()
        if BOARD.error:
            raise SystemExit(BOARD.error)
        s = BOARD.snapshot
        print(json.dumps({'chats': len(s['threads']), 'projects': len(s['projects']), 'workspaces': len(s['workspaces']), 'coverage': s['coverage']}))
        return
    reliability.configure_logging(ROOT)
    (ROOT / '.runtime' / 'server.pid').write_text(str(os.getpid()))
    server = LocalServer(('127.0.0.1', args.port), Handler)
    BOARD.refresh()
    url = 'http://127.0.0.1:' + str(args.port)
    LOGGER.info('Workboard started on %s', url)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        LOGGER.info('Workboard stopped')
        server.server_close()


if __name__ == '__main__':
    main()
