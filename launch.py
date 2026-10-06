#!/usr/bin/env python3
"""Start once, then open the existing local app. Uses the current Python installation."""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser
import fcntl

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8080'


def running():
    try:
        with urlopen(URL + '/api/health', timeout=1) as r:
            return json.load(r).get('app') == 'workboard'
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-open', action='store_true')
    args = parser.parse_args()
    runtime = ROOT / '.runtime'
    runtime.mkdir(exist_ok=True)
    with (runtime / 'launch.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not running():
            # Startup-only errors are bounded on every launch; service logs rotate independently.
            with (runtime / 'startup.log').open('wb') as log:
                child = subprocess.Popen([sys.executable, '-B', str(ROOT / 'server.py')], cwd=ROOT,
                                         stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                         start_new_session=True, close_fds=True)
            (runtime / 'server.pid').write_text(str(child.pid))
            for _ in range(40):
                if running():
                    break
                if child.poll() is not None:
                    raise SystemExit('Could not start Workboard. Port 8080 may be in use. See .runtime/startup.log.')
                time.sleep(.2)
            else:
                raise SystemExit('Workboard did not start. See .runtime/startup.log.')
    print('Workboard is running: ' + URL)
    if not args.no_open:
        webbrowser.open(URL)


if __name__ == '__main__':
    main()
