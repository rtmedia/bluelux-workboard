"""Bounded, read-only Markdown roadmap adapter. Source text is data, never instructions."""
from pathlib import Path
import hashlib
import re

LIMIT = 2 * 1024 * 1024
FILE_CACHE = {}
SKIP = {'.git', 'node_modules', 'work', 'vendor', '.local', '.gstack', 'archive', 'archives', 'dist', 'build', 'qa-artifacts', 'attached_assets', 'coverage', 'logs', '.runtime', '.venv', 'venv', 'site-packages'}
CORE = {'example-project': 'Example Project', 'example-site': 'Example Site', 'example-service': 'Example Service', 'example_importer': 'Example Importer', 'example-device': 'Example Device', 'example_device': 'Example Device', 'bluelux-workboard':'Workboard', 'workboard':'Workboard'}


def clean(value):
    value = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', value)
    return re.sub(r'[*`]', '', value).strip()


def status(value):
    value = clean(value).upper().replace('IN PROGRESS', 'IN_PROGRESS')
    for key, words in [('active', ('INPROGRESS', 'IN_PROGRESS', 'IN-PROGRESS', 'IN_FLIGHT', 'INFLIGHT', 'IN FLIGHT')), ('blocked', ('BLOCKED',)), ('done', ('DONE', 'COMPLETE', 'COMPLETED', 'SHIPPED')), ('deferred', ('DEFERRED', 'PARKED', 'CANCELLED', 'CANCELED')), ('next', ('TODO', 'TO DO', 'NOT STARTED', 'PLANNED', 'PENDING'))]:
        if any(re.match(re.escape(w) + r'(?:\b|[—:–])', value) for w in words):
            return key
    return None


def task_key(title):
    match = re.match(r'([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*\d+[A-Z0-9-]*|SURFACE-[A-Z-]+)\b', clean(title))
    return match.group(1) if match else hashlib.sha256(clean(title).lower().encode()).hexdigest()[:14]


def parse_tasks(text):
    lines = text.splitlines()
    headings = []
    fenced = False
    ignored = set()
    for i, line in enumerate(lines):
        if re.match(r'^\s*(```|~~~)', line):
            fenced = not fenced
            ignored.add(i)
            continue
        if fenced:
            ignored.add(i)
            continue
        m = re.match(r'^(#{1,6})\s+(.+)', line)
        if m:
            headings.append({'start': i, 'level': len(m[1]), 'title': clean(m[2])})
    for n, h in enumerate(headings):
        h['end'] = next((x['start'] for x in headings[n+1:] if x['level'] <= h['level']), len(lines))
        h['directEnd'] = headings[n+1]['start'] if n+1 < len(headings) else len(lines)
        h['history'] = bool(re.search(r'archiv|historical|review report', h['title'], re.I)) or any(p['history'] and p['start'] < h['start'] < p['end'] for p in headings[:n])
        direct = '\n'.join(lines[i] for i in range(h['start']+1,h['directEnd']) if i not in ignored)
        m = re.search(r'^\s*(?:[-*]\s*)?(?:\*\*)?Status(?:\*\*)?\s*:\s*(.+)', direct, re.M | re.I)
        h['status'] = status(m[1]) if m else None
        h['statusText'] = clean(m[1]) if m else ''
    tasks = []
    def add(title, state, line, end, group, evidence, kind='task'):
        body = '\n'.join(lines[line:end])
        checks = [{'done': m[1].lower() == 'x', 'text': clean(m[2])} for m in re.finditer(r'^\s*[-*] \[([ xX])\]\s+(.+)', body, re.M)]
        key = task_key(title)
        if re.fullmatch(r'[0-9a-f]{14}', key):
            key = hashlib.sha256((group+'\0'+clean(title)).encode()).hexdigest()[:14]
        tasks.append({'key': key, 'title': clean(title), 'status': state, 'statusText': evidence,
                      'line': line+1, 'group': group, 'body': body[:14000], 'truncated': len(body)>14000,
                      'checks': checks[:80], 'kind': kind})
    for h in headings:
        if h['status'] and not h['history']:
            add(h['title'], h['status'], h['start'], h['end'], h['title'], h['statusText'])
    table = None
    for i, line in enumerate(lines):
        if i in ignored:
            continue
        parents = [h for h in headings if h['start'] < i < h['end']]
        h = parents[-1] if parents else None
        if any(p['history'] for p in parents):
            continue
        if line.startswith('|'):
            cells = [clean(x) for x in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
            status_col = next((j for j, c in enumerate(cells) if re.match(r'^status\b', c, re.I)), None)
            if status_col is not None:
                table = status_col
                continue
            if table is not None and len(cells) > table and status(cells[table]):
                title = cells[0]
                if len(cells)>2 and re.fullmatch(r'SURFACE-[A-Z-]+', title):
                    title += ' — ' + cells[2]
                add(title, status(cells[table]), i, i+1, h['title'] if h else '', cells[table], 'milestone')
            continue
        table = None
        # Explicit task sections own their acceptance criteria: don't count each as a separate task.
        if any(p['status'] for p in parents):
            continue
        check = re.match(r'^[-*] \[([ xX])\]\s+(.+)', line)
        if check:
            end = next((j for j in range(i+1, len(lines)) if re.match(r'^(?:#{1,6} |[-*] \[)', lines[j])), len(lines))
            title = check[2]
            for continuation in lines[i+1:end]:
                if not continuation.strip() or not continuation.startswith('  ') or re.match(r'^\s*[-*]', continuation):
                    break
                # Bold checklist labels name a task; their following prose is detail.
                if check[2].startswith('**') and check[2].count('**')>=2:
                    break
                title += ' ' + continuation.strip()
            add(title, 'done' if check[1].lower()=='x' else 'next', i, end, h['title'] if h else '', 'Checked' if check[1].lower()=='x' else 'Unchecked')
        elif h and re.match(r'^In progress\b', h['title'], re.I):
            bullet = re.match(r'^[-*] \*\*(.+?)\*\*', line)
            if bullet:
                add(bullet[1], 'active', i, i+1, h['title'], 'In progress section')
    # A task mentioned in a summary table and detailed section is one item.
    dedup = {}
    for task in tasks:
        previous = dedup.get(task['key'])
        if previous is None or len(task['body']) > len(previous['body']):
            dedup[task['key']] = task
    return sorted(dedup.values(), key=lambda t:t['line'])


CONFIG_NAMES = {'.gitignore','.gitattributes','.editorconfig','.dockerignore','.nvmrc','package.json','pyproject.toml','requirements.txt','dockerfile','makefile','procfile','render.yaml','render.yml','wrangler.toml','wrangler.json','wrangler.jsonc','components.json','manifest.json','compose.yml','compose.yaml','docker-compose.yml','docker-compose.yaml'}


def category(relative):
    p=Path(relative); name=p.name.lower()
    if name in ('tasks.md','todos.md'): return 'tasks'
    if name in ('agents.md','claude.md','gemini.md','copilot-instructions.md') or 'playbook' in name: return 'instructions'
    if any(w in name for w in ('design','architecture','guideline')): return 'design'
    if any(w in name for w in ('plan','roadmap','checkpoint')): return 'plans'
    if p.suffix.lower() not in ('.md','.mdx'): return 'configuration'
    return 'reference'


def candidate(relative):
    p=Path(relative);name=p.name.lower()
    if p.is_absolute() or '..' in p.parts or len(p.parts)>6 or any(part.lower() in SKIP for part in p.parts[:-1]): return False
    if name.startswith('.env') or re.search(r'(?:secret|credential|private[-_]?key|service[-_]?account|auth\.json)',name): return False
    if p.suffix.lower() in ('.md','.mdx'):
        return len(p.parts)==1 or p.parts[0].lower() in ('docs','.codex','.agents','tasks') or name in ('agents.md','claude.md','readme.md','design.md')
    if name in CONFIG_NAMES: return True
    if re.fullmatch(r'(?:tsconfig|eslint\.config|vite\.config|vitest\.config|tailwind\.config|postcss\.config|drizzle\.config)(?:[.\w-]*)\.(?:json|jsonc|js|mjs|cjs|ts)',name): return True
    return len(p.parts)==3 and p.parts[:2]==('.github','workflows') and p.suffix.lower() in ('.yml','.yaml')


def priority(relative):
    return (0 if Path(relative).name.lower() in ('tasks.md','agents.md','claude.md','design.md','engineering_playbook.md','readme.md') else 1 if category(relative) in ('instructions','configuration','design','plans') else 2, len(Path(relative).parts),relative)


def read_safe(root, relative):
    path = (Path(root) / relative).resolve()
    if not path.is_relative_to(Path(root).resolve()) or not path.is_file() or path.stat().st_size > LIMIT:
        return None
    return path.read_text(encoding='utf-8', errors='replace')


def collect(projects, workspaces, git):
    documents = {}
    warnings = {}
    for p in projects:
        slug = (p.get('remote') or '').rstrip('/').split('/')[-1].lower()
        p['core'] = slug in CORE or p['name'].lower() in CORE
        p['displayName'] = CORE.get(slug, CORE.get(p['name'].lower(), p['name']))
    for w in workspaces:
        root = w['path']
        raw, error = git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
        if error:
            warnings.setdefault(w['repoId'], []).append('Cannot inspect documents in ' + root)
            continue
        paths = sorted(set(x for x in raw.split('\0') if candidate(x)), key=priority)
        if len(paths)>120:
            warnings.setdefault(w['repoId'], []).append('Document discovery limited to 120 files per checkout.')
        for rel in paths[:120]:
            try:
                file_path=(Path(root)/rel).resolve()
                if not file_path.is_relative_to(Path(root).resolve()): continue
                stat=file_path.stat()
                code=next((f['code'] for f in w['files'] if f['path']==rel or rel.startswith(f['path'])), '')
                signature=(stat.st_mtime_ns,stat.st_size,w['repoId'],w.get('head'),w['branch'],code)
                cached=FILE_CACHE.get((root,rel))
                if cached and cached['signature']==signature:
                    base=cached['document']
                    documents.setdefault(base['id'],{**base,'sources':[]})['sources'].append(cached['source'])
                    continue
                content = read_safe(root, rel)
                if content is None:
                    warnings.setdefault(w['repoId'], []).append('Skipped unreadable, oversized or external file: ' + rel)
                    continue
                doc_id = hashlib.sha256((w['repoId']+'\0'+rel.lower()+'\0'+content).encode()).hexdigest()[:20]
                stamp, _ = git(root, 'log', '-1', '--format=%ct%x09%H', '--', rel)
                commit_fields = (stamp or '').strip().split('\t')
                committed = int(commit_fields[0] or 0)
                commit_sha = commit_fields[1] if len(commit_fields)>1 else None
                tracked_raw, tracked_error = git(root, 'ls-files', '--error-unmatch', '--', rel)
                tracked = tracked_error is None and bool(tracked_raw)
                head_blob, _ = git(root, 'rev-parse', 'HEAD:' + rel)
                head_blob = (head_blob or '').strip() or None
                raw_bytes = (Path(root)/rel).read_bytes()
                blob = hashlib.sha1(b'blob '+str(len(raw_bytes)).encode()+b'\0'+raw_bytes).hexdigest()
                dirty = blob != head_blob
                local_state = 'untracked' if not tracked else 'modified' if dirty else 'committed'
                source = {'path': str(Path(root)/rel), 'workspace':root, 'branch':w['branch'], 'label':w['label'],
                          'committedAt':committed, 'modified':dirty, 'tracked':tracked, 'localState':local_state, 'commit':commit_sha, 'committedBlob':head_blob, 'fileMtime':Path(root,rel).stat().st_mtime}
                if doc_id not in documents:
                    title = next((clean(l.lstrip('# ')) for l in content.splitlines() if re.match(r'^# ',l)), Path(rel).stem)
                    documents[doc_id] = {'id':doc_id, 'projectId':w['repoId'], 'relative':rel, 'title':title,
                        'kind':'tasks' if Path(rel).name.lower()=='tasks.md' else 'plan' if category(rel)=='plans' else 'document', 'category':category(rel), 'format':'markdown' if Path(rel).suffix.lower() in ('.md','.mdx') else 'text', 'sources':[], 'content':content,
                        'tasks':parse_tasks(content) if category(rel) in ('tasks','plans') else [], 'blob':blob}
                documents[doc_id]['sources'].append(source)
                FILE_CACHE[(root,rel)]={'signature':signature,'source':source,'document':{k:v for k,v in documents[doc_id].items() if k!='sources'}}
            except (OSError, ValueError):
                warnings.setdefault(w['repoId'], []).append('Cannot read ' + rel)
    active={(s['workspace'],d['relative']) for d in documents.values() for s in d['sources']}
    for key in list(FILE_CACHE):
        if key not in active: FILE_CACHE.pop(key,None)
    for d in documents.values():
        d['sources'].sort(key=lambda s:(s['committedAt'], s['modified'], s['label']=='Primary checkout'), reverse=True)
        d['source'] = d['sources'][0]
    roadmaps = []
    summaries = []
    for p in projects:
        docs = [d for d in documents.values() if d['projectId']==p['id']]
        docs.sort(key=lambda d:(d['source']['committedAt'], d['source']['modified']), reverse=True)
        task_docs = [d for d in docs if d['kind']=='tasks']
        selected = task_docs[0] if task_docs else None
        # Select one newest local version of each plan path. Other versions stay accessible as sources.
        plans = {}
        for d in docs:
            if d['kind']=='plan':
                plans.setdefault(d['relative'].lower(), d['id'])
        roadmaps.append({'projectId':p['id'], 'sourceId':selected['id'] if selected else None,
                         'tasks':selected['tasks'] if selected else [], 'alternates':[d['id'] for d in task_docs],
                         'planIds':list(plans.values()), 'documentIds':list({d['relative'].lower():d['id'] for d in reversed(docs)}.values()), 'warnings':warnings.get(p['id'], []),
                         'statusConflicts':sum(len(states)>1 for states in ({k:{t['status'] for d in task_docs for t in d['tasks'] if t['key']==k} for k in {t['key'] for d in task_docs for t in d['tasks']}}).values())})
        for d in docs:
            summary = {k:v for k,v in d.items() if k not in ('content','tasks')}
            summary['taskCounts'] = {state:sum(t['status']==state for t in d['tasks']) for state in ('active','next','blocked','done','deferred')}
            summaries.append(summary)
    return roadmaps, summaries, documents
