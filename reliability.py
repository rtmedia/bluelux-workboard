"""Local health reporting and bounded operational diagnostics."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time

LOG_BYTES = 1024 * 1024
LOG_BACKUPS = 3


def configure_logging(root):
    folder = Path(root) / '.runtime'
    folder.mkdir(exist_ok=True)
    handler = RotatingFileHandler(folder/'service.log', maxBytes=LOG_BYTES, backupCount=LOG_BACKUPS, encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger = logging.getLogger('workboard')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


def health(board, started, root):
    now = time.monotonic()
    age = now-board.scan_started if board.refreshing and board.scan_started else 0
    state = 'degraded' if board.error or age>120 else 'ready' if board.snapshot else 'starting'
    return {'app':'workboard','version':'1.1','readOnly':True,'status':state,
            'uptimeSeconds':int(now-started),'root':str(root),'refreshing':board.refreshing,
            'scanSeconds':round(age,1),'lastScan':(board.snapshot or {}).get('checkedAt'),
            'lastScanDurationSeconds':board.scan_duration,'error':board.error,
            'logPolicy':{'maxBytesPerFile':LOG_BYTES,'backups':LOG_BACKUPS},
            'automaticStartup':False}
