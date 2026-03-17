"""
Data Lake — synchronisation vers stockage objet MinIO (zone Bronze/Silver/Gold).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from ude_platform.config import (
    DATA_ROOT,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    MINIO_SECURE,
)

logger = logging.getLogger(__name__)


def _client(fast: bool = False):
    from minio import Minio
    kwargs = {
        "access_key": MINIO_ACCESS_KEY,
        "secret_key": MINIO_SECRET_KEY,
        "secure": MINIO_SECURE,
    }
    if fast:
        import urllib3
        kwargs["http_client"] = urllib3.PoolManager(
            timeout=urllib3.Timeout(connect=1.0, read=2.0),
            retries=urllib3.Retry(total=0),
        )
    return Minio(MINIO_ENDPOINT, **kwargs)


def ensure_bucket() -> bool:
    try:
        client = _client()
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
        return True
    except Exception as e:
        logger.warning("[MinIO] Bucket : %s", e)
        return False


def sync_lake_to_minio(zones: List[str] = None) -> int:
    """Upload récursif des zones data/bronze|silver|gold vers le bucket lake."""
    zones = zones or ["bronze", "silver", "gold", "export"]
    uploaded = 0
    try:
        client = _client()
        ensure_bucket()
        for zone in zones:
            base = DATA_ROOT / zone
            if not base.exists():
                continue
            for path in base.rglob("*"):
                if path.is_file() and path.name != ".gitkeep":
                    key = f"{zone}/{path.relative_to(base).as_posix()}"
                    client.fput_object(MINIO_BUCKET, key, str(path))
                    uploaded += 1
        logger.info("[MinIO] %s fichiers uploadés vers %s", uploaded, MINIO_BUCKET)
    except Exception as e:
        logger.warning("[MinIO] Sync lake : %s", e)
    return uploaded


def check_minio() -> bool:
    try:
        return _client(fast=True).bucket_exists(MINIO_BUCKET)
    except Exception:
        return False
