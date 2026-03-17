"""
Système distribué — événements via Redis Streams.
Producteur : fin de pipeline. Consommateur : invalidation cache API.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ude_platform.config import REDIS_STREAM, REDIS_URL

logger = logging.getLogger(__name__)


def _redis_client():
    import redis
    return redis.from_url(REDIS_URL, decode_responses=True)


def publish_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> bool:
    """Publie un événement sur le stream Redis (compétence streaming)."""
    try:
        client = _redis_client()
        body = {
            "type": event_type,
            "payload": payload or {},
            "at": datetime.now().isoformat(),
        }
        msg_id = client.xadd(REDIS_STREAM, {"data": json.dumps(body)})
        logger.info("[Redis] Événement publié %s id=%s", event_type, msg_id)
        return True
    except Exception as e:
        logger.warning("[Redis] Publication impossible : %s", e)
        return False


def publish_pipeline_completed(metrics: Optional[Dict[str, Any]] = None) -> bool:
    redis_ok = publish_event("pipeline.completed", metrics)
    try:
        from ude_platform.kafka_streaming import publish_pipeline_completed_kafka

        kafka_ok = publish_pipeline_completed_kafka(metrics)
    except ImportError:
        kafka_ok = False
    return redis_ok or kafka_ok


def consume_events_once(count: int = 10, block_ms: int = 1000) -> int:
    """Lit les derniers événements (consumer batch). Retourne le nombre traité."""
    try:
        client = _redis_client()
        last_id = "0-0"
        processed = 0
        messages = client.xread({REDIS_STREAM: last_id}, count=count, block=block_ms)
        for _stream, entries in messages:
            for entry_id, fields in entries:
                data = json.loads(fields.get("data", "{}"))
                logger.info("[Redis] Consumer reçu : %s", data.get("type"))
                processed += 1
        return processed
    except Exception as e:
        logger.warning("[Redis] Consumer : %s", e)
        return 0


def check_redis() -> bool:
    try:
        return _redis_client().ping()
    except Exception:
        return False
