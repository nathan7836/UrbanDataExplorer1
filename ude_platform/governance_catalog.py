"""Catalogues d'accès BDD — compétences relationnelle et non-relationnelle (RNCP)."""

from __future__ import annotations

from typing import Any, Dict, List

COMPETENCE_RELATIONNELLE = (
    "Concevoir et développer une base de données relationnelle universellement "
    "accessible en réponse aux besoins d'un client / d'une gouvernance"
)

COMPETENCE_NON_RELATIONNELLE = (
    "Concevoir et développer une base de données non-relationnelle universellement "
    "accessible permettant la mise à disposition des données"
)

BESOINS_CLIENT_SQL: List[Dict[str, str]] = [
    {
        "besoin": "Prix et évolution par arrondissement",
        "objet_sql": "v_prix_par_annee",
        "consommateur": "Dashboard, exports CSV/Parquet",
    },
    {
        "besoin": "Indicateurs carte (pollution, délits, revenus…)",
        "objet_sql": "v_indicateurs_complets",
        "consommateur": "Couches MapLibre",
    },
    {
        "besoin": "Accessibilité logement (prix / revenu)",
        "objet_sql": "v_accessibilite_prix_revenu",
        "consommateur": "Décideur / rapport client",
    },
    {
        "besoin": "Traçabilité et gouvernance",
        "objet_sql": "integration_report, governance_access",
        "consommateur": "Équipe data, audit",
    },
]

CANAUX_ACCES_UNIVERSEL: List[Dict[str, str]] = [
    {"canal": "API REST", "url": "/sql/accessibilite", "role": "ude_reader (via API)"},
    {"canal": "API catalogue", "url": "/bdd/relationnelle", "role": "public"},
    {"canal": "SQL direct", "url": "postgresql://ude_reader@host:5433/urban_data", "role": "ude_reader"},
    {"canal": "OpenAPI", "url": "/docs", "role": "public"},
]

CANAUX_ACCES_MONGO: List[Dict[str, str]] = [
    {"canal": "API points géo", "url": "/mongo/geo-points", "role": "lecture"},
    {"canal": "Filtre arrondissement", "url": "/mongo/geo-points?arrondissement=6", "role": "lecture"},
    {"canal": "Filtre type", "url": "/mongo/geo-points?type=dvf_transaction", "role": "lecture"},
    {"canal": "API catalogue", "url": "/bdd/non-relationnelle", "role": "public"},
    {"canal": "Métadonnées couche", "url": "/mongo/metadata", "role": "public"},
]


def catalogue_relationnel() -> Dict[str, Any]:
    return {
        "competence": COMPETENCE_RELATIONNELLE,
        "moteur": "PostgreSQL 16",
        "base": "urban_data",
        "contenu": "Gold agrégé (20 arrondissements, prix, indicateurs)",
        "gouvernance": {
            "ude_admin": "Écriture — pipeline et sync Gold",
            "ude_reader": "Lecture seule — client, BI, API (accès universel)",
        },
        "besoins_client": BESOINS_CLIENT_SQL,
        "vues_metier": [
            "v_prix_par_annee",
            "v_indicateurs_complets",
            "v_accessibilite_prix_revenu",
            "v_catalogue_donnees",
        ],
        "canaux_acces": CANAUX_ACCES_UNIVERSEL,
        "schema": "database/init.sql",
        "documentation": "BDD_RELATIONNELLE.md",
    }


def catalogue_non_relationnel() -> Dict[str, Any]:
    return {
        "competence": COMPETENCE_NON_RELATIONNELLE,
        "moteur": "MongoDB 7",
        "base": "urban_data",
        "collection": "geo_points",
        "contenu": "Points géolocalisés issus du Bronze (transactions DVF, adresses géocodées)",
        "pas_en_mongo": "Gold agrégé (uniquement PostgreSQL + fichier JSON)",
        "types_documents": {
            "dvf_transaction": "Vente DVF avec lat/lon (échantillon par arrondissement)",
            "geocoded_address": "Adresse géocodée BAN/Nominatim",
        },
        "indexes": ["arrondissement", "type", "code_insee", "location 2dsphere"],
        "canaux_mise_a_disposition": CANAUX_ACCES_MONGO,
        "sync": "ude_platform/geo_points.sync_mongo_geo_points() depuis data/bronze/raw_cache",
        "documentation": "BDD_NON_RELATIONNELLE.md",
    }
