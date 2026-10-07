import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import triage
import server

class ChoiceTests(unittest.TestCase):
    def test_persist_focus_switch_and_reset(self):
        with tempfile.TemporaryDirectory() as root:
            store=triage.Store(Path(root)/'triage.json')
            a={'id':'a','requestAt':'one'};b={'id':'b','requestAt':'two'}
            store.update(a,'focus','Verify sign-in')
            items=store.update(b,'focus','Ship')
            self.assertEqual(items['a']['status'],'resume')
            self.assertEqual(items['b']['status'],'focus')
            self.assertEqual(triage.Store(store.path).read()['a']['note'],'Verify sign-in')
            self.assertEqual(store.update(b,'completed','')['b']['requestToken'],'two')
            self.assertNotIn('b',store.update(b,'auto',''))
    def test_invalid_or_corrupt_data_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            store=triage.Store(Path(root)/'triage.json')
            with self.assertRaises(ValueError):store.update({'id':'a'},'wrong','')
            with self.assertRaises(ValueError):store.update({'id':'a'},'resume','x'*1001)
            store.path.write_text('corrupt')
            with self.assertRaises(ValueError):store.update({'id':'a'},'resume','')
            self.assertEqual(store.path.read_text(),'corrupt')
    def test_http_action_stale_request_and_unknown_chat(self):
        with tempfile.TemporaryDirectory() as root:
            board=server.Board();board.triage=triage.Store(Path(root)/'triage.json')
            board.snapshot={'threads':[{'id':'a','requestAt':'current'}]}
            handler=server.Handler.__new__(server.Handler)
            handler.server=type('Server',(),{'server_port':43127})()
            handler.path='/api/triage'
            responses=[];handler.send=lambda code,body:responses.append((code,body))
            def submit(data,header=True):
                encoded=json.dumps(data).encode();handler.rfile=io.BytesIO(encoded)
                handler.headers={'Host':'127.0.0.1:43127','Content-Type':'application/json','Content-Length':str(len(encoded))}
                if header:handler.headers['X-Workboard-Action']='triage'
                handler.do_POST();return responses[-1][0]
            with patch.object(server,'BOARD',board):
                data={'id':'a','status':'completed','requestToken':'old'}
                self.assertEqual(submit(data),409)
                self.assertEqual(submit({**data,'requestToken':'current'},False),403)
                self.assertEqual(submit({**data,'id':'unknown'}),404)
                self.assertEqual(submit({**data,'requestToken':'current'}),200)
            self.assertEqual(board.triage.read()['a']['status'],'completed')

if __name__=='__main__':unittest.main()
