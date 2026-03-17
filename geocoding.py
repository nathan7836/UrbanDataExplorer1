"""
Géocodage d'adresses : API BAN (prioritaire) puis Nominatim (OpenStreetMap).
Cache local pour limiter les appels et respecter les quotas.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

BAN_SEARCH_URL = "https://api-adresse.data.gouv.fr/search/"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
CACHE_PATH = Path("data/bronze/raw_cache/geocoding_cache.json")
USER_AGENT = os.environ.get("GEOCODING_USER_AGENT", "UrbanDataExplorer/1.0 (data-pipeline)")


class GeocodingService:
    """BAN en premier, Nominatim en secours."""

    def __init__(self, cache_path: Path = CACHE_PATH):
        self.cache_path = cache_path
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = self._load_cache()
        self._last_nominatim = 0.0
        self.nominatim_delay = float(os.environ.get("NOMINATIM_DELAY_SEC", "1.1"))

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        self.cache_path.write_text(
            json.dumps(self._cache, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def geocode(self, query: str, city: str = "Paris") -> Optional[Dict[str, Any]]:
        """
        Retourne {longitude, latitude, provider, score} ou None.
        """
        q = " ".join(query.split()).strip()
        if not q:
            return None

        cache_key = f"{q}|{city}".lower()
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._geocode_ban(q, city)
        if not result:
            result = self._geocode_nominatim(q, city)

        if result:
            self._cache[cache_key] = result
            self._save_cache()
        return result

    def _geocode_ban(self, query: str, city: str) -> Optional[Dict[str, Any]]:
        try:
            params = {"q": f"{query}, {city}", "limit": 1}
            r = requests.get(
                BAN_SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            r.raise_for_status()
            features = r.json().get("features") or []
            if not features:
                return None
            props = features[0].get("properties", {})
            coords = features[0].get("geometry", {}).get("coordinates")
            if not coords or len(coords) < 2:
                return None
            lon, lat = float(coords[0]), float(coords[1])
            return {
                "longitude": round(lon, 6),
                "latitude": round(lat, 6),
                "provider": "ban",
                "score": props.get("score"),
                "label": props.get("label"),
            }
        except Exception as e:
            logger.debug("[BAN] échec pour %s : %s", query[:40], e)
            return None

    def _geocode_nominatim(self, query: str, city: str) -> Optional[Dict[str, Any]]:
        elapsed = time.time() - self._last_nominatim
        if elapsed < self.nominatim_delay:
            time.sleep(self.nominatim_delay - elapsed)
        try:
            params = {
                "q": f"{query}, {city}, France",
                "format": "json",
                "limit": 1,
            }
            r = requests.get(
                NOMINATIM_SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            r.raise_for_status()
            self._last_nominatim = time.time()
            rows = r.json()
            if not rows:
                return None
            row = rows[0]
            return {
                "longitude": round(float(row["lon"]), 6),
                "latitude": round(float(row["lat"]), 6),
                "provider": "nominatim",
                "score": float(row.get("importance", 0)),
                "label": row.get("display_name"),
            }
        except Exception as e:
            logger.debug("[Nominatim] échec pour %s : %s", query[:40], e)
            return None


def build_dvf_address(row: Dict[str, Any]) -> str:
    """Construit une adresse postale à partir des colonnes DVF."""
    parts = []
    for col in ("adresse_numero", "adresse_suffixe"):
        v = row.get(col)
        if v is not None and str(v).strip() not in ("", "nan"):
            parts.append(str(v).strip())
    voie_parts = []
    for col in ("type_voie", "adresse_nom_voie"):
        v = row.get(col)
        if v is not None and str(v).strip() not in ("", "nan"):
            voie_parts.append(str(v).strip())
    if voie_parts:
        parts.append(" ".join(voie_parts))
    cp = row.get("code_postal")
    if cp is not None and str(cp).strip():
        parts.append(str(int(float(cp))) if str(cp).replace(".", "").isdigit() else str(cp))
    return " ".join(parts).strip()
