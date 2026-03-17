"""
Consommateur Kafka — traite les événements pipeline en quasi temps réel.
Relais vers Redis pub/sub pour invalidation cache API (< 1 s après batch).
"""

from __future__ import annotations

import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "ude.pipeline.events")
KAFKA_GROUP = os.getenv("KAFKA_GROUP", "ude-pipeline-consumers")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_CHANNEL = os.getenv("CACHE_INVALIDATE_CHANNEL", "ude:cache:invalidate")


def _handle_event(payload: dict) -> None:
    event_type = payload.get("type")
    logger.info("Kafka événement : %s @ %s", event_type, payload.get("at"))
    if event_type != "pipeline.completed":
        return
    try:
        import redis

        client = redis.from_url(REDIS_URL, decode_responses=True)
        client.publish(CACHE_CHANNEL, json.dumps({"action": "invalidate", "via": "kafka"}))
        logger.info("Invalidation cache relayée (latence post-batch quasi temps réel)")
    except Exception as e:
        logger.warning("Relais Redis impossible : %s", e)


def main() -> None:
    from kafka import KafkaConsumer

    logger.info("Kafka consumer — topic=%s bootstrap=%s", KAFKA_TOPIC, KAFKA_BOOTSTRAP_SERVERS)

    while True:
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=[s.strip() for s in KAFKA_BOOTSTRAP_SERVERS.split(",") if s.strip()],
                group_id=KAFKA_GROUP,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            for message in consumer:
                t0 = time.perf_counter()
                _handle_event(message.value)
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                logger.info("Traitement événement en %s ms", elapsed_ms)
        except Exception as e:
            logger.warning("Kafka consumer erreur : %s — retry 5s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
