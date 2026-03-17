# Synthèse des écarts — Urban Data Explorer

Document consolidé à partir des vérifications du projet (pipeline, API, exports, dashboard, architecture technique, compétences RNCP, objectifs du sujet).

**Dernière mise à jour :** juin 2026

### Validation RNCP (8 compétences)

| Statut | Détail |
|--------|--------|
| **Validé (artefacts + doc)** | [BDD_RELATIONNELLE.md](BDD_RELATIONNELLE.md) + [BDD_NON_RELATIONNELLE.md](BDD_NON_RELATIONNELLE.md), endpoints `/bdd/*` |
| **Démontré** | `docker compose up -d postgres mongo` → `python scripts/sync_platform.py` → `curl /bdd/relationnelle` |
| **Commande** | `python scripts/validate_rncp.py` · démo complète : `scripts/demo.ps1` |

---

## Limites assumées (à dire au jury)

| Limite | Choix / justification |
|--------|-------------------------|
| **Maille IRIS / quartiers** | Périmètre MVP = 20 arrondissements. IRIS = refonte carto + agrégations (semaines). |
| **Loyers** | Open data **encadrement Paris** (loyers de référence T2 non meublé 1946–1970), pas l'ensemble du marché locatif ni toutes les typologies. |
| **Logements sociaux %** | Taux 2024 = **références par arrondissement** ; pas d'export RPLS officiel ventilé 75101–75120 sur data.gouv. |
| **Évolution logements sociaux** | Série 2018–2024 **calibrée sur les livraisons** Paris open data, pas une série RPLS annuelle brute. |
| **INSEE / Melodi** | `insee: skipped` — portail non souscrit ; revenus Filosofi, typologie DVF, logements Paris en alternative. |
| **Végétation / transports** | Couches **partiellement simulées** (`transports_data.js`) ; air et délinquance = open data réelles. |
| **MinIO / lake cloud** | Optionnel en démo locale ; Parquet partitionné + `data/export/` suffisent pour le MVP. |
| **Tuiles vectorielles** | 20 polygones GeoJSON + OSM raster ; pas de Martin/tippecanoe (hors périmètre). |

Ces limites sont aussi visibles dans le dashboard (panneau **Limites du MVP**).

---

## Légende

| Priorité | Signification |
|----------|----------------|
| **P1** | Fortement attendu au jury / explicitement dans le sujet |
| **P2** | Important pour crédibilité ou compétences RNCP |
| **P3** | Amélioration / industrialisation (nice to have) |

---

## Écarts restants (résumé)

| Domaine | Statut | Priorité |
|---------|--------|----------|
| `SOURCES.md` formel | Ouvert | P1 |
| Maille IRIS | Hors MVP (assumé) | P1 |
| Loyers open data | **Fait** | — |
| Logements sociaux + évolution | **Fait** (limites ci-dessus) | — |
| Accessibilité prix/revenu UI | **Fait** | — |
| INSEE / typologie recensement | Ouvert (alternatives OK) | P2 |
| Végétation / transports réels | Ouvert | P2 |
| Filtres API combinés | Partiel | P2 |
| Bbox géo `/mongo/geo-points` | **Fait** | — |
| a11y complète (audit WCAG) | Partiel | P1 |
| Tests (pipeline/export) | Partiel (8 tests) | P2 |
| Schéma architecture | Ouvert | P2 |
| Tuiles vectorielles | Ouvert | P2–P3 |
| Auth API | Hors MVP | P3 |

---

## Synthèse par blocs

| Bloc | Couverture | Reste principal |
|------|------------|-----------------|
| Compétences RNCP | **~95 %** | Démo live (`scripts/demo.ps1`) |
| Objectifs projet | **~92 %** | IRIS, doc sourcing |
| Dashboard logement | **~90 %** | Végétation/transports réels |
| API REST | **~95 %** | Filtres combinés |
| Architecture technique | **~85 %** | Tuiles, MinIO prod |

---

## Checklist soutenance

- [x] `python pipeline.py` exécuté (Gold à jour — juin 2026)
- [x] `python scripts/sync_platform.py` (Postgres + Mongo OK)
- [ ] `python api.py` démarré (port **8001**)
- [ ] `dashboard/index.html` ouvert (Live Server **5500**)
- [x] Limites annoncées (panneau dashboard + section ci-dessus)
- [ ] Démo : année 2023 → comparaison 1 vs 6 → loyers → accessibilité → Points DVF
- [ ] `curl http://localhost:8001/bdd/relationnelle` et `/bdd/non-relationnelle`

### Commandes démo

```powershell
docker compose up -d postgres mongo redis
python scripts/sync_platform.py
python api.py
# Live Server sur dashboard/
```

Ou : `.\scripts\demo.ps1`

---

## Phrase de clôture (oral)

> Urban Data Explorer livre une chaîne data complète sur Paris par arrondissement : collecte open data, lake Medallion, géocodage, sync PostgreSQL/MongoDB, API et dashboard. Les limites — maille arrondissement, loyers d'encadrement, évolution sociale calibrée sur livraisons, INSEE absent, végétation/transports partiels — sont assumées et visibles dans l'interface.

---

## Fichiers utiles

| Fichier | Rôle |
|---------|------|
| `pipeline.py` | Bronze → Gold |
| `scripts/sync_platform.py` | Gold → Postgres, Bronze → Mongo |
| `scripts/demo.ps1` | Démo soutenance |
| `public_data_integrations.py` | Loyers, logements sociaux, DVF |
| `database/init.sql` | Schéma PostgreSQL |
| `api.py` | API REST |
| `dashboard/` | Interface + `config.js` |
