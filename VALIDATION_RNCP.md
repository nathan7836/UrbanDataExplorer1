# Validation des 8 compétences RNCP

## Matrice de validation

| # | Compétence | Implémentation | Preuve / commande |
|---|------------|----------------|-------------------|
| 1 | BDD relationnelle | [BDD_RELATIONNELLE.md](BDD_RELATIONNELLE.md) — Postgres, gouvernance `ude_reader`, vues client | `GET /bdd/relationnelle` · `GET /sql/accessibilite` · `pytest tests/test_load_sql.py` |
| 2 | BDD non relationnelle | [BDD_NON_RELATIONNELLE.md](BDD_NON_RELATIONNELLE.md) — MongoDB `geo_points` (Bronze) | `GET /bdd/non-relationnelle` · `GET /mongo/geo-points` |
| 3 | Data Lake + RGPD | Medallion `data/` + MinIO + [DATA_LAKE.md](DATA_LAKE.md) + [RGPD.md](RGPD.md) | `docker compose up minio` · sync MinIO dans pipeline |
| 4 | Infra HA | nginx + 2× API + healthchecks | `docker compose up` · `GET /health` · arrêt `api1` |
| 5 | API inter-services | FastAPI, OpenAPI, sync endpoint, gouvernance | `http://localhost:8001/docs` · `GET /platform/governance` · `GET /platform/freshness` |
| 6 | Streaming distribué | Redis Streams + consumer | `services/stream_consumer.py` · event `pipeline.completed` |
| 7 | Transformation multi-sources | `public_data_integrations.py` + Medallion | `python pipeline.py` |
| 8 | Perf pipelines | Cache, Parquet partitionné, métriques | `data/gold/parquet/` · logs orchestration |

## Démarrage plateforme complète

```bash
pip install -r requirements.txt
python pipeline.py
docker compose up -d
curl http://localhost:8001/health
curl http://localhost:8001/sql/accessibilite
```

## Variables d'environnement

Voir [.env.example](.env.example).

## Backend API

`DATA_BACKEND=auto` : PostgreSQL → MongoDB → fichier JSON.

## Soutenance (1 phrase par compétence)

1. **SQL** : modèle relationnel avec vues métier pour le client en lecture seule.
2. **NoSQL** : même jeu en documents Mongo pour flexibilité schéma.
3. **Lake** : zones Bronze/Silver/Gold versionnées + copie MinIO + doc RGPD.
4. **HA** : deux instances API derrière nginx, healthchecks Docker.
5. **API** : point d’accès unique pour le dashboard et les services.
6. **Streaming** : Redis notifie la fin de pipeline et invalide le cache API.
7. **ETL** : multi-sources open data fusionnées par code INSEE.
8. **Perf** : cache, Parquet partitionné par année, métriques de durée par étape.
