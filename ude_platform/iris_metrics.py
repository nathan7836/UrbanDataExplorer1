"""Calcul d'indicateurs natifs à la maille IRIS.

Les jointures DVF et arbres sont spatiales. Les bases INSEE sont jointes par
code IRIS. Aucun indicateur d'arrondissement n'est recopié dans cette couche.
"""

from __future__ import annotations

import json
import logging
import math
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import pandas as pd
import requests


logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = ROOT / "data" / "bronze" / "raw_cache"
CONTOURS_FILE = ROOT / "dashboard" / "static" / "data" / "paris_iris.geojson"
OUTPUT_FILE = ROOT / "dashboard" / "static" / "data" / "paris_iris_metrics.json"

DVF_URL = "https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/departements/75.csv.gz"
POPULATION_URL = (
    "https://www.insee.fr/fr/statistiques/fichier/8268806/"
    "base-ic-evol-struct-pop-2021_csv.zip"
)
LOGEMENT_URL = (
    "https://www.insee.fr/fr/statistiques/fichier/8268838/"
    "base-ic-logement-2021_csv.zip"
)
REVENUS_URL = (
    "https://www.insee.fr/fr/statistiques/fichier/8229323/"
    "BASE_TD_FILO_IRIS_2021_DISP_CSV.zip"
)
ARBRES_URL = (
    "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/"
    "les-arbres/exports/csv?select=geo_point_2d"
)

MIN_DVF_TRANSACTIONS = 3


def _download(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("[IRIS] Téléchargement %s", url)
    with requests.get(url, timeout=300, stream=True) as response:
        response.raise_for_status()
        with path.open("wb") as stream:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    stream.write(chunk)
    return path


def _rings(geometry: Dict[str, Any]) -> Iterable[list]:
    if geometry.get("type") == "Polygon":
        yield from geometry.get("coordinates", [])
    elif geometry.get("type") == "MultiPolygon":
        for polygon in geometry.get("coordinates", []):
            yield from polygon


def _point_in_ring(lon: float, lat: float, ring: list) -> bool:
    inside = False
    j = len(ring) - 1
    for i, (xi, yi) in enumerate(ring):
        xj, yj = ring[j]
        intersects = ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-15) + xi
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def _point_in_geometry(lon: float, lat: float, geometry: Dict[str, Any]) -> bool:
    polygons = (
        [geometry.get("coordinates", [])]
        if geometry.get("type") == "Polygon"
        else geometry.get("coordinates", [])
    )
    for polygon in polygons:
        if polygon and _point_in_ring(lon, lat, polygon[0]):
            if not any(_point_in_ring(lon, lat, hole) for hole in polygon[1:]):
                return True
    return False


def _ring_area_km2(ring: list) -> float:
    if len(ring) < 3:
        return 0.0
    mean_lat = sum(point[1] for point in ring) / len(ring)
    x_scale = 111.320 * math.cos(math.radians(mean_lat))
    y_scale = 110.574
    area = 0.0
    for (lon1, lat1), (lon2, lat2) in zip(ring, ring[1:] + ring[:1]):
        area += (lon1 * x_scale) * (lat2 * y_scale)
        area -= (lon2 * x_scale) * (lat1 * y_scale)
    return abs(area) / 2


def _geometry_area_km2(geometry: Dict[str, Any]) -> float:
    polygons = (
        [geometry.get("coordinates", [])]
        if geometry.get("type") == "Polygon"
        else geometry.get("coordinates", [])
    )
    total = 0.0
    for polygon in polygons:
        if not polygon:
            continue
        total += _ring_area_km2(polygon[0])
        total -= sum(_ring_area_km2(hole) for hole in polygon[1:])
    return max(total, 0.0)


class IrisLocator:
    def __init__(self, geojson: Dict[str, Any]):
        self.by_arrondissement: Dict[int, list] = defaultdict(list)
        for feature in geojson.get("features", []):
            props = feature["properties"]
            points = [point for ring in _rings(feature["geometry"]) for point in ring]
            lons = [point[0] for point in points]
            lats = [point[1] for point in points]
            self.by_arrondissement[int(props["arrondissement"])].append(
                (min(lons), min(lats), max(lons), max(lats), feature)
            )

    def locate(self, lon: float, lat: float, arrondissement: Optional[int] = None) -> Optional[str]:
        candidates = (
            self.by_arrondissement.get(arrondissement, [])
            if arrondissement
            else [item for values in self.by_arrondissement.values() for item in values]
        )
        for min_lon, min_lat, max_lon, max_lat, feature in candidates:
            if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                if _point_in_geometry(lon, lat, feature["geometry"]):
                    return feature["properties"]["code_iris"]
        return None


def _read_zip_csv(path: Path, columns: list[str], decimal: str = ".") -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        member = next(
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv") and not Path(name).name.lower().startswith("meta_")
        )
        with archive.open(member) as stream:
            return pd.read_csv(
                stream,
                sep=";",
                usecols=columns,
                dtype={"IRIS": str},
                decimal=decimal,
                low_memory=False,
            )


def _number(value: Any, digits: int = 1) -> Optional[float]:
    try:
        result = float(value)
        if math.isnan(result):
            return None
        return round(result, digits)
    except (TypeError, ValueError):
        return None


def _arrondissement_from_code(value: Any) -> Optional[int]:
    try:
        code = str(int(float(value))).zfill(5)
        if code.startswith("751"):
            number = int(code[-2:])
            return number if 1 <= number <= 20 else None
    except (TypeError, ValueError):
        pass
    return None


def _load_dvf(path: Path, year: int, locator: IrisLocator) -> Dict[str, Dict[str, Any]]:
    columns = [
        "id_mutation", "valeur_fonciere", "type_local", "surface_reelle_bati",
        "nombre_pieces_principales", "longitude", "latitude", "code_commune",
    ]
    frame = pd.read_csv(path, usecols=columns, low_memory=False)
    frame = frame[frame["type_local"] == "Appartement"].copy()
    for column in (
        "valeur_fonciere", "surface_reelle_bati", "nombre_pieces_principales",
        "longitude", "latitude",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["id_mutation", "valeur_fonciere", "surface_reelle_bati", "longitude", "latitude"])
    frame = frame[(frame["surface_reelle_bati"] > 9) & (frame["valeur_fonciere"] > 0)]
    sales = frame.groupby("id_mutation", as_index=False).agg(
        valeur_fonciere=("valeur_fonciere", "first"),
        surface_reelle_bati=("surface_reelle_bati", "sum"),
        nombre_pieces=("nombre_pieces_principales", "sum"),
        longitude=("longitude", "first"),
        latitude=("latitude", "first"),
        code_commune=("code_commune", "first"),
    )
    sales["prix_m2"] = sales["valeur_fonciere"] / sales["surface_reelle_bati"]
    sales = sales[sales["prix_m2"].between(1000, 30000)]
    buckets: Dict[str, list] = defaultdict(list)
    for row in sales.itertuples(index=False):
        code = locator.locate(
            float(row.longitude), float(row.latitude), _arrondissement_from_code(row.code_commune)
        )
        if code:
            buckets[code].append(row)
    result = {}
    for code, rows in buckets.items():
        if len(rows) < MIN_DVF_TRANSACTIONS:
            continue
        prices = pd.Series([row.prix_m2 for row in rows])
        surfaces = pd.Series([row.surface_reelle_bati for row in rows])
        rooms = pd.Series([row.nombre_pieces for row in rows])
        result[code] = {
            "annee": year,
            "prix_m2_median": round(float(prices.median()), 0),
            "nombre_transactions": len(rows),
            "surface_mediane_m2": round(float(surfaces.median()), 1),
            "pieces_moyennes": round(float(rooms.mean()), 1),
        }
    return result


def build_iris_metrics(
    *,
    contours_path: Path = CONTOURS_FILE,
    output_path: Path = OUTPUT_FILE,
    source_overrides: Optional[Dict[str, Path]] = None,
) -> Dict[str, Any]:
    source_overrides = source_overrides or {}
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with contours_path.open(encoding="utf-8") as stream:
        contours = json.load(stream)
    locator = IrisLocator(contours)
    metrics: Dict[str, Dict[str, Any]] = {}
    for feature in contours["features"]:
        props = feature["properties"]
        area = _geometry_area_km2(feature["geometry"])
        metrics[props["code_iris"]] = {
            "code_iris": props["code_iris"],
            "nom_iris": props["nom_iris"],
            "arrondissement": props["arrondissement"],
            "superficie_km2": round(area, 4),
        }

    population_path = source_overrides.get("population") or _download(
        POPULATION_URL, CACHE_DIR / "population_iris_2021.zip"
    )
    population = _read_zip_csv(population_path, ["IRIS", "P21_POP"])
    for row in population.itertuples(index=False):
        code = str(row.IRIS).zfill(9)
        if code not in metrics:
            continue
        pop = _number(row.P21_POP, 0)
        area = metrics[code]["superficie_km2"]
        if pop is not None:
            metrics[code]["population"] = {
                "population": int(pop),
                "densite_km2": round(pop / area, 0) if area else None,
                "annee": 2021,
            }

    revenus_path = source_overrides.get("revenus") or _download(
        REVENUS_URL, CACHE_DIR / "revenus_iris_2021.zip"
    )
    revenus = _read_zip_csv(
        revenus_path, ["IRIS", "DISP_MED21", "DISP_TP6021", "DISP_GI21"], decimal=","
    )
    for row in revenus.itertuples(index=False):
        code = str(row.IRIS).zfill(9)
        if code in metrics:
            median = _number(row.DISP_MED21, 0)
            metrics[code]["revenus"] = {
                "niveau_vie_median": int(median) if median is not None else None,
                "taux_pauvrete": _number(row.DISP_TP6021),
                "indice_gini": _number(row.DISP_GI21, 3),
                "annee": 2021,
            }

    logement_path = source_overrides.get("logement") or _download(
        LOGEMENT_URL, CACHE_DIR / "logement_iris_2021.zip"
    )
    logement = _read_zip_csv(
        logement_path,
        [
            "IRIS", "P21_LOG", "P21_RP", "P21_RP_LOCHLMV", "P21_MAISON",
            "P21_APPART", "P21_RP_1P", "P21_RP_2P", "P21_RP_3P",
            "P21_RP_4P", "P21_RP_5PP",
        ],
    )
    for row in logement.itertuples(index=False):
        code = str(row.IRIS).zfill(9)
        if code not in metrics:
            continue
        rp = _number(row.P21_RP)
        hlm = _number(row.P21_RP_LOCHLMV)
        total = _number(row.P21_LOG)
        appartements = _number(row.P21_APPART)
        metrics[code]["logements"] = {
            "nombre_logements": round(total) if total is not None else None,
            "residences_principales": round(rp) if rp is not None else None,
            "logements_sociaux": round(hlm) if hlm is not None else None,
            "logements_sociaux_pourcentage": round(hlm / rp * 100, 1) if rp and hlm is not None else None,
            "appartements_pourcentage": round(appartements / total * 100, 1) if total and appartements is not None else None,
            "repartition_pieces": {
                "1": round(_number(row.P21_RP_1P) or 0),
                "2": round(_number(row.P21_RP_2P) or 0),
                "3": round(_number(row.P21_RP_3P) or 0),
                "4": round(_number(row.P21_RP_4P) or 0),
                "5+": round(_number(row.P21_RP_5PP) or 0),
            },
            "annee": 2021,
        }

    for year in (2022, 2023, 2024):
        path = source_overrides.get(f"dvf_{year}") or _download(
            DVF_URL.format(year=year), CACHE_DIR / f"dvf_75_{year}.csv.gz"
        )
        for code, values in _load_dvf(path, year, locator).items():
            metrics[code].setdefault("immobilier", {})[str(year)] = values

    arbres_path = source_overrides.get("arbres") or _download(
        ARBRES_URL, CACHE_DIR / "arbres_paris.csv"
    )
    tree_counts: Dict[str, int] = defaultdict(int)
    arbres = pd.read_csv(arbres_path, sep=";", dtype=str)
    point_column = next((column for column in arbres.columns if "geo_point" in column), None)
    if point_column:
        for raw in arbres[point_column].dropna():
            try:
                lat_text, lon_text = str(raw).split(",", 1)
                code = locator.locate(float(lon_text), float(lat_text))
                if code:
                    tree_counts[code] += 1
            except (TypeError, ValueError):
                continue
    for code, count in tree_counts.items():
        area = metrics[code]["superficie_km2"]
        metrics[code]["vegetation"] = {
            "nombre_arbres": count,
            "arbres_par_km2": round(count / area, 1) if area else None,
        }

    for code, item in metrics.items():
        income = (item.get("revenus") or {}).get("niveau_vie_median")
        for year, real_estate in (item.get("immobilier") or {}).items():
            price = real_estate.get("prix_m2_median")
            if price and income:
                item.setdefault("accessibilite", {})[year] = {
                    "mois_revenu_pour_50m2_achat": round(price * 50 / (income / 12), 1),
                    "revenu_reference": 2021,
                }

    payload = {
        "maille": "IRIS",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "minimum_transactions_dvf": MIN_DVF_TRANSACTIONS,
        "sources": {
            "contours": "Contours...IRIS® IGN-INSEE, édition 2024",
            "population": "INSEE Recensement de la population 2021, base IRIS",
            "revenus": "INSEE Filosofi 2021, revenus disponibles à l'IRIS",
            "logements": "INSEE Recensement Logement 2021, base IRIS",
            "immobilier": "DVF géolocalisée 2022-2024, data.gouv.fr",
            "vegetation": "Les arbres, Paris Data",
        },
        "indicateurs_non_disponibles": [
            "loyers", "tension_locative", "delinquance", "pollution",
            "transports", "sante", "score_global", "potentiel_plus_value",
        ],
        "iris": metrics,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
    logger.info("[IRIS] %s indicateurs écrits dans %s", len(metrics), output_path)
    return payload
