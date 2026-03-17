# Conformité données — Urban Data Explorer

## Périmètre des données

- **Sources** : open data publiques (data.gouv, OpenData Paris, INSEE/Filosofi agrégé).
- **Pas de données personnelles directes** en Gold : agrégats par **arrondissement** (pas de nom d’individu).
- **Géocodage** : adresses DVF utilisées pour calculer des centroïdes ; pas stockage d’adresses complètes en couche Gold.

## Base légale

- Intérêt légitime / mission de formation et démonstration technique.
- Licences open data des producteurs (voir `integration_report` dans Gold).

## Mesures techniques

| Mesure | Implémentation |
|--------|----------------|
| Minimisation | Agrégation arrondissement |
| Secrets | `.env` non versionné (`.gitignore`) |
| Accès | PostgreSQL : rôle `ude_reader` lecture seule ; `ude_admin` pipeline |
| Stockage | Lake local + MinIO (chiffrement au repos = responsabilité hébergeur) |
| Rétention | Cache Bronze 14–30 jours ; snapshots horodatés + `*_latest` |

## Droits des personnes

Non applicable aux jeux agrégés sans identification. En cas d’ajout de PII : procédure d’effacement à documenter.

## Registre simplifié

| Traitement | Finalité | Données | Durée |
|------------|----------|---------|-------|
| Pipeline UDE | Analyse marché logement Paris | Indicateurs publics | Durée projet + caches |
| API / Dashboard | Visualisation | Gold | Même |

## Responsable

Équipe projet Urban Data Explorer (formation).
