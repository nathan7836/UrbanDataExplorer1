# Dashboard Immobilier Paris - Comparaison par Arrondissement

Dashboard web interactif avec carte choroplethe pour comparer les prix immobiliers et indicateurs par arrondissement a Paris.

## Fonctionnalites

- **Architecture Medallion** (Bronze -> Silver -> Gold)
- **API REST FastAPI** avec 15+ endpoints
- **Dashboard interactif** avec carte choroplethe MapLibre
- **11 indicateurs** : Prix/m2, Evolution, Logements sociaux, Loyers, Accessibilite, Tension locative, Pollution, Delits, Revenus, Densite, Vegetation, Transports
- **Export multi-formats** (CSV, Parquet, GeoJSON)
- **Pipeline batch** automatise (GitHub Actions)

## Installation

```bash
pip install -r requirements.txt
python pipeline.py
python run.py
```

Accedez au dashboard : http://localhost:8001/dashboard/

## Structure du projet

```
urban-data/
|-- api.py                      # API REST FastAPI (15+ endpoints)
|-- pipeline.py                 # Orchestration pipeline Bronze->Silver->Gold
|-- run.py                      # Point d'entree principal
|-- config.py                   # Configuration generale
|-- config_real_estate.py       # Configuration sources de donnees
|
|-- data/                       # Donnees (architecture Medallion)
|   |-- bronze/                 # Donnees brutes (API externes)
|   |-- silver/                 # Donnees nettoyees et validees
|   |-- gold/                   # Donnees enrichies (production)
|   |   |-- parquet/            # Export partitionne par annee
|   |-- export/                 # Tables exportees (CSV, Parquet, GeoJSON)
|
|-- dashboard/                  # Frontend web
|   |-- index.html              # Page principale
|   |-- config.js               # Configuration client
|   |-- static/
|       |-- css/style.css       # Styles
|       |-- js/app.js           # Application JavaScript
|       |-- js/paris_*.js       # Polygones arrondissements
|       |-- images/             # Assets graphiques
|
|-- ude_platform/               # Modules plateforme data
|   |-- config.py               # Variables d'environnement
|   |-- data_access.py          # Acces unifie aux donnees (SQL/JSON)
|   |-- enrichment.py           # Enrichissement metier
|   |-- freshness.py            # Fraicheur des donnees
|   |-- sync_databases.py       # Synchronisation PostgreSQL/MongoDB
|   |-- streaming.py            # Redis/Kafka streaming
|   |-- governance_catalog.py   # Catalogue de gouvernance
|   |-- api_security.py         # Securite API (rate limiting)
|
|-- database/                   # Scripts base de donnees
|   |-- init.sql                # Schema PostgreSQL
|   |-- migrate_governance.sql  # Migration gouvernance
|
|-- scripts/                    # Scripts utilitaires
|   |-- validate_rncp.py        # Validation competences RNCP
|   |-- sync_platform.py        # Synchronisation plateforme
|
|-- services/                   # Services background
|   |-- stream_consumer.py      # Consumer Redis
|   |-- kafka_consumer.py       # Consumer Kafka
|
|-- tests/                      # Tests unitaires
|   |-- test_enrichment.py
|   |-- test_data_access.py
|   |-- test_freshness.py
|
|-- .github/workflows/          # CI/CD
|   |-- pipeline-scheduled.yml  # Pipeline batch hebdomadaire
|
|-- docker-compose.yml          # Stack complete (PostgreSQL, MongoDB, Redis, Kafka, MinIO)
|-- Dockerfile                  # Image Docker API
|-- requirements.txt            # Dependances Python
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /arrondissements` | Liste complete avec donnees enrichies |
| `GET /prix?annee=2024` | Prix par annee |
| `GET /pollution` | Qualite de l'air par arrondissement |
| `GET /comparaison?arr1=1&arr2=6` | Comparaison entre 2 arrondissements |
| `GET /timeline?arr=6` | Evolution temporelle |
| `GET /health` | Etat des services |
| `GET /docs` | Documentation Swagger |

## Indicateurs

### Indicateurs principaux
- **Prix/m2** : Prix median au metre carre (DVF)
- **Logements sociaux** : Pourcentage de logements sociaux (RPLS)
- **Loyers** : Loyers de reference (encadrement Paris)

### Indicateurs avec formules
- **Accessibilite** : `(prix_m2 x 50) / (revenu_median / 12)` - Mois de revenu pour 50m2
- **Tension locative** : `(loyer_m2 x 50 x 12) / revenu_median x 100` - Part du revenu
- **Densite** : `population / superficie_km2`
- **Qualite de l'air** : `indice_Paris x f(densite, transports)` - Indice ATMO local

### Indicateurs personnalises
- **Pollution** : Indice Citeair (OpenData Paris / Airparif)
- **Delits** : Delinquance enregistree (data.gouv / SSMSI)
- **Revenus** : Revenu median des menages (Filosofi)
- **Vegetation** : Nombre d'arbres (OpenData Paris)
- **Transports** : Stations metro/RER (RATP)

## Sources de donnees

| Source | Donnees |
|--------|---------|
| DVF (data.gouv) | Transactions immobilieres |
| OpenData Paris | Loyers, vegetation, transports, qualite de l'air |
| SSMSI (data.gouv) | Delinquance communale |
| Filosofi (data.gouv) | Revenus des menages |
| RPLS | Logements sociaux |

## Pipeline batch

Le pipeline s'execute automatiquement chaque lundi a 6h (GitHub Actions) :

```bash
# Execution manuelle
python pipeline.py
```

Etapes :
1. **Bronze** : Collecte des donnees brutes (APIs externes)
2. **Silver** : Nettoyage et validation
3. **Gold** : Enrichissement et calcul des indicateurs
4. **Export** : Generation CSV, Parquet, GeoJSON

## Deploiement

### Local
```bash
python run.py
```

### Docker
```bash
docker compose up -d
```

### Production
Voir `render.yaml` et `Procfile` pour le deploiement cloud.

## Documentation projet

- [SYNTHESE_ECARTS.md](SYNTHESE_ECARTS.md) - Synthese des ecarts et checklist
- [VALIDATION_RNCP.md](VALIDATION_RNCP.md) - Validation des 8 competences RNCP
- [BDD_RELATIONNELLE.md](BDD_RELATIONNELLE.md) - Base de donnees SQL
- [BDD_NON_RELATIONNELLE.md](BDD_NON_RELATIONNELLE.md) - Base de donnees NoSQL
- [DATA_LAKE.md](DATA_LAKE.md) - Architecture Data Lake
- [RGPD.md](RGPD.md) - Conformite RGPD

## Licence

MIT License
