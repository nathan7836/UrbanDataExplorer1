"""
Accès unifié aux données Gold : PostgreSQL (prioritaire) ou JSON (fichier).
Les points géo sont dans MongoDB (voir ude_platform/geo_points.py, /mongo/geo-points).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ude_platform.config import DATA_BACKEND, GOLD_JSON, POSTGRES_READER_URL

logger = logging.getLogger(__name__)

# Champs présents dans Gold JSON mais absents du schéma PostgreSQL actuel
_JSON_SUPPLEMENT_KEYS = (
    "vegetation_arbres",
    "transports_publics",
    "loyers",
    "logements_sociaux_evolution",
    "prix_m2_historique",
    "evolution_calculee",
    "tendance_annuelle",
    "accessibilite_logement",
)


def _merge_json_supplements(arrondissements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Complète les indicateurs non stockés en SQL (végétation, transports, etc.)."""
    try:
        gold_by_num = {
            a["arrondissement"]: a
            for a in _load_json().get("arrondissements", [])
        }
    except Exception as exc:
        logger.warning("Fusion Gold JSON impossible : %s", exc)
        return arrondissements

    for arr in arrondissements:
        src = gold_by_num.get(arr.get("arrondissement")) or {}
        for key in _JSON_SUPPLEMENT_KEYS:
            if src.get(key) is not None:
                arr[key] = src[key]
        if src.get("pollution_qualite_air"):
            pol = dict(arr.get("pollution_qualite_air") or {})
            pol.update(
                {k: v for k, v in src["pollution_qualite_air"].items() if v is not None}
            )
            arr["pollution_qualite_air"] = pol
    return arrondissements


def _load_json() -> Dict[str, Any]:
    with open(GOLD_JSON, encoding="utf-8") as f:
        return json.load(f)


def _load_postgres() -> Dict[str, Any]:
    import psycopg2
    from psycopg2.extras import RealDictCursor

    conn = psycopg2.connect(POSTGRES_READER_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT report_json, sources_updated_at FROM integration_report ORDER BY id DESC LIMIT 1")
    rep_row = cur.fetchone()
    integration_report = rep_row["report_json"] if rep_row else {}
    sources_updated_at = rep_row["sources_updated_at"] if rep_row else None

    cur.execute("SELECT * FROM arrondissements ORDER BY arrondissement")
    arrs = cur.fetchall()
    arrondissements: List[Dict] = []

    for row in arrs:
        num = row["arrondissement"]
        cur.execute(
            "SELECT annee, prix_m2_median, nombre_transactions, variation_annuelle_pct "
            "FROM prix_annuel WHERE arrondissement = %s ORDER BY annee",
            (num,),
        )
        prix_rows = cur.fetchall()
        evolution_annuelle = [
            {
                "annee": p["annee"],
                "prix_m2_median": float(p["prix_m2_median"]) if p["prix_m2_median"] else None,
                "nombre_transactions": p["nombre_transactions"],
            }
            for p in prix_rows
        ]
        cur.execute("SELECT * FROM indicateurs_arrondissement WHERE arrondissement = %s", (num,))
        ind = cur.fetchone() or {}

        prix_vals = [e["prix_m2_median"] for e in evolution_annuelle if e.get("prix_m2_median")]
        arrondissements.append({
            "arrondissement": num,
            "nom": row["nom"],
            "code_insee": row["code_insee"],
            "geocoding": {
                "longitude": row["longitude"],
                "latitude": row["latitude"],
            },
            "prix_m2_median": [],
            "evolution_annuelle": evolution_annuelle,
            "logements_sociaux_pourcentage": ind.get("logements_sociaux_pct"),
            "revenus_moyens": {
                "revenu_median_menage": ind.get("revenu_median_menage"),
                "revenu_moyen_menage": ind.get("revenu_moyen_menage"),
            },
            "densite_population": {
                "densite_km2": ind.get("densite_km2"),
                "population": ind.get("population"),
            },
            "pollution_qualite_air": {"indice_atmo": ind.get("pollution_indice_atmo")},
            "delits_enregistres": {
                "delits_par_1000_habitants": ind.get("delits_par_1000"),
                "total_delits": ind.get("total_delits"),
            },
            "typologie": ind.get("typologie_json") or {},
            "statistiques": {
                "prix_m2_actuel": prix_vals[-1] if prix_vals else None,
                "prix_m2_median": sorted(prix_vals)[len(prix_vals) // 2] if prix_vals else None,
                "prix_m2_min": min(prix_vals) if prix_vals else None,
                "prix_m2_max": max(prix_vals) if prix_vals else None,
                "prix_m2_moyen": sum(prix_vals) / len(prix_vals) if prix_vals else None,
            },
            "_sources": ind.get("sources_json") or {},
        })

    cur.close()
    conn.close()
    arrondissements = _merge_json_supplements(arrondissements)
    return {
        "arrondissements": arrondissements,
        "integration_report": integration_report,
        "sources_updated_at": sources_updated_at.isoformat()
        if hasattr(sources_updated_at, "isoformat")
        else sources_updated_at,
        "generated_at": sources_updated_at.isoformat()
        if hasattr(sources_updated_at, "isoformat")
        else sources_updated_at,
        "data_backend": "postgres",
    }


def load_gold_data(backend: Optional[str] = None) -> Dict[str, Any]:
    mode = (backend or DATA_BACKEND).lower()
    if mode == "json":
        data = _load_json()
        data["data_backend"] = "json"
        return data
    if mode == "postgres":
        return _load_postgres()
    if mode == "mongo":
        raise ValueError(
            "Gold n'est plus servi depuis MongoDB. Utilisez DATA_BACKEND=postgres|auto|json. "
            "Points géo : GET /mongo/geo-points"
        )
    # auto : postgres → json (Gold SQL ; NoSQL = points géo uniquement)
    try:
        return _load_postgres()
    except Exception as e:
        logger.debug("Postgres indisponible : %s", e)
    data = _load_json()
    data["data_backend"] = "json"
    return data


def invalidate_cache_hook():
    """Appelé par le consumer Redis."""
    pass
