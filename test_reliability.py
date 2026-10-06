import logging
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import reliability
import server

class HealthTests(unittest.TestCase):
    def test_starting_ready_failed_and_stuck_are_distinct(self):
        b=server.Board();started=time.monotonic()
        self.assertEqual(reliability.health(b,started,'/app')['status'],'starting')
        b.snapshot={'checkedAt':'today'}
        self.assertEqual(reliability.health(b,started,'/app')['status'],'ready')
        b.error='Scan failed'
        self.assertEqual(reliability.health(b,started,'/app')['status'],'degraded')
        b.error=None;b.refreshing=True;b.scan_started=time.monotonic()-130
        self.assertEqual(reliability.health(b,started,'/app')['status'],'degraded')

    def test_log_retention_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(reliability,'LOG_BYTES',256):
                logger=reliability.configure_logging(folder)
            handler=logger.handlers[-1]
            try:
                for _ in range(100):logger.info('Diagnostic entry for bounded log verification')
                handler.flush()
                files=list((Path(folder)/'.runtime').glob('service.log*'))
                self.assertLessEqual(len(files),4)
                self.assertTrue(all(f.stat().st_size<300 for f in files))
            finally:
                logger.removeHandler(handler);handler.close()

if __name__=='__main__':unittest.main()
