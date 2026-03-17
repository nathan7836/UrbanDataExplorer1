# Compétence — Base de données non relationnelle

> **Libellé RNCP :** *Concevoir et développer une base de données non-relationnelle universellement accessible permettant la mise à disposition des données.*

## Rôle de MongoDB dans le projet

| Couche | Stockage |
|--------|----------|
| **Bronze** | Fichiers (`data/bronze/raw_cache/`) — DVF brut, cache géocodage |
| **Gold agrégé** | **PostgreSQL** (SQL) — pas en Mongo |
| **Points géolocalisés** | **MongoDB** `geo_points` — mise à disposition NoSQL |

## Conception document

Collection **`geo_points`** — un document = un point :

| Champ | Description |
|-------|-------------|
| `type` | `dvf_transaction` ou `geocoded_address` |
| `arrondissement` | 1–20 |
| `location` | GeoJSON `Point` `[longitude, latitude]` |
| `properties` | Attributs variables (prix, surface, provider…) |

Index : `arrondissement`, `type`, `code_insee`, `2dsphere` sur `location`.

## Extraction (Bronze → Mongo)

Module : `ude_platform/geo_points.py`

- Lit `data/bronze/raw_cache/dvf_75_*.csv.gz` (échantillon par arrondissement)
- Lit `geocoding_cache.json` (adresses BAN/Nominatim)
- **Ne charge pas** le Gold JSON dans Mongo

Commande : `python scripts/sync_platform.py` ou `POST /platform/sync`

## Mise à disposition universelle

| Endpoint | Usage |
|----------|--------|
| `GET /mongo/geo-points` | Tous les points (limite 500) |
| `GET /mongo/geo-points?arrondissement=6` | Filtre par arrondissement |
| `GET /mongo/geo-points?type=dvf_transaction` | Ventes DVF uniquement |
| `GET /mongo/metadata` | Stats et catalogue |
| `GET /bdd/non-relationnelle` | Fiche compétence + état connexion |

## Exemple

```bash
curl "http://localhost:8001/mongo/geo-points?arrondissement=6&limit=10"
```
