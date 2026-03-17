"""
Service distribué — consommateur Redis Streams (invalidation / orchestration).
"""

import json
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_STREAM = os.getenv("REDIS_STREAM", "ude:pipeline:events")
CACHE_CHANNEL = "ude:cache:invalidate"


def main():
    import redis

    client = redis.from_url(REDIS_URL, decode_responses=True)
    last_id = "$"
    logger.info("Consumer démarré — stream %s", REDIS_STREAM)

    while True:
        try:
            messages = client.xread({REDIS_STREAM: last_id}, block=5000, count=1)
            for _stream, entries in messages:
                for entry_id, fields in entries:
                    last_id = entry_id
                    payload = json.loads(fields.get("data", "{}"))
                    event_type = payload.get("type")
                    logger.info("Événement reçu : %s", event_type)
                    if event_type == "pipeline.completed":
                        client.publish(CACHE_CHANNEL, json.dumps({"action": "invalidate"}))
                        logger.info("Signal invalidation cache publié")
        except Exception as e:
            logger.warning("Erreur consumer : %s — retry", e)
            time.sleep(2)


if __name__ == "__main__":
    main()
