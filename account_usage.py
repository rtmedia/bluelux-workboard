"""Read-only optional Codex app-server usage adapter. No prompts or reset redemption."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import threading
import time
import telemetry


def normalize(result):
    buckets = result.get('rateLimitsByLimitId')
    raw = buckets.get('codex') if isinstance(buckets, dict) else result.get('rateLimits')
    raw = raw if isinstance(raw, dict) else {}
    limits = {k: {'used_percent': v.get('usedPercent'), 'window_minutes': v.get('windowDurationMins'),
                   'resets_at': v.get('resetsAt')} for k in ('primary', 'secondary')
              if isinstance(v := raw.get(k), dict)}
    limits['credits'] = raw.get('credits')
    stamp = datetime.now(timezone.utc).isoformat()
    usage = telemetry.snapshot({'rate_limits': limits}, stamp)
    resets = result.get('rateLimitResetCredits')
    usage['resets'] = None
    if isinstance(resets, dict):
        count = telemetry.number(resets.get('availableCount'))
        details = resets.get('credits')
        usage['resets'] = {'availableCount': count if count is not None and float(count).is_integer() else None,
                           'items': [{'expiresAt': telemetry.number(x.get('expiresAt'))}
                                     for x in details[:100] if isinstance(x, dict) and x.get('status') == 'available']
                           if isinstance(details, list) else None}
    usage['source'] = 'Signed-in Codex account · read-only app-server check'
    return usage


def executable():
    # Existing installation only; never install or download a CLI.
    for path in ('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex',
                 '/Applications/Codex.app/Contents/Resources/codex', shutil.which('codex')):
        if path and Path(path).is_file() and os.access(path, os.X_OK):
            return path
    raise RuntimeError('Codex executable unavailable; account usage unknown.')


def read(home):
    process = subprocess.Popen([executable(), 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env={**os.environ, 'CODEX_HOME': str(home)})
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 20
    buffer = b''
    total = 0
    def send(value):
        process.stdin.write((json.dumps(value)+'\n').encode())
        process.stdin.flush()
    try:
        send({'id': 1, 'method': 'initialize', 'params': {'clientInfo': {'name': 'workboard', 'version': '1.0'}}})
        while time.monotonic() < deadline:
            if not selector.select(max(0, deadline-time.monotonic())):
                break
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > 1024*1024:
                raise RuntimeError('Account response exceeded its size limit.')
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                message = json.loads(line)
                if message.get('id') not in (1, 2):
                    continue
                if message.get('error'):
                    raise RuntimeError('Codex account usage unavailable; check sign-in or CLI compatibility.')
                if message.get('id') == 1:
                    send({'method': 'initialized'})
                    send({'id': 2, 'method': 'account/rateLimits/read'})
                elif isinstance(message.get('result'), dict):
                    return normalize(message['result'])
        raise RuntimeError('Codex account usage timed out or disconnected.')
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        process.stdin.close()
        process.stdout.close()


class Monitor:
    def __init__(self, home):
        self.home, self.data, self.error = home, None, None
        self.checked = 0
        self.busy = False
        self.lock = threading.Lock()

    def refresh(self):
        with self.lock:
            if self.busy or time.monotonic()-self.checked < 300:
                return
            self.busy = True
            self.checked = time.monotonic()
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        try:
            self.data = read(self.home)
            self.error = None
        except Exception:
            self.error = 'Account check unavailable. Previous values, if any, may be outdated.'
        finally:
            self.busy = False

    def state(self):
        return {'data': self.data, 'error': self.error, 'refreshing': self.busy}
