"""
Streaming Apache Kafka — bus d'événements pipeline (complément Redis Streams).
Producteur : fin de pipeline. Consommateur : services/kafka_consumer.py
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ude_platform.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC

logger = logging.getLogger(__name__)


def _producer():
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=[s.strip() for s in KAFKA_BOOTSTRAP_SERVERS.split(",") if s.strip()],
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        acks="all",
        retries=2,
        request_timeout_ms=5000,
    )


def publish_kafka_event(event_type: str, payload: Optional[Dict[str, Any]] = None) -> bool:
    """Publie un événement sur le topic Kafka."""
    try:
        body = {
            "type": event_type,
            "payload": payload or {},
            "at": datetime.now().isoformat(),
            "source": "urban-data-explorer",
        }
        producer = _producer()
        future = producer.send(KAFKA_TOPIC, body)
        future.get(timeout=10)
        producer.flush(timeout=5)
        producer.close()
        logger.info("[Kafka] Événement publié %s sur %s", event_type, KAFKA_TOPIC)
        return True
    except Exception as e:
        logger.warning("[Kafka] Publication impossible : %s", e)
        return False


def publish_pipeline_completed_kafka(metrics: Optional[Dict[str, Any]] = None) -> bool:
    return publish_kafka_event("pipeline.completed", metrics)


def check_kafka() -> bool:
    """Verifie si Kafka est disponible (timeout rapide)."""
    try:
        from kafka import KafkaConsumer
        import socket

        # Test rapide de connexion TCP d'abord
        servers = [s.strip() for s in KAFKA_BOOTSTRAP_SERVERS.split(",") if s.strip()]
        host, port = servers[0].split(":")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        if result != 0:
            return False

        consumer = KafkaConsumer(
            bootstrap_servers=servers,
            consumer_timeout_ms=1000,
            request_timeout_ms=2000,
            api_version_auto_timeout_ms=1000,
        )
        consumer.bootstrap_connected()
        consumer.close()
        return True
    except Exception:
        return False


def streaming_catalogue() -> Dict[str, Any]:
    return {
        "kafka": {
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "topic": KAFKA_TOPIC,
            "role": "bus d'événements durable (pipeline, sync, métriques)",
            "disponible": check_kafka(),
        },
        "comparaison": {
            "redis_streams": "léger, invalidation cache temps réel, faible latence",
            "kafka": "journal durable, replay, montée en charge, standard industrie",
        },
        "veille": "Redis retenu pour cache ; Kafka pour orchestration et traçabilité événements",
    }
