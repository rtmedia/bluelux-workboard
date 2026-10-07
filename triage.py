"""Workboard-owned choices. Never writes source repositories or Codex data."""
import json
import os
from pathlib import Path
import threading
from datetime import datetime, timezone


def request_token(thread):
    return str(thread.get('requestAt') or thread.get('lastMessageAt') or thread.get('updatedAt') or '')


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def read(self):
        try:
            data = json.loads(self.path.read_text())
            if not isinstance(data, dict) or any(not isinstance(v, dict) for v in data.values()):
                raise ValueError('Invalid choices file')
            return data
        except FileNotFoundError:
            return {}

    def update(self, thread, action, note):
        if action not in {'focus', 'resume', 'completed', 'parked', 'auto'}:
            raise ValueError('Choose a supported discussion status.')
        if not isinstance(note, str) or len(note) > 1000:
            raise ValueError('Next step must be text of at most 1000 characters.')
        with self.lock:
            items = self.read()  # Never overwrite unreadable saved choices.
            if action == 'focus':
                for item in items.values():
                    if item.get('status') == 'focus':
                        item['status'] = 'resume'
            if action == 'auto':
                items.pop(thread['id'], None)
            else:
                items[thread['id']] = {'status': action, 'note': note.strip(),
                    'requestToken': request_token(thread),
                    'updatedAt': datetime.now(timezone.utc).isoformat()}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            with temporary.open('w') as f:
                json.dump(items, f, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.path)
            return items
