#!/usr/bin/env python3
"""On-demand diagnostic; never uploads inventory or starts other services."""
import json
import sys
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

try:
    with urlopen('http://127.0.0.1:8080/api/health',timeout=4) as response:
        data=json.load(response)
    if data.get('app')!='workboard':
        raise ValueError('Port 8080 belongs to another application.')
    print(json.dumps(data,indent=2))
    sys.exit(0 if data.get('status')=='ready' else 1)
except (URLError,HTTPError,ValueError) as exc:
    print('Workboard is unavailable:',str(exc))
    print('Run Launch Workboard.command to start it. No automatic startup is configured.')
    sys.exit(1)
