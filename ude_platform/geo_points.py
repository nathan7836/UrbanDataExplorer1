"""
Extraction des points géolocalisés depuis Bronze → MongoDB (NoSQL).
Le Gold agrégé reste en PostgreSQL uniquement.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ude_platform.config import DATA_ROOT, MONGO_DB, MONGO_GEO_COLLECTION, MONGO_URL

logger = logging.getLogger(__name__)

RAW_CACHE = DATA_ROOT / "bronze" / "raw_cache"
GEO_POINTS_MAX_PER_ARR = int(os.getenv("GEO_POINTS_MAX_PER_ARR", "40"))
GEO_POINTS_MAX_GEOCODED = int(os.getenv("GEO_POINTS_MAX_GEOCODED", "80"))


def _arrondissement_from_postal(code_postal: Any) -> Optional[int]:
    try:
        cp = str(int(code_postal)).zfill(5)
        if cp.startswith("750") and len(cp) == 5:
            n = int(cp[2:])
            if 1 <= n <= 20:
                return n
    except (TypeError, ValueError):
        pass
    return None


def _arrondissement_from_insee(code_insee: str) -> Optional[int]:
    if code_insee and code_insee.startswith("751") and len(code_insee) == 5:
        n = int(code_insee[3:])
        if 1 <= n <= 20:
            return n
    return None


def find_dvf_cache() -> Optional[Path]:
    if not RAW_CACHE.exists():
        return None
    candidates = sorted(RAW_CACHE.glob("dvf_75_*.csv.gz"), reverse=True)
    return candidates[0] if candidates else None


def extract_dvf_points(cache_path: Path, max_per_arr: int = GEO_POINTS_MAX_PER_ARR) -> List[Dict[str, Any]]:
    import csv
    import gzip
    import random

    year_match = re.search(r"(\d{4})", cache_path.name)
    source_year = int(year_match.group(1)) if year_match else None

    buckets: Dict[str, List[Dict[str, Any]]] = {}
    opener = gzip.open if cache_path.suffix == ".gz" else open
    mode = "rt" if cache_path.suffix == ".gz" else "r"

    with opener(cache_path, mode, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if row.get("type_local") and row["type_local"] != "Appartement":
                continue
            try:
                code = str(int(float(row["code_commune"]))).zfill(5)
            except (KeyError, ValueError, TypeError):
                continue
            if not re.match(r"^751\d{2}$", code):
                continue
            try:
                lon = float(row["longitude"])
                lat = float(row["latitude"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                continue

            props: Dict[str, Any] = {"code_insee": code, "source_year": source_year}
            for key in ("valeur_fonciere", "surface_reelle_bati"):
                if row.get(key):
                    try:
                        props[key] = float(row[key])
                    except ValueError:
                        pass
            if row.get("date_mutation"):
                props["date_mutation"] = str(row["date_mutation"])[:10]

            buckets.setdefault(code, []).append({
                "row_id": i,
                "lon": lon,
                "lat": lat,
                "props": props,
            })

    points: List[Dict[str, Any]] = []
    for code in sorted(buckets.keys()):
        arr = _arrondissement_from_insee(code)
        if arr is None:
            continue
        pool = buckets[code]
        sample = random.sample(pool, min(max_per_arr, len(pool)))
        for item in sample:
            lon, lat = item["lon"], item["lat"]
            points.append({
                "_id": f"dvf_{code}_{item['row_id']}",
                "type": "dvf_transaction",
                "arrondissement": arr,
                "location": {"type": "Point", "coordinates": [lon, lat]},
                "longitude": round(lon, 6),
                "latitude": round(lat, 6),
                "properties": item["props"],
                "source": "data.gouv/geo-dvf",
                "synced_at": datetime.now().isoformat(),
            })
    return points


def extract_geocoded_points(
    cache_path: Optional[Path] = None, max_points: int = GEO_POINTS_MAX_GEOCODED
) -> List[Dict[str, Any]]:
    path = cache_path or (RAW_CACHE / "geocoding_cache.json")
    if not path.exists():
        return []

    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    points: List[Dict[str, Any]] = []
    for i, (key, geo) in enumerate(cache.items()):
        if i >= max_points:
            break
        lon = geo.get("longitude")
        lat = geo.get("latitude")
        if lon is None or lat is None:
            continue
        cp_match = re.search(r"750(\d{2})", key)
        arr = int(cp_match.group(1)) if cp_match else None
        if arr is None or arr < 1 or arr > 20:
            continue
        code = f"751{arr:02d}"
        points.append({
            "_id": f"geocoded_{i}",
            "type": "geocoded_address",
            "arrondissement": arr,
            "code_insee": code,
            "location": {"type": "Point", "coordinates": [float(lon), float(lat)]},
            "longitude": round(float(lon), 6),
            "latitude": round(float(lat), 6),
            "properties": {
                "label": geo.get("label"),
                "provider": geo.get("provider"),
                "score": geo.get("score"),
            },
            "source": geo.get("provider", "ban"),
            "synced_at": datetime.now().isoformat(),
        })
    return points


def build_geo_points_payload() -> Dict[str, Any]:
    dvf_cache = find_dvf_cache()
    dvf_pts: List[Dict[str, Any]] = []
    if dvf_cache:
        logger.info("[GeoPoints] Extraction DVF depuis %s", dvf_cache.name)
        dvf_pts = extract_dvf_points(dvf_cache)
    geo_pts = extract_geocoded_points()
    all_pts = dvf_pts + geo_pts
    by_type: Dict[str, int] = {}
    for p in all_pts:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1
    return {
        "points": all_pts,
        "stats": {
            "total": len(all_pts),
            "dvf_cache": str(dvf_cache) if dvf_cache else None,
            "by_type": by_type,
        },
    }


def sync_mongo_geo_points() -> bool:
    """Charge les points géolocalisés Bronze → collection Mongo geo_points."""
    try:
        from pymongo import MongoClient
        from pymongo.errors import CollectionInvalid
    except ImportError:
        logger.error("pymongo requis")
        return False

    payload = build_geo_points_payload()
    points = payload["points"]
    if not points:
        logger.warning("[MongoDB] Aucun point géo extrait du Bronze")
        return False

    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client[MONGO_DB]
        col = db[MONGO_GEO_COLLECTION]
        col.drop()
        col.insert_many(points)
        col.create_index("arrondissement")
        col.create_index("type")
        col.create_index("code_insee")
        try:
            col.create_index([("location", "2dsphere")])
        except CollectionInvalid:
            pass

        db["metadata"].replace_one(
            {"_id": "geo_points_catalog"},
            {
                "role": "nosql_geo_layer",
                "description": "Points géolocalisés issus du Bronze (DVF + géocodage), pas le Gold agrégé",
                "stats": payload["stats"],
                "synced_at": datetime.now().isoformat(),
            },
            upsert=True,
        )
        # Ancienne collection Gold dupliquée — nettoyage
        if "arrondissements" in db.list_collection_names():
            db["arrondissements"].drop()
            logger.info("[MongoDB] Collection arrondissements (ancien Gold) supprimée")

        logger.info("[MongoDB] %s points géo insérés dans %s", len(points), MONGO_GEO_COLLECTION)
        return True
    except Exception as e:
        logger.error("[MongoDB] Sync geo_points échouée : %s", e)
        return False
