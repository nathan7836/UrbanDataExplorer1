# Data Lake — Urban Data Explorer

## Zones (architecture Medallion)

| Zone | Chemin | Contenu | Accès |
|------|--------|---------|--------|
| **Bronze** | `data/bronze/` | Données brutes, `raw_cache/`, JSON fusionné | Pipeline écriture ; analystes lecture contrôlée |
| **Silver** | `data/silver/` | Données nettoyées, normalisées | Pipeline |
| **Gold** | `data/gold/` | Données enrichies prêtes consommation | API, **PostgreSQL** |
| **Points géo** | Bronze → Mongo `geo_points` | Coordonnées DVF / géocodage | API `/mongo/geo-points` |
| **Export** | `data/export/` | CSV, Parquet, GeoJSON | BI, dashboard |
| **Lake objet** | Bucket MinIO `ude-lake` | Copie des zones Bronze/Silver/Gold/Export | `ude_platform/lake_storage.py` |

## Flux

```text
Sources APIs → Bronze → Silver → Gold → Export
                              ↓
                    PostgreSQL + MongoDB
                              ↓
                         API FastAPI → Dashboard
```

## Performance

- Cache disque : `raw_cache/` (DVF, parquet délinquance)
- Gold analytique partitionné : `data/gold/parquet/prix_annuel/annee=YYYY/`
- API : cache mémoire + invalidation Redis après pipeline

## Sécurité

Voir [RGPD.md](RGPD.md).

## Commandes

```bash
python pipeline.py
python scripts/sync_platform.py  # si Gold déjà présent
docker compose up -d
```
