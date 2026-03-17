"""
Synchronisation :
  - Gold → PostgreSQL (relationnel, compétence SQL)
  - Points géo Bronze → MongoDB geo_points (NoSQL, compétence NoSQL)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from ude_platform.config import GOLD_JSON, POSTGRES_URL
from ude_platform.geo_points import sync_mongo_geo_points

logger = logging.getLogger(__name__)


def load_gold(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or GOLD_JSON
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def sync_postgres(gold: Dict[str, Any], dsn: Optional[str] = None) -> bool:
    """Charge le jeu Gold dans PostgreSQL."""
    try:
        import psycopg2
        from psycopg2.extras import Json
    except ImportError:
        logger.error("psycopg2-binary requis : pip install psycopg2-binary")
        return False

    url = dsn or POSTGRES_URL
    try:
        conn = psycopg2.connect(url)
        conn.autocommit = False
        cur = conn.cursor()

        for arr in gold.get("arrondissements", []):
            num = arr["arrondissement"]
            geo = arr.get("geocoding") or {}
            cur.execute(
                """
                INSERT INTO arrondissements (arrondissement, nom, code_insee, longitude, latitude, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (arrondissement) DO UPDATE SET
                    nom = EXCLUDED.nom, code_insee = EXCLUDED.code_insee,
                    longitude = EXCLUDED.longitude, latitude = EXCLUDED.latitude,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    num,
                    arr.get("nom"),
                    arr.get("code_insee"),
                    geo.get("longitude"),
                    geo.get("latitude"),
                    datetime.now(),
                ),
            )

            cur.execute("DELETE FROM prix_annuel WHERE arrondissement = %s", (num,))
            evolution = sorted(arr.get("evolution_annuelle", []), key=lambda x: x.get("annee", 0))
            for i, evol in enumerate(evolution):
                var_pct = None
                if i > 0:
                    prev = evolution[i - 1].get("prix_m2_median")
                    cur_p = evol.get("prix_m2_median")
                    if prev and cur_p and prev > 0:
                        var_pct = round(((cur_p - prev) / prev) * 100, 2)
                cur.execute(
                    """
                    INSERT INTO prix_annuel
                    (arrondissement, annee, prix_m2_median, nombre_transactions, variation_annuelle_pct)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        num,
                        evol.get("annee"),
                        evol.get("prix_m2_median"),
                        evol.get("nombre_transactions"),
                        var_pct,
                    ),
                )

            poll = arr.get("pollution_qualite_air") or {}
            delits = arr.get("delits_enregistres") or {}
            rev = arr.get("revenus_moyens") or {}
            dens = arr.get("densite_population") or {}
            cur.execute(
                """
                INSERT INTO indicateurs_arrondissement (
                    arrondissement, logements_sociaux_pct, revenu_median_menage, revenu_moyen_menage,
                    densite_km2, population, pollution_indice_atmo, delits_par_1000, total_delits,
                    typologie_json, sources_json, updated_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (arrondissement) DO UPDATE SET
                    logements_sociaux_pct = EXCLUDED.logements_sociaux_pct,
                    revenu_median_menage = EXCLUDED.revenu_median_menage,
                    revenu_moyen_menage = EXCLUDED.revenu_moyen_menage,
                    densite_km2 = EXCLUDED.densite_km2,
                    population = EXCLUDED.population,
                    pollution_indice_atmo = EXCLUDED.pollution_indice_atmo,
                    delits_par_1000 = EXCLUDED.delits_par_1000,
                    total_delits = EXCLUDED.total_delits,
                    typologie_json = EXCLUDED.typologie_json,
                    sources_json = EXCLUDED.sources_json,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    num,
                    arr.get("logements_sociaux_pourcentage"),
                    rev.get("revenu_median_menage"),
                    rev.get("revenu_moyen_menage"),
                    dens.get("densite_km2"),
                    dens.get("population"),
                    poll.get("indice_atmo"),
                    delits.get("delits_par_1000_habitants"),
                    delits.get("total_delits"),
                    Json(arr.get("typologie") or {}),
                    Json(arr.get("_sources") or {}),
                    datetime.now(),
                ),
            )

        cur.execute(
            "INSERT INTO integration_report (report_json, sources_updated_at) VALUES (%s, %s)",
            (Json(gold.get("integration_report") or {}), gold.get("sources_updated_at")),
        )
        finalize_metrics = (gold.get("integration_report") or {}).get("pipeline_finalize")
        cur.execute(
            "INSERT INTO pipeline_runs (status, finished_at, metrics_json) VALUES (%s, %s, %s)",
            (
                "sync_ok",
                datetime.now(),
                Json(
                    finalize_metrics
                    or {
                        "arrondissements": len(gold.get("arrondissements", [])),
                        "source": str(GOLD_JSON),
                    }
                ),
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
        logger.info("[PostgreSQL] %s arrondissements synchronisés", len(gold.get("arrondissements", [])))
        return True
    except Exception as e:
        logger.error("[PostgreSQL] Sync échouée : %s", e)
        return False


def sync_gold_to_databases(gold_path: Optional[Path] = None) -> Dict[str, bool]:
    gold = load_gold(gold_path)
    return {
        "postgres": sync_postgres(gold),
        "mongo_geo_points": sync_mongo_geo_points(),
    }
