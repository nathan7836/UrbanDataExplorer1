# Urban Data Explorer — Rapport de Projet

**Dashboard immobilier Paris — comparaison par arrondissement**

*Rapport de validation des compétences data — juin 2026*

---

## Table des matières
Résumé Exécutif	
1.1 Objectifs et Périmètre	
1.2 Choix Techniques Principaux	
1.3 Résultats Clés	
Introduction et Contexte	
2.1 Contexte Urbain et Problématique Métier	
2.2 Cadre Théorique	
2.3 Objectifs Pédagogiques et Contraintes	
Analyse du Besoin Utilisateur	
3.1 Utilisateur Cible (Personas)	
3.2 Scénarios d’Usage	
3.3 Hypothèses et Contraintes Utilisateur	
Méthodologie de Travail et Gestion de Projet	
4.1 Méthodologie Adoptée	
4.2 Organisation et Outils Collaboratifs	
4.3 Planification, risques et limites	
Référentiel de Données	
5.1 Corpus et Sources de Données	
5.2 Modèle Conceptuel et Schéma de Données	
5.3 Stratégie de Traitement et Préparation des Données	
Pipeline Data et Architecture	
6.1 Vue d’Ensemble du Pipeline	
6.2 Étapes de Traitement Détaillées	
6.3 Qualité des données et traçabilité des sources
6.4 Données prêtes pour l'analyse et le Machine Learning
Implémentation Technique	
7.1 Stack Technologique	
7.2 API REST et couches d’accès aux données 
7.3 Synchronisation plateformes
7.4 Test, reproductibilité et documentation technique
Conception et Développement du Tableau de Bord	
8.1 Principes de conception UX et co-construction métier
8.2 Architecture du dashboard	
8.3 Choix des visualisations par indicateur
8.4 Accessibilité, lisibilité et transparence
Interactivité et Exploitation en Temps Réel	
9.1 Filtres, sélection et navigation	
9.2 Fonctionnalités avancées	
9.3 Rafraîchissement des données et fraîcheur du snapshot
9.4 Responsive design et aide à la décision
Analyse Territoriale et Insights Métier	
10.1 Méthodologie d’analyse et indicateurs statistiques retenus	
10.2 Résultats par thématique	
10.3 Exemples de comparaisons inter-arrondissements	
10.4 Alignement des insights avec les objectifs stratégiques	
Gouvernance, Conformité et Exploitation	
11.1 Architecture Data Lake et politique RGPD	
11.2 Catalogue, rôles d’accès et sécurité API	
11.3 Haute disponibilité, streaming et performance
11.4 Industrialisation et perspectives d’évolution
Conclusion	
12.1 Synthèse des Réalisations et auto évaluation	
12.2 Bilan des Compétences Acquises	
12.3 Pistes d’amélioration et ouverture
Annexes	


---

# Résumé Exécutif

**Urban Data Explorer** est un dashboard web interactif dédié à l'analyse comparative du marché immobilier et des indicateurs territoriaux sur les **20 arrondissements de Paris**. Le projet répond à un besoin croissant de transparence et d'aide à la décision pour les acteurs publics, les analystes immobiliers et les équipes data, confrontés à une dispersion des sources open data (DVF, OpenData Paris, Filosofi, délinquance, logements sociaux, etc.).

La solution repose sur une **architecture Medallion** (Bronze → Silver → Gold), une **API REST FastAPI** et un **tableau de bord cartographique** (MapLibre GL + Chart.js) exposant plus de **11 indicateurs** : prix au m², loyers, logements sociaux, accessibilité, tension locative, revenus, densité, pollution, délinquance, transports et santé de proximité.

Le pipeline automatise la collecte, le nettoyage, l'enrichissement et l'export multi-formats (JSON, CSV, Parquet, GeoJSON), avec synchronisation vers PostgreSQL et MongoDB. Le dashboard permet une exploration interactive : carte choroplèthe, filtres par année et indicateur, comparaison d'arrondissements, drill-down et visualisations analytiques en temps quasi réel.

Les principaux résultats montrent des **disparités marquées** entre arrondissements centraux et périphériques sur le prix, l'accessibilité au logement et la mixité sociale. Le projet valide les compétences en préparation des données, visualisation et analyse territoriale, dans un périmètre MVP assumé et documenté.

## 1.1 Objectifs et Périmètre

**Objectif général :** mettre à disposition un outil unifié permettant de comparer les dynamiques de logement et de qualité de vie entre les arrondissements parisiens, à partir de données publiques fiables et traçables.

**Objectifs spécifiques :**
- Collecter et agréger les sources open data pertinentes
- Transformer les données selon une architecture Medallion
- Exposer une API REST documentée et des exports analytiques
- Proposer un dashboard interactif orienté décision
- Documenter les sources, la qualité des données et la conformité RGPD

**Périmètre fonctionnel (MVP) :** 20 arrondissements, données 2018–2024 selon les indicateurs, 11 indicateurs cartographiques et 7 graphiques analytiques.

**Hors périmètre :** maille IRIS, modèle ML déployé, flux temps réel continu, couches végétation/transports entièrement réelles sur la carte.

## 1.2 Choix Techniques Principaux

Le backend s'appuie sur **Python 3.11+** (pandas, pyarrow, FastAPI, Uvicorn). Les données sont structurées en architecture **Medallion** avec persistance **PostgreSQL 16** (Gold relationnel), **MongoDB 7** (points géolocalisés), **Redis** (cache et streaming) et **MinIO** (lake objet, optionnel). Le frontend est une application web statique (HTML/CSS/JS) avec **MapLibre GL** et **Chart.js**. L'infrastructure est conteneurisée via **Docker Compose** et automatisée par **GitHub Actions**.

Le principe directeur est une **source de vérité analytique** en couche Gold, consommée par l'API, le dashboard et les exports BI.

## 1.3 Résultats Clés

- Pipeline opérationnel Bronze → Gold en ~1 minute, 20 arrondissements enrichis avec traçabilité `_sources`
- API avec 30+ endpoints, documentation OpenAPI, enrichissement à ~150 ms par requête
- Dashboard interactif : carte choroplèthe, 7 graphiques, mode comparaison, timeline animée
- Exports CSV, Parquet partitionné, GeoJSON prêts pour BI et ML
- 18 tests automatisés (API, enrichissement, SQL, gouvernance)
- Disparités territoriales documentées : prix, accessibilité (>200 mois de revenu pour 50 m² dans plusieurs arrondissements), mixité sociale (13e ~28 % vs 8e ~10 %)

---

# Introduction et Contexte

## 2.1 Contexte Urbain et Problématique Métier

Paris concentre des enjeux immobiliers majeurs : pression sur les prix, tension locative, inégalités territoriales en matière de logement social, de revenus et d'accès aux services. Les données utiles à l'analyse existent, mais elles sont dispersées entre de multiples portails (data.gouv.fr, OpenData Paris, Caisse des Dépôts) et présentent des formats hétérogènes.

Les acteurs concernés — élus, services urbanisme/logement, analystes, chercheurs — manquent souvent d'un outil unifié pour comparer rapidement deux arrondissements, suivre l'évolution temporelle, croiser immobilier et contexte socio-environnemental, et s'appuyer sur des données traçables.

Urban Data Explorer répond à cette problématique en centralisant la préparation des données et en les rendant explorables via une carte interactive et des visualisations analytiques, dans une logique de **data-driven policy**.

## 2.2 Cadre Théorique

**Open Data.** Le projet s'appuie exclusivement sur des données publiques ouvertes. Chaque indicateur conserve une trace de sa source, de sa date de mise à jour et de sa méthode de calcul.

**Architecture Medallion.** Le lac de données est structuré en trois zones :
- **Bronze** — données brutes telles que collectées (`data/bronze/`)
- **Silver** — données nettoyées, dédupliquées, validées (`data/silver/`)
- **Gold** — données enrichies, prêtes pour la consommation (`data/gold/`)

Ce modèle sépare ingestion, qualité et enrichissement métier. Il facilite l'audit et la reprise sur erreur.

**Gouvernance des données.** Catalogue (`/platform/governance`), rôles d'accès différenciés (`ude_admin` / `ude_reader`), politique RGPD documentée, suivi de la fraîcheur des snapshots (`/platform/freshness`).

## 2.3 Objectifs Pédagogiques et Contraintes

Le projet vise la validation de compétences en trois blocs :

- **Préparation des données (C1–C4)** — transformation, qualité, documentation, données prêtes pour ML
- **Visualisation (C1–C4)** — dashboard informatif, interactif, fonctionnalités avancées, responsive
- **Analyse (C1–C3)** — techniques statistiques adaptées, insights métier, démarche documentée

**Contraintes du MVP :** délai de réalisation (maille arrondissement), disponibilité partielle des sources (INSEE non souscrit, loyers = encadrement), ressources infra limitées (MinIO/Kafka optionnels), accessibilité WCAG partielle, pas de flux DVF continu.

Ces contraintes sont assumées et visibles dans `SYNTHESE_ECARTS.md` et le panneau « Limites du périmètre » du dashboard.

---

# Analyse du Besoin Utilisateur

## 3.1 Utilisateur Cible (Personas)

**Claire — chargée d'études en collectivité (32 ans).** Maîtrise Excel, peu de code. Veut comparer son arrondissement aux autres et préparer des notes pour élus. Frustration : données éparpillées. Besoins : carte lisible, comparaison A vs B, export, indicateurs documentés.

**Thomas — data analyst en agence immobilière (28 ans).** SQL, Python, API REST. Veut croiser prix, revenus, typologie et alimenter des rapports clients. Besoins : API documentée, fraîcheur des données, exports CSV/Parquet.

**Sophie — journaliste / citoyenne informée (40 ans).** Lecture de graphiques, pas d'expertise technique. Veut comprendre les inégalités territoriales. Besoins : interface intuitive, codes couleur explicites, transparence sur les sources et limites.

Ces trois profils ont orienté le découpage du dashboard : carte + sidebar pour l'exploration grand public, API + exports pour l'analyste, documentation intégrée pour la crédibilité.

## 3.2 Scénarios d'Usage

**Comparaison d'accessibilité (Claire).** Sélection de l'indicateur Accessibilité, ouverture du mode Comparer (6e vs 18e), lecture du graphique achat vs location, consultation des limites méthodologiques. Résultat : éléments chiffrés pour une note en quelques minutes.

**Suivi de tendance prix (Thomas).** Filtre année 2022, timeline animée, clic sur le 15e arrondissement, appel API `/timeline?arr=15`, export CSV. Résultat : croisement visuel et programmatique.

**Exploration qualité de vie (Sophie).** Parcours des indicateurs Environnement et Santé, activation pollution et santé de proximité, lecture du radar multi-dimensionnel, vérification des limites affichées.

**Vérification fraîcheur (Thomas / admin).** Lecture de la bannière « Analyse à l'instant T », appel `/platform/freshness` et `/health`.

## 3.3 Hypothèses et Contraintes Utilisateur

**Hypothèses de conception :** l'utilisateur connaît la découpe par arrondissements ; la comparaison visuelle prime sur les tableaux ; les non-techniques n'utilisent pas l'API ; les analystes ont besoin d'exports ; la transparence sur les limites renforce la confiance.

**Contraintes ergonomiques :** prise en main sans formation, temps de chargement acceptable (overlay, cache), lisibilité (contrastes, légende), accessibilité partielle (ARIA, clavier).

**Contraintes métier :** granularité arrondissement uniquement, loyers = encadrement Paris, comparaison limitée à 2 arrondissements, historique 2022–2024 dans le dashboard.

**Contraintes techniques :** connexion API requise, navigateur moderne, pas d'authentification en MVP.

---

# Méthodologie de Travail et Gestion de Projet

## 4.1 Méthodologie Adoptée

Le projet suit une approche **itérative centrée sur le MVP** :

1. Pipeline Bronze + collecte DVF
2. Silver / Gold + normalisation
3. API FastAPI + exports
4. Dashboard cartographique
5. Plateforme (Postgres, Mongo, Redis)
6. CI/CD + documentation

Chaque itération se termine par une validation : pipeline, endpoints, dashboard.

**Validation continue :** tests pytest, `python pipeline.py`, `curl /health`, script `validate_rncp.py`, démo `demo.ps1`.

**Principes directeurs :** données d'abord, traçabilité, transparence des limites, reproductibilité, pas de sur-ingénierie (YAGNI).

## 4.2 Organisation et Outils Collaboratifs

Quatre axes parallèles : Data Engineering (`pipeline.py`, `data/`), Backend (`api.py`, `ude_platform/`), Frontend (`dashboard/`), DevOps/Doc (`.github/workflows/`, documentation Markdown).

Outils : Git/GitHub, GitHub Actions, Python, Docker Compose, FastAPI/Swagger, pytest, Render/Railway/GitHub Pages pour le déploiement.

**Workflows automatisés :**
- Pipeline hebdomadaire (lundi 6h) — `pipeline-scheduled.yml`
- Déploiement dashboard sur push `main` — `deploy.yml`

## 4.3 Planification, Risques et Limites Assumées

**Planning indicatif :** cadrage (1 sem.), pipeline (2–3 sem.), API+BDD (2 sem.), dashboard (2–3 sem.), plateforme+CI (1–2 sem.), documentation (1–2 sem.).

**Risques principaux et mitigations :**
- Indisponibilité API open data → cache `raw_cache/`, retry
- Formats hétérogènes → `data_normalization.py`
- INSEE absent → Filosofi, DVF en alternative
- Docker complexe → mode dégradé API + JSON Gold
- Données obsolètes → pipeline hebdomadaire + affichage fraîcheur

**Limites assumées :** maille IRIS, loyers encadrement, logements sociaux calibrés, INSEE, végétation/transports simulés, pas de ML déployé, auth optionnelle, WCAG partiel. Documentées dans `SYNTHESE_ECARTS.md`.

---

# Référentiel de Données

## 5.1 Corpus et Sources de Données

Toutes les données proviennent de **sources publiques ouvertes**. La clé de jointure territoriale est le code INSEE arrondissement (75101–75120).

| Source | Données | Format |
|--------|---------|--------|
| DVF (data.gouv) | Transactions, prix/m², typologie | CSV.gz |
| Filosofi (data.gouv) | Revenus médians ménages | CSV |
| Délinquance (SSMSI) | Faits délictuels communaux | Parquet |
| OpenData Paris | Loyers encadrement, logements sociaux, air | API CSV |
| Caisse des Dépôts | Logements sociaux par commune | CSV |
| BAN / Nominatim | Géocodage adresses DVF | API + cache |
| Référentiels agrégés | Santé de proximité, transports (carte) | JS statique |

**Couverture :** 20 arrondissements, ~74 700 points DVF géocodés, séries 2018–2024 selon indicateurs.

Chaque arrondissement porte un bloc `_sources` (provider, dataset, status, fetched_at, url). Un `integration_report` global synthétise le statut de chaque source (`ok`, `skipped`).

**Sources en repli :** INSEE/Melodi → Filosofi + DVF ; RPLS ventilé → taux 2024 + série calibrée ; marché locatif complet → encadrement Paris uniquement.

## 5.2 Modèle Conceptuel et Schéma de Données

L'**arrondissement** est l'entité centrale, enrichie par indicateurs thématiques et séries temporelles (prix, logements sociaux, revenus, environnement, santé, transports).

**PostgreSQL** — modèle relationnel normalisé :
- `arrondissements` (référentiel)
- `prix_annuel` (faits temporels)
- `indicateurs_arrondissement` (attributs socio-éco, JSON typologie)
- Vues métier : `v_prix_par_annee`, `v_indicateurs_complets`, `v_accessibilite_prix_revenu`
- Gouvernance : `governance_access`, `pipeline_runs`, `integration_report`
- Rôle `ude_reader` : SELECT uniquement

**MongoDB** — collection `geo_points` : documents GeoJSON (transactions DVF, adresses géocodées), index `2dsphere`. Le Gold agrégé n'est pas stocké en Mongo.

**Gold JSON** — source de vérité analytique du MVP : blocs `statistiques`, `evolution_annuelle`, `accessibilite_logement`, `typologie`, `_sources`, `data_quality`, etc.

**Exports :** CSV aplati, Parquet partitionné `annee=YYYY/`, GeoJSON.

## 5.3 Stratégie de Traitement et Préparation des Données

**Bronze :** collecte multi-sources, cache `raw_cache/`, fusion par code INSEE, géocodage BAN.

**Silver :** déduplication, validation types, bornes (prix 1 000–50 000 €/m², surface 9–500 m²), politique NA documentée, bloc `data_quality`.

**Gold :** enrichissement métier (accessibilité, tension locative, pollution locale, évolution logements sociaux).

**Export et sync :** CSV/Parquet/GeoJSON, sync Postgres + Mongo, copie MinIO optionnelle.

**Orchestration :** `python pipeline.py` (manuel) ou GitHub Actions (hebdomadaire).

---

# Pipeline Data et Architecture

## 6.1 Vue d'Ensemble du Pipeline

```
Sources open data → BRONZE → SILVER → GOLD → API / Dashboard / Exports
                                      ↓
                            PostgreSQL + MongoDB + Parquet
```

Commande unique : `python pipeline.py` (~1 minute).

| Étape | Module | Sortie |
|-------|--------|--------|
| Collecte | `RealEstateDataFetcher` | `data/bronze/` |
| Transformation | `DataProcessor` | `data/silver/`, `data/gold/` |
| Export | `TableExporter` | `data/export/` |
| Finalisation | `finalize_pipeline()` | Parquet, sync BDD, Redis |

## 6.2 Étapes de Traitement Détaillées

**Ingestion (Bronze) :** téléchargement DVF département 75, APIs OpenData et data.gouv, géocodage BAN/Nominatim, fusion par arrondissement.

**Nettoyage (Silver) :** validation territoire, normalisation dates/prix/surfaces, déduplication, bornage pourcentages, métadonnées qualité.

**Enrichissement (Gold) :** statistiques prix (médiane, min, max, évolution %), accessibilité `(prix_m² × 50) / (revenu/12)`, tension locative, densité, pollution locale ajustée, loyer estimé si absent.

**Export :** tables prix par année, fusion socio-éco, GeoJSON ; Parquet partitionné Hive-style.

L'API recalcule l'enrichissement à chaque requête via `enrich_all()` pour cohérence avec l'année sélectionnée.

## 6.3 Qualité des Données et Traçabilité des Sources

Politique NA (`data_normalization.py`) :
- Champs obligatoires (date, prix) → exclusion
- Champs optionnels → `null` explicite
- Numériques invalides → exclusion

Bloc `data_quality` par arrondissement : champs manquants, imputés, horodatage.

Traçabilité à trois niveaux : `_sources` par indicateur, `integration_report` global, tables `integration_report` et `pipeline_runs` en PostgreSQL.

Fraîcheur : événement Redis `pipeline.completed`, invalidation cache API, bannière utilisateur.

## 6.4 Données Prêtes pour l'Analyse et le Machine Learning

**Critères ML-ready :** grain stable (arrondissement ou arr × année), types normalisés, features dérivées pré-calculées, séries temporelles partitionnées, traçabilité, formats standards (CSV, Parquet, JSON).

**Fichiers exploitables :**
- `data/export/donnees_fusionnees_latest.csv` — régression, clustering
- `data/gold/parquet/prix_annuel/` — séries temporelles, forecasting
- `real_estate_data_gold_latest.json` — notebooks Python
- Vue SQL `v_accessibilite_prix_revenu` — analyse directe

**Pistes ML (hors MVP) :** prédiction prix/m² (Random Forest), clustering territorial (K-Means), détection d'anomalies sur séries prix.

Le MVP fournit des données et du feature engineering documentés ; aucun modèle n'est déployé.

---

# Implémentation Technique

Cette partie décrit la stack technologique, l'API REST, la synchronisation multi-plateformes et les mécanismes de test et documentation qui rendent Urban Data Explorer déployable et maintenable.

## 7.1 Stack Technologique

### Vue d'ensemble

Le projet adopte une architecture **modulaire en couches**, séparant la préparation des données, l'exposition API et la visualisation frontend.

```
┌──────────────────────────────────────────────────────────────┐
│  FRONTEND          Dashboard HTML/CSS/JS + MapLibre + Chart.js │
├──────────────────────────────────────────────────────────────┤
│  API               FastAPI + Uvicorn (port 8001)             │
├──────────────────────────────────────────────────────────────┤
│  PLATEFORME        ude_platform/ (enrichment, sync, security)│
├──────────────────────────────────────────────────────────────┤
│  PIPELINE          pipeline.py, data_processor.py, exports   │
├──────────────────────────────────────────────────────────────┤
│  STOCKAGE          PostgreSQL │ MongoDB │ Redis │ MinIO      │
├──────────────────────────────────────────────────────────────┤
│  INFRA             Docker Compose │ nginx │ GitHub Actions    │
└──────────────────────────────────────────────────────────────┘
```

### Backend — Python

Le cœur applicatif repose sur **Python 3.11+**. Les bibliothèques principales sont : **pandas** et **pyarrow** pour la manipulation tabulaire et l'export Parquet partitionné ; **requests** pour la collecte open data ; **psycopg2-binary** et **pymongo** pour les connexions PostgreSQL et MongoDB ; **redis** et **kafka-python** pour le streaming d'événements ; **minio** pour la copie objet du Data Lake (optionnel en local).

### API — FastAPI

L'exposition des données passe par **FastAPI** (validation Pydantic, documentation OpenAPI automatique), servie par **Uvicorn** en mode ASGI. Les tests utilisent **httpx** ; la configuration est externalisée via **python-dotenv**. La documentation interactive est accessible sur `http://localhost:8001/docs`.

### Bases de données et frontend

Côté persistance : **PostgreSQL 16** pour le Gold relationnel et les vues métier, **MongoDB 7** pour les points géolocalisés DVF (`geo_points`, index `2dsphere`), **Redis 7** pour les streams et l'invalidation du cache API, **MinIO** pour archiver les zones Medallion.

Le frontend est une application web statique sans framework lourd : **HTML5/CSS3**, **JavaScript vanilla**, **MapLibre GL JS 3.6** pour la carte choroplèthe et **Chart.js 4.4** pour les graphiques (barres, courbes, donut, radar). La typographie **DM Sans** assure une bonne lisibilité.

### Infrastructure et configuration

L'infrastructure locale est orchestrée par **Docker Compose** (10 services). En production, **nginx** répartit la charge entre deux instances API (`least_conn`). **GitHub Actions** automatise le pipeline hebdomadaire et le déploiement du dashboard sur Pages. L'API peut être déployée sur **Render** ou **Railway** ; le dashboard sur **GitHub Pages** ou **Netlify**.

Toutes les variables d'environnement sont centralisées dans `ude_platform/config.py` et `.env.example`. Le mode `DATA_BACKEND=auto` tente PostgreSQL en priorité, puis retombe sur le fichier Gold JSON — ce qui permet de faire tourner l'API **sans Docker** en local.

## 7.2 API REST et Couches d'Accès aux Données

### Architecture de l'API

L'API (`api.py`) expose **plus de 30 endpoints** regroupés en six familles :

- **Santé / plateforme** — `/health`, `/platform/freshness`, `/platform/metrics` : état des services et fraîcheur des données
- **Données métier** — `/arrondissements`, `/prix`, `/comparaison`, `/timeline` : consultation et analyse territoriale
- **Indicateurs thématiques** — `/pollution`, `/delits`, `/revenus`, `/accessibilite`… : accès par domaine
- **SQL** — `/sql/accessibilite`, `/sql/vues` : requêtes métier PostgreSQL
- **MongoDB** — `/mongo/geo-points`, `/mongo/metadata` : points géolocalisés
- **Gouvernance** — `/platform/governance`, `/bdd/relationnelle` : catalogue, quotas, fiches compétences

### Couche d'accès unifiée

Le module `ude_platform/data_access.py` abstrait la source de données selon le flux suivant :

```
Requête API
    │
    ▼
load_gold_data()  ──►  DATA_BACKEND=auto
    │                      │
    │              ┌───────┴───────┐
    │              ▼               ▼
    │         PostgreSQL      Gold JSON
    │         (ude_reader)    (fichier local)
    │
    ▼
_merge_json_supplements()  ──►  végétation, transports, loyers…
    │
    ▼
enrich_all()  ──►  accessibilité, loyers, pollution locale
    │
    ▼
attach_response_meta()  ──►  fraîcheur, latence, version cache
```

Cette architecture garantit que le dashboard reçoit **toujours des données enrichies**, quelle que soit la source sous-jacente.

### Sécurité et enrichissement

Le module `ude_platform/api_security.py` implémente une clé API optionnelle (header `X-API-Key`), un rate limiting global (100 req/min/IP, 500 req/jour), des quotas spécifiques par type d'endpoint (exports : 5/min, geo-points : 10/min) et des headers de quota (`X-RateLimit-*`). Les chemins `/health`, `/docs` et `/platform/freshness` restent publics.

Chaque requête `/arrondissements` déclenche le chargement Gold, la fusion des suppléments JSON, l'enrichissement métier et l'attachement des métadonnées de fraîcheur. La latence typique est d'environ **150 ms** pour 20 arrondissements enrichis.

**Exemples d'appels :**

```bash
curl "http://localhost:8001/arrondissements?annee=2024"
curl "http://localhost:8001/comparaison?arr1=6&arr2=18"
curl "http://localhost:8001/mongo/geo-points?arrondissement=6&limit=50"
curl "http://localhost:8001/sql/accessibilite"
curl "http://localhost:8001/health"
```

### Haute disponibilité (Docker)

En production Docker, nginx distribue la charge entre deux instances API :

```nginx
upstream api_backend {
    least_conn;
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
}
```

Les healthchecks Docker sur chaque replica garantissent la continuité de service.

## 7.3 Synchronisation Plateformes

### Objectif et flux

Après chaque exécution du pipeline, les données Gold sont répliquées vers les systèmes de consommation :

```
Gold JSON
    │
    ├──► sync_postgres()           → arrondissements, prix_annuel, indicateurs
    ├──► sync_mongo_geo_points()   → collection geo_points (Bronze DVF)
    ├──► export_prix_partitioned() → Parquet annee=YYYY/
    ├──► TableExporter.export_all() → CSV, GeoJSON
    └──► sync_lake_to_minio()      → bucket ude-lake (optionnel)
```

### PostgreSQL et MongoDB

Le module `ude_platform/sync_databases.py` charge le Gold dans PostgreSQL : UPSERT sur `arrondissements` et `indicateurs_arrondissement`, remplacement des lignes `prix_annuel` par arrondissement, insertion d'un nouveau `integration_report` et des métriques dans `pipeline_runs`.

```bash
python scripts/sync_platform.py
# ou : curl -X POST http://localhost:8001/platform/sync
```

MongoDB, via `ude_platform/geo_points.py`, lit les CSV DVF bruts (`raw_cache/dvf_75_*.csv.gz`) et le cache géocodage, puis insère des documents GeoJSON dans `geo_points` (index `2dsphere`). Le Gold agrégé n'est **pas** stocké en Mongo — séparation claire SQL vs NoSQL.

### Streaming et modes de déploiement

Après synchronisation, `finalize_pipeline()` publie un événement `pipeline.completed` sur **Redis Streams** (consumer `stream_consumer.py`) et sur **Kafka** (`ude.pipeline.events`). L'API écoute Redis pour invalider son cache mémoire.

Quatre modes de déploiement sont possibles :

| Mode | Commande | Services actifs |
|------|----------|-----------------|
| Minimal | `python api.py` | API + Gold JSON |
| Local complet | `docker compose up -d postgres mongo` + sync | API + SQL + Mongo |
| Stack complète | `docker compose up -d` | 10 containers |
| Cloud | Render/Railway + GitHub Pages | API distante + dashboard statique |

## 7.4 Tests, Reproductibilité et Documentation Technique

### Stratégie de tests

Le projet comporte **18 tests automatisés** répartis en six fichiers : `test_api.py` (4), `test_enrichment.py` (5), `test_data_access.py` (1), `test_freshness.py` (4), `test_kafka.py` (2), `test_load_sql.py` (2).

```bash
python -m pytest tests/ -q
# Résultat attendu : 18 passed
```

Le fichier `test_load_sql.py` exécute **50 requêtes consécutives** sur la vue `v_accessibilite_prix_revenu` pour valider l'intégrité des données, l'absence d'erreur sous charge légère et le respect du rôle lecture seule `ude_reader`.

### Reproductibilité

La reproductibilité repose sur une chaîne d'artefacts documentés : `requirements.txt` et `Dockerfile` pour l'environnement, `.env.example` pour la configuration, `python pipeline.py` comme commande unique de génération des données, `scripts/demo.ps1` pour la démo soutenance, `scripts/validate_rncp.py` pour la vérification des artefacts, et GitHub Actions pour le pipeline planifié.

**Séquence de démo :**

```bash
pip install -r requirements.txt
python pipeline.py
docker compose up -d postgres mongo
python scripts/sync_platform.py
python api.py
# Dashboard : http://localhost:8001/dashboard/
```

### Documentation et observabilité

La documentation technique couvre l'ensemble du projet : `README.md` (installation, endpoints), `DATA_LAKE.md` (Medallion), `BDD_RELATIONNELLE.md` et `BDD_NON_RELATIONNELLE.md` (schémas SQL et Mongo), `RGPD.md`, `VALIDATION_RNCP.md`, `SYNTHESE_ECARTS.md`, `GRILLE_RNCP.md`, `DEPLOIEMENT.md`, et l'OpenAPI interactive sur `/docs`.

L'observabilité s'appuie sur des logs horodatés dans le pipeline, la latence exposée dans les métadonnées API, les métriques dans `pipeline_runs.metrics_json` (`GET /platform/metrics`), l'état des services via `GET /health` et la fraîcheur via `GET /platform/freshness`.

### Limites de la couverture

Les chemins critiques (API, enrichissement, SQL, gouvernance) sont automatisés. En revanche, le pipeline ETL complet et les exports CSV/Parquet ne sont validés qu'en manuel ; le dashboard repose sur des tests manuels et un audit WCAG non exhaustif ; la résilience HA est assurée par des healthchecks Docker sans tests de chaos formels. Ces limites sont documentées dans `SYNTHESE_ECARTS.md` et constituent des axes d'évolution (P1–P3).

---

# Conception et Développement du Tableau de Bord

## 8.1 Principes de conception UX et co-construction métier

Trois principes guident le dashboard :

1. **Clarté** — un indicateur actif sur la carte, approfondissement via sidebar et graphiques
2. **Transparence** — badge « formule », panneau explicatif, limites du MVP visibles
3. **Orientation décision** — codes couleur sémantiques, unités parlantes (mois de revenu)

Les 11 indicateurs sont regroupés en quatre familles (Immobilier, Socio-économique, Environnement, Santé), alignés sur les personas du chapitre 3.

## 8.2 Architecture du dashboard

Application web statique en trois zones :

- **Header** — année, comparer, thème, fraîcheur
- **Sidebar** — stats globales, indicateurs, détail arrondissement, limites
- **Zone principale** — carte MapLibre + 7 graphiques Chart.js

Flux : appel API parallèle + ressources statiques (GeoJSON, sante_data.js). Cache navigateur `DataCache`. Contrôles carte : Points DVF, Timeline, guide de lecture.

## 8.3 Choix des visualisations par indicateur

- **Carte choroplèthe** — comparaison spatiale (tous indicateurs)
- **Courbe** — évolution des prix ; logements sociaux 2018–2024
- **Barres** — classement par arrondissement ; accessibilité achat vs location ; transports
- **Donut** — typologie logements (Studio–T5+)
- **Radar** — santé de proximité (7 dimensions)

Technologies : Chart.js 4, MapLibre GL 3.6 — open source, sans licence propriétaire.

## 8.4 Accessibilité, lisibilité et transparence

Thème sombre par défaut, clair disponible. Typographie DM Sans. Indicateurs focusables (ARIA, clavier flèches). Panneau limites : maille, loyers, INSEE, données simulées. Overlay de chargement pour la performance perçue. Audit WCAG complet hors périmètre MVP.

---

# Interactivité et Exploitation en Temps Réel

## 9.1 Filtres, sélection et navigation

Le dashboard propose plusieurs leviers d'exploration :

- **Sélecteur d'année** (2022–2024) — recharge carte, stats et graphiques via `loadData()`
- **Liste d'indicateurs** — 11 choix exclusifs, mise à jour carte + légende + panneau formule
- **Clic / survol arrondissement** — tooltip au survol, sélection au clic avec flyTo cartographique
- **Navigation clavier** — flèches pour changer d'indicateur sans souris

La sélection d'un arrondissement déclenche `selectArrondissement()` : mise à jour du panneau détail, des 7 graphiques et optionnellement de la couche points DVF.

## 9.2 Fonctionnalités avancées

**Mode Comparer** — sélection de deux arrondissements, appel API `/comparaison`, affichage cartes côte à côte (prix, accessibilité, indicateurs clés).

**Drill-down** — carte → clic → détail arrondissement + graphiques contextuels. Équivalent fonctionnel au drill-down BI classique.

**Timeline animée** — bouton « Timeline » : défilement automatique des années toutes les 2 secondes, mise à jour carte et stats.

**Couches géographiques** — toggle « Points DVF » charge `/mongo/geo-points` avec filtre bbox ; marqueurs transports sur indicateur dédié.

**Panneau formules** — pour chaque indicateur calculé : titre, formule, unité, note méthodologique (`INDICATOR_FORMULAS` dans `app.js`).

## 9.3 Rafraîchissement des données et fraîcheur du snapshot

Le dashboard n'est pas alimenté par un flux continu mais par un **snapshot Gold** rafraîchi par le pipeline batch (hebdomadaire en CI, manuel en local).

À chaque requête API :
- enrichissement recalculé (~150 ms)
- métadonnées fraîcheur attachées (âge snapshot, latence, version cache)
- invalidation cache Redis après `pipeline.completed`

Affichage utilisateur : *« Analyse à l'instant T — snapshot il y a X · requête Y ms · cache vZ »*.

Endpoints de contrôle : `/platform/freshness`, `/health`.

## 9.4 Responsive design et aide à la décision

**Responsive** (`style.css`, breakpoint 1024 px) : sidebar empilée, carte 460 px, grille graphiques en colonne unique, header adaptatif.

**Aide à la décision :**
- Vue d'ensemble : prix médian Paris + variation annuelle
- Comparaison immédiate entre territoires
- Accessibilité en mois de revenu (actionnable pour politique logement)
- Score santé radar pour aménagement des services
- Exports pour analyses complémentaires

---

# Analyse Territoriale et Insights Métier

## 10.1 Méthodologie d'analyse et indicateurs statistiques retenus

Les analyses s'appuient sur des **statistiques robustes et des ratios normalisés** adaptés aux données immobilières et territoriales :

- **Médiane** pour les prix/m² (résistance aux valeurs extrêmes DVF)
- **Agrégation temporelle** annuelle (2018–2024)
- **Ratios** — densité, pharmacies/10 000 hab., accessibilité en mois de revenu
- **Scores composites pondérés** — santé de proximité, pollution locale
- **Variation %** — évolution prix, tension locative
- **Jointure multi-sources** par code INSEE

Outils : pandas (pipeline), SQL (vues PostgreSQL), enrichissement Python (`enrichment.py`), tests de charge SQL (50 requêtes sur `v_accessibilite_prix_revenu`).

## 10.2 Résultats par thématique

**Immobilier.** Les arrondissements centraux (1er–8e) affichent des prix médians nettement supérieurs aux arrondissements du nord-est (18e–20e). Sur la période 2022–2024, une tendance à la baisse modérée est observable sur plusieurs territoires (ex. 1er : ~13 080 → ~12 450 €/m²).

**Accessibilité.** Plusieurs arrondissements dépassent **200 mois de revenu médian** pour financer 50 m² à l'achat (ex. 1er ~213 mois, 3e ~202 mois). La tension locative varie selon le couple loyer/revenu local.

**Logements sociaux.** Forte hétérogénéité : 13e (~28,5 %) et 20e (~26,1 %) vs 8e (~10,5 %) et 16e (~9,8 %). L'évolution 2018–2024 montre une progression générale des taux.

**Socio-économie.** Revenus médians (Filosofi) et densité structurent les contrastes entre ouest parisien et nord-est. La délinquance et la pollution complètent le portrait territorial.

**Environnement et santé.** L'indice air local varie selon densité et transports. Le score santé de proximité met en évidence des forces (densité pharmacies, médecins dans l'ouest) et faiblesses (temps d'accès urgences) selon les territoires.

## 10.3 Exemples de comparaisons inter-arrondissements

**1er vs 13e (prix et mixité).** Le 1er combine prix élevé (~13 000 €/m²) et faible taux de logements sociaux (~14 %). Le 13e présente un prix plus modéré et un taux de logements sociaux parmi les plus élevés (~28,5 %). Insight : deux modèles territoriaux opposés en termes de mixité et de pression immobilière.

**6e vs 18e (accessibilité et cadre de vie).** Le 6e reste cher avec une accessibilité contrainte mais un cadre central prisé. Le 18e combine prix plus bas et indicateurs de tension sociale plus marqués (logements sociaux, délinquance). Insight : le « prix bas » ne signifie pas « accessible » si les revenus locaux sont plus faibles.

Ces comparaisons sont reproductibles via le mode Comparer du dashboard ou `GET /comparaison?arr1=1&arr2=13`.

## 10.4 Alignement des insights avec les objectifs stratégiques

| Objectif stratégique | Insight produit | Indicateur clé |
|---------------------|-----------------|----------------|
| Politique du logement | Territoires sous forte tension d'accessibilité | Mois de revenu pour 50 m² |
| Mixité sociale | Écarts importants entre arrondissements | Logements sociaux % |
| Qualité de vie | Pollution et santé variables | Indice air, score santé |
| Veille immobilière | Évolution prix 2022–2024 | Évolution annuelle |
| Décision éclairée | Comparaison multi-dimensionnelle | Mode Comparer |

Les analyses répondent à la mission initiale : **éclairer les décisions par des indicateurs reproductibles** plutôt que par des intuitions.

---

# Gouvernance, Conformité et Exploitation

## 11.1 Architecture Data Lake et politique RGPD

Architecture Medallion documentée dans `DATA_LAKE.md` :

```
Sources → Bronze → Silver → Gold → Export
                          ↓
                PostgreSQL + MongoDB → API → Dashboard
```

Copie objet optionnelle : bucket MinIO `ude-lake`.

**RGPD** (`RGPD.md`) :
- Données agrégées par arrondissement, **pas de données personnelles** en Gold
- Géocodage : adresses utilisées pour centroïdes, pas stockées en clair en Gold
- Licences open data des producteurs
- Minimisation, rôles d'accès, `.env` non versionné
- Rétention : cache Bronze 14–30 jours, snapshots horodatés

## 11.2 Catalogue, rôles d'accès et sécurité API

**Catalogue** — `GET /platform/governance` et vue SQL `v_catalogue_donnees` listent les objets accessibles.

**Rôles PostgreSQL :**
- `ude_admin` — écriture pipeline, sync Gold
- `ude_reader` — SELECT uniquement sur tables et vues (client, API, BI)

**Sécurité API :**
- Clé `UDE_API_KEY` optionnelle (header `X-API-Key`)
- Rate limiting par IP et par endpoint
- Headers de quota exposés au client
- Chemins publics : `/health`, `/docs`, `/platform/freshness`

## 11.3 Haute disponibilité, streaming et performance

**HA :** deux instances API (`api1`, `api2`) derrière nginx (`least_conn`), healthchecks Docker, endpoint `/health`.

**Streaming :** Redis Streams (`pipeline.completed`) et Kafka (`ude.pipeline.events`) notifient la fin du batch. Consumers : `stream_consumer.py`, `kafka_consumer.py`.

**Performance :**
- Pipeline batch ~1 min ; transformation seule ~0,2 s
- Enrichissement API ~150 ms/requête
- Cache mémoire API + invalidation Redis
- Parquet partitionné pour lectures analytiques
- Métriques : `GET /platform/metrics`, `pipeline_runs.metrics_json`

## 11.4 Industrialisation et perspectives d'évolution

**État actuel :** MVP fonctionnel, documenté, déployable (local, Docker, cloud), CI pipeline hebdomadaire, 18 tests automatisés.

**Perspectives :**
- Maille IRIS / quartiers
- Sources INSEE/Melodi officielles
- Modèle ML prédictif prix/m²
- Flux DVF temps réel
- Audit WCAG complet
- Auth API obligatoire en production
- Tuiles vectorielles (Martin/tippecanoe)
- `SOURCES.md` formel

---

# Conclusion

## 12.1 Synthèse des Réalisations et auto-évaluation

Urban Data Explorer livre une **plateforme data complète** autour d'un cas d'usage concret : comparer les dynamiques de logement et de qualité de vie à Paris.

**Réalisations principales :**
- Pipeline Medallion opérationnel et documenté
- 20 arrondissements enrichis, 11 indicateurs, traçabilité complète
- API REST 30+ endpoints, mode dégradé sans Docker
- Dashboard interactif responsive
- Stack plateforme (Postgres, Mongo, Redis, Kafka, MinIO)
- 18 tests, CI/CD, documentation RNCP

**Auto-évaluation compétences :**

| Bloc | Niveau | Commentaire |
|------|--------|-------------|
| Préparation données C1–C4 | Validé | Pipeline, qualité, docs, exports ML-ready |
| Visualisation C1–C4 | Validé | Dashboard informatif, interactif, drill-down, responsive |
| Analyse C1–C3 | Validé | Stats adaptées, insights territoriaux, démarche documentée |
| Compétences RNCP infra | Partiel à validé | HA, streaming OK ; chaos test et WCAG partiels |

Couverture globale estimée : **~90–95 %** du référentiel visé (`SYNTHESE_ECARTS.md`).

## 12.2 Bilan des Compétences Acquises

**Data Engineering :** architecture Medallion, normalisation multi-sources, politique qualité, exports Parquet.

**Développement :** API FastAPI, couche d'accès unifiée, tests automatisés, Docker Compose.

**Visualisation :** cartographie choroplèthe, choix de graphiques par message, UX orientée décision.

**Analyse :** indicateurs dérivés, comparaisons territoriales, interprétation métier.

**Gouvernance :** RGPD, rôles SQL, catalogue, fraîcheur, limites assumées.

**DevOps :** GitHub Actions, déploiement cloud, reproductibilité (`demo.ps1`).

## 12.3 Pistes d'amélioration et ouverture

Les limites du MVP sont connues et documentées — elles constituent des axes d'évolution crédibles plutôt que des angles morts.

À court terme : audit accessibilité WCAG, tests d'intégration pipeline, `SOURCES.md` formel.

À moyen terme : maille IRIS, connexion INSEE, modèle prédictif prix, authentification API.

À long terme : plateforme de veille territoriale multi-villes, flux temps réel, industrialisation MinIO en production.

Le projet démontre qu'une **chaîne data complète** — de la collecte open data à la visualisation interactive — peut être construite de manière reproductible, transparente et orientée décision, même dans un périmètre MVP contraint.

---

# Annexes

## Annexe A — Commandes de déploiement et démonstration

```bash
# Installation
pip install -r requirements.txt

# Pipeline complet
python pipeline.py

# Stack locale (Postgres + Mongo)
docker compose up -d postgres mongo
python scripts/sync_platform.py

# API
python api.py
# Dashboard : http://localhost:8001/dashboard/

# Vérifications
curl http://localhost:8001/health
curl http://localhost:8001/platform/freshness
curl "http://localhost:8001/comparaison?arr1=6&arr2=18"
python -m pytest tests/ -q
python scripts/validate_rncp.py
```

Démo soutenance complète : `scripts/demo.ps1`

## Annexe B — Dictionnaire des indicateurs et formules

| Indicateur | Formule / méthode | Unité |
|------------|-------------------|-------|
| Prix/m² | Médiane transactions DVF | €/m² |
| Accessibilité achat | `(prix_m² × 50) / (revenu_médian / 12)` | mois de revenu |
| Tension locative | `(loyer_m² × 50 × 12) / revenu_médian × 100` | % |
| Densité | `population / superficie_km²` | hab./km² |
| Pollution locale | Indice Citeair × f(densité, transports) | 1–10 |
| Score santé | Σ (ratio équipement × pondération) | 0–100 |
| Logements sociaux | Taux RPLS / références open data | % |

Pondérations santé : pharmacies 20 %, médecins 20 %, urgences 20 %, dentistes 15 %, DAE 10 %, centres 10 %, hôpitaux 5 %.

## Annexe C — Endpoints API principaux

- `GET /arrondissements?annee=2024` — liste enrichie
- `GET /arrondissements/{num}` — détail
- `GET /comparaison?arr1=1&arr2=13` — comparaison
- `GET /timeline?arr=15` — évolution temporelle
- `GET /sql/accessibilite` — vue SQL métier
- `GET /mongo/geo-points?arrondissement=6` — points DVF
- `GET /platform/governance` — catalogue et quotas
- `GET /health` — état des services
- `GET /docs` — documentation Swagger

## Annexe D — Structure du dépôt

```
urban-data/
├── api.py                    # API FastAPI
├── pipeline.py               # Orchestration Medallion
├── data_processor.py         # Bronze → Silver → Gold
├── public_data_integrations.py
├── data_normalization.py
├── dashboard/                # Frontend
├── ude_platform/             # Modules plateforme
├── database/init.sql         # Schéma PostgreSQL
├── data/                     # Bronze, Silver, Gold, export
├── tests/                    # 18 tests pytest
├── scripts/                  # sync, demo, validate
└── .github/workflows/        # CI/CD
```

## Annexe E — Bibliographie et sources open data

- data.gouv.fr — DVF (geo-dvf), Filosofi, délinquance SSMSI
- opendata.paris.fr — loyers encadrement, logements sociaux, qualité de l'air
- opendata.caissedesdepots.fr — logements sociaux CDL
- adresse.data.gouv.fr — Base Adresse Nationale (géocodage)
- Documentation Medallion — Databricks Lakehouse
- FastAPI — https://fastapi.tiangolo.com
- MapLibre GL — https://maplibre.org
- Chart.js — https://www.chartjs.org

## Annexe F — Validation des compétences (synthèse)

**Préparation des données**
- C1 Outils transformation : pandas, pyarrow, pipeline Medallion ✓
- C2 Qualité métier : politique NA, `data_quality`, `_sources` ✓
- C3 Documentation : README, DATA_LAKE, logs pipeline ✓
- C4 Prêt ML : CSV, Parquet partitionné, features dérivées ✓

**Visualisation**
- C1 Clarté et gouvernance : 11 indicateurs, légendes, limites MVP ✓
- C2 Temps réel : enrichissement à la requête, fraîcheur affichée ✓
- C3 Fonctionnalités avancées : comparer, drill-down, timeline ✓
- C4 Responsive et décision : breakpoint 1024px, accessibilité mois revenu ✓

**Analyse**
- C1 Techniques adaptées : médiane, ratios, scores composites ✓
- C2 Insights métier : disparités prix, mixité, accessibilité ✓
- C3 Documentation alignée : SYNTHESE_ECARTS, formules, objectifs ✓

---

*Fin du rapport — Urban Data Explorer, juin 2026*
