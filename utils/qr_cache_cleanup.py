"""QR Cache Cleanup Utility

Deletes QR code image files older than configured TTL (PDF_QR_CACHE_TTL) inside static/qr_codes.
Usage (CLI):
    python -m utils.qr_cache_cleanup [--dry-run]
Can be cronned daily. If TTL=0 (no caching) this script removes nothing.
"""
from __future__ import annotations
import os, argparse, time
from datetime import datetime, UTC
from config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

def cleanup(dry_run: bool=False, base_dir: str='static/qr_codes', ttl: int|None=None) -> int:
    ttl = ttl if ttl is not None else int(getattr(Config, 'PDF_QR_CACHE_TTL', 0))
    if ttl <= 0:
        logger.info('TTL <= 0 (no caching) – nothing to clean.')
        return 0
    if not os.path.isdir(base_dir):
        logger.info('QR directory not found: %s', base_dir)
        return 0
    now = time.time()
    removed = 0
    for fname in os.listdir(base_dir):
        if not fname.lower().endswith(('.png','.svg')):
            continue
        path = os.path.join(base_dir, fname)
        try:
            age = now - os.path.getmtime(path)
            if age > ttl:
                if dry_run:
                    logger.info('[DRY] Would remove %s age=%.0fs > ttl=%ss', fname, age, ttl)
                else:
                    os.remove(path)
                    removed += 1
                    logger.info('Removed %s age=%.0fs > ttl=%ss', fname, age, ttl)
        except Exception as e:
            logger.warning('Skip file %s error %s', fname, e)
    logger.info('Cleanup complete removed=%d ttl=%s dir=%s', removed, ttl, base_dir)
    return removed

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Cleanup expired QR cache files.')
    ap.add_argument('--dry-run', action='store_true', help='List files that would be removed without deleting.')
    ap.add_argument('--dir', default='static/qr_codes', help='QR cache directory')
    ap.add_argument('--ttl', type=int, default=None, help='Override TTL seconds (default: PDF_QR_CACHE_TTL env)')
    args = ap.parse_args()
    cleanup(dry_run=args.dry_run, base_dir=args.dir, ttl=args.ttl)
