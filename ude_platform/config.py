"""Configuration plateforme (variables d'environnement)."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATA_ROOT = Path(os.getenv("UDE_DATA_ROOT", "data"))

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://ude_admin:ude_admin_dev@localhost:5433/urban_data",
)
POSTGRES_READER_URL = os.getenv(
    "POSTGRES_READER_URL",
    "postgresql://ude_reader:ude_reader_dev@localhost:5433/urban_data",
)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "urban_data")
# NoSQL : points géolocalisés (Bronze), pas le Gold agrégé
MONGO_GEO_COLLECTION = os.getenv("MONGO_GEO_COLLECTION", "geo_points")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", MONGO_GEO_COLLECTION)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_STREAM = os.getenv("REDIS_STREAM", "ude:pipeline:events")

# Kafka — hôte : localhost:9094 | conteneurs Docker : kafka:9092
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9094")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "ude.pipeline.events")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "ude_minio")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "ude_minio_secret")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "ude-lake")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"

DATA_BACKEND = os.getenv("DATA_BACKEND", "auto")  # auto | json | postgres | mongo
GOLD_JSON = DATA_ROOT / "gold" / "real_estate_data_gold_latest.json"
