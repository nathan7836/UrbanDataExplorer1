# Compétence — Base de données relationnelle

> **Libellé RNCP :** *Concevoir et développer une base de données relationnelle universellement accessible en réponse aux besoins d’un client / d’une gouvernance.*

## Besoins client (Urban Data Explorer)

| Besoin métier | Tables / vues | Usage |
|---------------|---------------|--------|
| Comparer les prix par arrondissement et par année | `prix_annuel`, `v_prix_par_annee` | Dashboard, exports BI |
| Indicateurs socio-économiques fusionnés | `indicateurs_arrondissement`, `v_indicateurs_complets` | Carte choroplèthe |
| Accessibilité logement (prix vs revenu) | `v_accessibilite_prix_revenu` | Rapport client / politique publique |
| Traçabilité des sources | `integration_report`, `sources_json` | Gouvernance data |
| Audit des chargements | `pipeline_runs` | Équipe data (lecture seule client) |

## Conception relationnelle

- **Normalisation** : référentiel `arrondissements`, faits `prix_annuel`, attributs `indicateurs_arrondissement`.
- **Intégrité** : clés primaires, FK, contraintes `CHECK` (arrondissement 1–20, années 2018–2030).
- **Vues métier** : exposition simplifiée pour les consommateurs (pas de jointures complexes côté client).

Schéma : [`database/init.sql`](database/init.sql)

## Gouvernance d’accès

| Rôle | Droits | Profil |
|------|--------|--------|
| `ude_admin` | Lecture + écriture (pipeline, sync Gold) | Équipe ingestion |
| `ude_reader` | **SELECT uniquement** sur tables et vues | Client, API, BI, jury |

Principe : séparation **production** (écriture) / **consommation** (lecture universelle).

## Gold = SQL uniquement

Le jeu **Gold agrégé** (20 arrondissements, KPIs, typologie) est dans **PostgreSQL**, pas dans MongoDB.  
Mongo stocke uniquement les **points géolocalisés** issus du Bronze (voir [BDD_NON_RELATIONNELLE.md](BDD_NON_RELATIONNELLE.md)).

## Accès universel (plusieurs canaux)

1. **SQL direct** (lecture seule) : utilisateur `ude_reader` → base `urban_data`
2. **API REST** : `GET /sql/accessibilite`, `GET /sql/vues`, `GET /bdd/relationnelle`, `GET /arrondissements`
3. **OpenAPI** : http://localhost:8001/docs
4. **Backend auto** : `DATA_BACKEND=auto` → Postgres puis repli JSON fichier

## Mise en service

```powershell
docker compose up -d postgres
python pipeline.py
python scripts/sync_platform.py
curl http://localhost:8001/bdd/relationnelle
curl http://localhost:8001/sql/accessibilite
```

## Exemple SQL (client en lecture seule)

```sql
-- Connexion : ude_reader @ urban_data
SELECT * FROM v_accessibilite_prix_revenu ORDER BY mois_revenu_pour_50m2 DESC;
SELECT * FROM v_prix_par_annee WHERE annee = 2023;
```
