"""Optional presentation scope; never executable configuration or file-discovery roots."""
import json
from pathlib import Path


def load(path):
    path = Path(path)
    if not path.exists():
        return None
    if path.stat().st_size > 65536:
        raise ValueError('Project configuration exceeds 64 KiB')
    value = json.loads(path.read_text())
    if not isinstance(value, dict) or not isinstance(value.get('projects'), dict):
        raise ValueError('Project configuration requires a projects object')
    for slug, label in value['projects'].items():
        if not isinstance(slug, str) or not isinstance(label, str) or not slug or not label or len(slug)>200 or len(label)>100:
            raise ValueError('Project configuration keys and labels must be short nonempty strings')
    return value['projects']


def apply(projects, aliases):
    for p in projects:
        slug = (p.get('remote') or '').rstrip('/').split('/')[-1].lower()
        key = slug if aliases is not None and slug in aliases else p['name'].lower()
        p['core'] = p.get('kind') != 'chats' if aliases is None else key in aliases
        p['displayName'] = (aliases or {}).get(key, p['name'])
