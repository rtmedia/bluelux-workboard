import json
import subprocess
import sys
import unittest
from unittest.mock import patch
import account_usage
import telemetry

class AccountUsageTests(unittest.TestCase):
    def test_allowlist_and_unknown(self):
        result = account_usage.normalize({'accountId':'private', 'rateLimitsByLimitId':{'codex':{'credits':{'balance':'12.5'},'primary':{'usedPercent':20,'windowDurationMins':10080,'resetsAt':123}}}, 'rateLimitResetCredits':{'availableCount':3,'credits':[{'id':'private','status':'available','expiresAt':456}]}})
        self.assertEqual(result['credits']['balance'],12.5)
        self.assertEqual(result['resets']['availableCount'],3)
        self.assertEqual(len(result['resets']['items']),1)  # Count need not match capped details.
        self.assertNotIn('private',json.dumps(result))
        self.assertIsNone(account_usage.normalize({})['resets'])
        self.assertIsNone(account_usage.normalize({'rateLimitResetCredits':{'availableCount':True}})['resets']['availableCount'])
        for value in ('NaN','-1','bad',True):
            self.assertIsNone(telemetry.credits({'balance':value})['balance'])
        self.assertEqual(telemetry.credits({'balance':'0'})['balance'],0)

    def test_protocol_is_read_only(self):
        script = '''import sys,json
for expected in ['initialize','initialized','account/rateLimits/read']:
 msg=json.loads(sys.stdin.readline())
 if msg['method']!=expected: sys.exit(2)
 if expected=='initialize': print(json.dumps({'id':1,'result':{}}),flush=True)
 if expected=='account/rateLimits/read': print(json.dumps({'id':2,'result':{'rateLimitResetCredits':{'availableCount':0,'credits':[]}}}),flush=True)
'''
        real_popen=subprocess.Popen
        with patch('account_usage.executable',return_value='existing-codex'), patch('account_usage.subprocess.Popen',side_effect=lambda args,**kw:real_popen([sys.executable,'-c',script],**kw)):
            result=account_usage.read('/unused')
        self.assertEqual(result['resets']['availableCount'],0)
        self.assertEqual(result['resets']['items'],[])

    def test_failed_refresh_preserves_snapshot_and_cache(self):
        monitor=account_usage.Monitor('/unused')
        monitor.data={'observedAt':'old'}
        with patch('account_usage.read',side_effect=RuntimeError('secret')):
            monitor._read()
        self.assertEqual(monitor.data,{'observedAt':'old'})
        self.assertNotIn('secret',monitor.error)
        with patch('account_usage.time.monotonic',return_value=1000),patch('account_usage.threading.Thread') as thread:
            monitor.checked=950
            monitor.refresh()
            thread.assert_not_called()

    def test_timeout_terminates_reader(self):
        real_popen=subprocess.Popen
        spawned=[]
        def spawn(args,**kw):
            process=real_popen([sys.executable,'-c','import time; time.sleep(60)'],**kw)
            spawned.append(process)
            return process
        with patch('account_usage.executable',return_value='existing-codex'), patch('account_usage.subprocess.Popen',side_effect=spawn), patch('account_usage.time.monotonic',side_effect=[0,21]):
            with self.assertRaisesRegex(RuntimeError,'timed out'):
                account_usage.read('/unused')
        self.assertIsNotNone(spawned[0].poll())
