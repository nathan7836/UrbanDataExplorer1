#!/usr/bin/env python3
"""Vérifie la présence des briques de validation des 8 compétences RNCP."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    ("1 BDD relationnelle", ROOT / "database" / "init.sql"),
    ("2 BDD non relationnelle", ROOT / "ude_platform" / "sync_databases.py"),
    ("3 Data Lake", ROOT / "DATA_LAKE.md"),
    ("3 RGPD", ROOT / "RGPD.md"),
    ("4 HA docker", ROOT / "docker-compose.yml"),
    ("4 nginx", ROOT / "nginx" / "nginx.conf"),
    ("5 API", ROOT / "api.py"),
    ("6 Streaming", ROOT / "ude_platform" / "streaming.py"),
    ("6 Kafka", ROOT / "ude_platform" / "kafka_streaming.py"),
    ("6 Consumer", ROOT / "services" / "stream_consumer.py"),
    ("6 Kafka consumer", ROOT / "services" / "kafka_consumer.py"),
    ("7 ETL", ROOT / "public_data_integrations.py"),
    ("8 Parquet", ROOT / "ude_platform" / "parquet_lake.py"),
    ("Geo points Mongo", ROOT / "ude_platform" / "geo_points.py"),
    ("Gold", ROOT / "data" / "gold" / "real_estate_data_gold_latest.json"),
    ("CI planifiée", ROOT / ".github" / "workflows" / "pipeline-scheduled.yml"),
    ("Validation doc", ROOT / "VALIDATION_RNCP.md"),
    ("Doc BDD SQL", ROOT / "BDD_RELATIONNELLE.md"),
    ("Doc BDD NoSQL", ROOT / "BDD_NON_RELATIONNELLE.md"),
]


def main() -> int:
    ok = True
    print("Validation RNCP — Urban Data Explorer\n")
    for name, path in CHECKS:
        exists = path.exists()
        status = "OK" if exists else "MANQUANT"
        if not exists:
            ok = False
        print(f"  [{status}] {name}: {path.relative_to(ROOT)}")
    print()
    if ok:
        print("Tous les artefacts sont présents. Lancez: docker compose up -d && curl localhost:8001/health")
        return 0
    print("Exécutez d'abord: python pipeline.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
