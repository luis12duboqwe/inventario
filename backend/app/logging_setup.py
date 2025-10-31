from __future__ import annotations
import logging, os
from logging.handlers import RotatingFileHandler


def setup_logging():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger('softmobile.audit')
    logger.setLevel(logging.INFO)
    # Avoid duplicate handlers in dev reload
    if not any(isinstance(h, RotatingFileHandler) for h in logger.handlers):
        fh = RotatingFileHandler('logs/audit.jsonl', maxBytes=10_000_000, backupCount=5, encoding='utf-8')
        fmt = logging.Formatter('%(message)s')
        fh.setFormatter(fmt)
        logger.addHandler(fh)
