"""Read only the explicitly approved instruction sources; never general file access."""
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import stat

LIMIT = 64 * 1024


def read_source(path, key, title):
    result = {'id': key, 'title': title, 'path': str(path), 'content': '', 'status': 'unavailable'}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as source:
            meta = os.fstat(source.fileno())
            if not stat.S_ISREG(meta.st_mode):
                raise ValueError('Source is not a regular file.')
            data = source.read(LIMIT + 1)
        if len(data) > LIMIT:
            raise ValueError('Source exceeds the 64 KiB reading limit.')
        result.update(status='available', content=data.decode('utf-8'),
                      modifiedAt=meta.st_mtime, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    except FileNotFoundError:
        result['status'] = 'missing'
    except (OSError, ValueError, UnicodeError):
        result['error'] = 'Cannot safely read this source. It may be inaccessible, oversized, a symlink, or invalid UTF-8.'
    return result


def snapshot(codex_home, app_root):
    home, root = Path(codex_home), Path(app_root)
    sources = [read_source(home / 'AGENTS.md', 'global', 'Global Codex instructions'),
               read_source(home / 'AGENTS.override.md', 'override', 'Global override'),
               read_source(root / 'CHARTER.md', 'charter', 'Workboard charter')]
    standard, override, _ = sources
    if override['status'] == 'unavailable':
        effective = 'unknown'
    elif override['content'].strip():
        effective = 'override'
    elif standard['status'] == 'available' and standard['content'].strip():
        effective = 'global'
    else:
        effective = 'unknown' if standard['status'] == 'unavailable' else None
    return {'checkedAt': datetime.now(timezone.utc).isoformat(), 'sources': sources,
            'selectedGlobalFile': effective,
            'coverage': 'Local files only. This is not proof of instructions loaded by an existing chat or a cloud session.'}
