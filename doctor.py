#!/usr/bin/env python3
"""Read-only setup diagnostics. No installation, login, project scan or changes."""
import argparse
import http.client
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def port_status(port):
    try:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
        return 'ok', f'Loopback port {port} is available.'
    except OSError:
        connection = http.client.HTTPConnection('127.0.0.1', port, timeout=2)
        try:
            connection.request('GET', '/api/health')
            response = connection.getresponse()
            data = json.loads(response.read(65536))
            if response.status == 200 and data.get('app') == 'workboard':
                if data.get('root') == str(ROOT):
                    return 'ok', f'This checkout is already running ({data.get("status", "unknown")}).'
                return 'error', 'Another Workboard checkout/demo occupies this port; inspect it before starting.'
        except (OSError, ValueError, AttributeError, http.client.HTTPException):
            pass
        finally:
            connection.close()
        return 'error', f'Port {port} is occupied or cannot be bound. Do not kill an unidentified process.'


def inspect(demo=False, port=43127, config=None, github=False):
    checks = []
    def add(name, status, detail):
        checks.append({'check': name, 'status': status, 'detail': detail})
    add('Python', 'ok' if sys.version_info >= (3, 10) else 'error', f'{sys.version.split()[0]} at {sys.executable}; need 3.10+.')
    add('Platform', 'ok' if platform.system() == 'Darwin' else 'warning',
        f'{platform.system()}: macOS is the tested desktop platform; other desktop integrations are unsupported.')
    add('Port', *port_status(port))
    if demo:
        add('Sources', 'ok', 'Synthetic demo: no Codex index, configuration, Git or GitHub checks performed.')
        return checks
    add('Git', 'ok' if shutil.which('git') else 'error', shutil.which('git') or 'Git missing; install only with user approval.')
    try:
        import configuration
        aliases = configuration.load(config or ROOT / 'workboard.local.json')
        add('Configuration', 'ok', 'Default: all discovered projects.' if aliases is None else f'{len(aliases)} display aliases; these do not add discovery roots.')
    except (OSError, ValueError) as exc:
        add('Configuration', 'error', str(exc))
    home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))).expanduser().resolve()
    try:
        import server
        rows, projects, schema = server.CodexReader(home).index()
        add('Codex', 'ok', f'{home}: {schema}, {len(rows)} indexed chats, {len(projects)} saved project roots. Session files and repositories are not validated by this check.')
        if not rows and not projects:
            add('Discovery', 'warning', 'Index is empty. Use Codex in a real project first; Workboard does not search your disk or GitHub account.')
    except Exception as exc:
        add('Codex', 'error', f'{home}: {exc}. Open/use local Codex or select its actual CODEX_HOME; do not create/edit its database.')
    gh = shutil.which('gh')
    add('GitHub CLI', 'ok' if gh else 'warning', gh or 'Optional gh is missing; remote evidence will be unavailable.')
    if github and gh:
        try:
            result = subprocess.run([gh, 'auth', 'status', '--hostname', 'github.com'],
                                    capture_output=True, timeout=15, env={**os.environ, 'GH_PROMPT_DISABLED': '1'})
            add('GitHub authentication', 'ok' if result.returncode == 0 else 'warning',
                'GitHub.com CLI authentication check passed; individual private/org repository access is not proven.' if result.returncode == 0 else 'Authentication check failed. Run gh auth status --hostname github.com privately; do not paste tokens into Workboard.')
        except (OSError, subprocess.TimeoutExpired):
            add('GitHub authentication', 'warning', 'Authentication could not be checked; verify CLI/network access manually.')
    elif not github:
        add('GitHub authentication', 'warning', 'Not checked. Add --github to check the existing login. Normal server mode may use that login automatically.')
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--github', action='store_true', help='Check existing GitHub CLI authentication; never log in')
    parser.add_argument('--port', type=int, default=43127)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    checks = inspect(args.demo, args.port, args.config, args.github)
    if args.json:
        print(json.dumps({'checks': checks}, indent=2))
    else:
        for check in checks:
            print(f'{check["status"].upper():7} {check["check"]}: {check["detail"]}')
        print('Warnings describe optional/unverified coverage. Errors need attention before real-data startup.')
    return int(any(check['status'] == 'error' for check in checks))


if __name__ == '__main__':
    raise SystemExit(main())
