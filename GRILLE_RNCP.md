# Synthèse grille de notation RNCP — Urban Data Explorer

**Mise à jour :** juin 2026 — alignée sur le code actuel.

## Légende

| Niveau | Signification |
|--------|----------------|
| **OK** | Démo + artefact vérifiable |
| **Partiel** | Implémenté avec limites assumées |
| **Gap** | Hors périmètre MVP |

---

## BDD relationnelle

| Critère grille | Niveau | Preuve |
|----------------|--------|--------|
| Modèle répond au besoin gouvernance | **OK** | `database/init.sql`, vues `v_*`, `governance_access` |
| Technologies appropriées | **OK** | PostgreSQL 16, SQL, `ude_reader` |
| Normalisation + intégrité | **OK** | PK/FK, CHECK, UNIQUE |
| Tests de charge intégrité/perf | **OK** | `tests/test_load_sql.py` (50 requêtes vue accessibilité) |

## BDD NoSQL

| Critère | Niveau | Preuve |
|---------|--------|--------|
| Choix justifié | **OK** | Mongo `geo_points` (GeoJSON), Gold en SQL |
| Semi/non structuré | **OK** | `location`, `properties` variables, index 2dsphere |

## Architecture, perf, sécurité, HA

| Critère | Niveau | Preuve |
|---------|--------|--------|
| Indicateurs perf définis/suivis | **OK** | `GET /platform/metrics`, `pipeline_runs.metrics_json`, `pipeline_finalize` |
| Sécurité / RGPD | **Partiel** | `RGPD.md`, rôles SQL, `UDE_API_KEY`, rate limit — pas de chiffrement au repos |
| HA continuité | **Partiel** | nginx + api×2, healthchecks Docker |
| Scalabilité | **Partiel** | API stateless, BDD séparées |
| Résilience testée | **Partiel** | Healthchecks ; pas de chaos test formalisé |

## API

| Critère | Niveau | Preuve |
|---------|--------|--------|
| Technologies appropriées | **OK** | FastAPI, OpenAPI `/docs` |
| Données accessibles | **OK** | `/arrondissements`, `/sql/*`, `/mongo/*` |
| Complexité adaptée | **OK** | Filtres année/arr/bbox |
| Authentification | **Partiel** | `UDE_API_KEY` + `X-API-Key` (optionnel si vide) |
| Quotas compréhensibles | **OK** | `GET /platform/governance`, headers `X-RateLimit-*` |

## Streaming

| Critère | Niveau | Preuve |
|---------|--------|--------|
| Veille + solution adaptée | **OK** | Redis Streams vs Kafka (léger, event-driven) |
| Micro-batch secondes/ms | **Gap** | Batch ~1 min ; transformation seule ~0,2 s |
| Temps réel analytique | **Gap** | Événements post-batch, pas flux DVF continu |
| Analyse instant T utilisateur | **OK** | `GET /platform/freshness`, enrichissement à chaque requête (~150 ms) |

## ETL / pipelines / qualité

| Critère | Niveau | Preuve |
|---------|--------|--------|
| Outils transformation métier | **OK** | `public_data_integrations.py`, formules accessibilité |
| Intégration multi-sources | **OK** | DVF, Paris, CDL, Filosofi, BAN |
| Structuration analyses | **OK** | Gold + Parquet + export |
| Perf transfert | **OK** | `integration_report`, métriques `total_sec` |
| Qualité données | **Partiel** | `data_quality` Silver, `_sources` |

---

## Endpoints clés pour le jury

```bash
curl http://localhost:8001/platform/freshness
curl http://localhost:8001/platform/governance
curl http://localhost:8001/platform/metrics
curl http://localhost:8001/bdd/relationnelle
curl http://localhost:8001/sql/accessibilite
python -m pytest tests/ -q
```

## Phrase batch + instant T

> Le batch Medallion dure environ **1 minute** pour rafraîchir le snapshot. L’**analyse à l’instant T** est assurée par l’API : à chaque requête, les indicateurs (accessibilité, loyers…) sont recalculés en **~150 ms** sur le Gold le plus récent ; Redis propage la fin du batch vers le cache API.
