"""Regression: the retired personal tracking API cannot write choices."""
import io
import json
import unittest
from unittest.mock import patch
import server

class ReadOnlyTests(unittest.TestCase):
    def test_old_choice_requests_are_rejected(self):
        handler=server.Handler.__new__(server.Handler)
        handler.server=type('Server',(),{'server_port':43127})()
        handler.path='/api/triage'
        body=json.dumps({'id':'example','status':'completed','note':'do not save'}).encode()
        handler.headers={'Host':'127.0.0.1:43127','Content-Type':'application/json','Content-Length':str(len(body)),'X-Workboard-Action':'triage'}
        handler.rfile=io.BytesIO(body)
        responses=[];handler.send=lambda code,body:responses.append((code,body))
        handler.do_POST()
        self.assertEqual(responses[0][0],405)
        self.assertEqual(handler.rfile.tell(),0)

    def test_state_has_no_personal_choices(self):
        board=server.Board();board.snapshot={'threads':[]}
        self.assertNotIn('choices',board.state())
        self.assertFalse(hasattr(board,'triage'))

if __name__=='__main__':unittest.main()
