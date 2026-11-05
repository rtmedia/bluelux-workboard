#!/usr/bin/env python3
"""Manage this user's Workboard launchd service; no system-wide installation."""
import argparse
import os
from pathlib import Path
import plistlib
import sys
import subprocess

ROOT = Path(__file__).resolve().parent
LABEL = 'com.bluelux.workboard'
PLIST = Path.home() / 'Library' / 'LaunchAgents' / (LABEL + '.plist')
TARGET = 'gui/' + str(os.getuid()) + '/' + LABEL


def configuration(root, python):
    return {'Label': LABEL, 'ProgramArguments': [str(python), '-B', str(root/'server.py')],
            'WorkingDirectory': str(root), 'RunAtLoad': True, 'KeepAlive': True,
            'ThrottleInterval': 10, 'ProcessType': 'Interactive',
            'EnvironmentVariables': {
                'PATH': os.environ.get('PATH', os.defpath),
                'CODEX_HOME': str(Path(os.environ.get('CODEX_HOME', str(Path.home()/'.codex'))).expanduser().resolve()),
                **({'GH_CONFIG_DIR': str(Path(os.environ['GH_CONFIG_DIR']).expanduser().resolve())} if os.environ.get('GH_CONFIG_DIR') else {}),
                'WORKBOARD_SUPERVISED':'1'},
            'StandardOutPath':'/dev/null', 'StandardErrorPath':'/dev/null'}


def loaded():
    return subprocess.run(['/bin/launchctl','print',TARGET],capture_output=True).returncode == 0


def start():
    subprocess.run(['/bin/launchctl','kickstart',TARGET],check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['enable','status','disable'])
    action=parser.parse_args().action
    if action=='status':
        print('Automatic startup and restart: '+('enabled' if loaded() else 'not loaded'))
        return
    if action=='enable':
        python=sys.executable
        if not python: raise SystemExit('Python 3 is required.')
        config=configuration(ROOT,python)
        if PLIST.exists():
            existing=plistlib.loads(PLIST.read_bytes())
            if existing.get('Label')!=LABEL or existing.get('WorkingDirectory')!=str(ROOT):
                raise SystemExit('An unrelated service uses this path; left unchanged.')
            if loaded():
                print('Workboard service is already loaded.');return
        PLIST.parent.mkdir(parents=True,exist_ok=True)
        PLIST.write_bytes(plistlib.dumps(config))
        PLIST.chmod(0o644)
        subprocess.run(['/bin/launchctl','bootstrap','gui/'+str(os.getuid()),str(PLIST)],check=True)
        print('Enabled Workboard startup at login and restart on exit.')
    else:
        if PLIST.exists():
            existing=plistlib.loads(PLIST.read_bytes())
            if existing.get('WorkingDirectory')!=str(ROOT):raise SystemExit('Service belongs to another folder; left unchanged.')
            if loaded():subprocess.run(['/bin/launchctl','bootout',TARGET],check=True)
            saved=PLIST.with_suffix('.plist.disabled')
            if saved.exists():raise SystemExit('Disabled copy already exists; plist retained. Remove it only after review.')
            PLIST.rename(saved)
            print('Disabled. Configuration preserved at '+str(saved))
        else:print('No startup configuration installed.')

if __name__=='__main__':main()
