"""
Uniformisation des formats et politique de gestion des valeurs manquantes (NA).
Utilisé par public_data_integrations.py et data_processor.py.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

import pandas as pd

# Politique NA documentée pour la soutenance :
# - champs obligatoires (date, prix) : exclusion de la ligne (drop)
# - champs optionnels (indicateurs secondaires) : null explicite
# - pourcentages / compteurs invalides : exclusion ou borne selon le contexte
NA_POLICY = {
    "required_field": "drop",
    "optional_field": "null",
    "invalid_numeric": "drop",
}

T = TypeVar("T", bound=Dict[str, Any])


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() in ("", "nan", "NaN", "None"):
        return True
    return False


def normalize_date(value: Any) -> Optional[str]:
    """Retourne une date ISO YYYY-MM-DD ou None."""
    if is_missing(value):
        return None
    try:
        ts = pd.to_datetime(value, errors="coerce")
        if pd.isna(ts):
            return None
        return ts.strftime("%Y-%m-%d")
    except Exception:
        return None


def normalize_price(value: Any, min_val: float = 1000.0, max_val: float = 50000.0) -> Optional[float]:
    """Prix au m² en euros, 2 décimales."""
    if is_missing(value):
        return None
    try:
        p = round(float(value), 2)
        if min_val <= p <= max_val:
            return p
    except (TypeError, ValueError):
        pass
    return None


def normalize_surface_m2(value: Any, min_val: float = 9.0, max_val: float = 500.0) -> Optional[float]:
    """Surface en m², 1 décimale."""
    if is_missing(value):
        return None
    try:
        s = round(float(value), 1)
        if min_val <= s <= max_val:
            return s
    except (TypeError, ValueError):
        pass
    return None


def normalize_percent(value: Any) -> Optional[float]:
    if is_missing(value):
        return None
    try:
        p = round(float(value), 2)
        return max(0.0, min(100.0, p))
    except (TypeError, ValueError):
        return None


def normalize_year(value: Any, min_year: int = 2018, max_year: int = 2030) -> Optional[int]:
    if is_missing(value):
        return None
    try:
        y = int(value)
        if min_year <= y <= max_year:
            return y
    except (TypeError, ValueError):
        pass
    return None


def dedupe_records(records: List[T], key_fn: Callable[[T], Any]) -> List[T]:
    """Supprime les doublons en conservant la première occurrence."""
    seen = set()
    out: List[T] = []
    for item in records:
        key = key_fn(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def apply_na_policy_optional(value: Any, default: Any = None) -> Any:
    """Champs optionnels : null si manquant."""
    return default if is_missing(value) else value


def build_data_quality(missing_fields: List[str], imputed_fields: List[str]) -> Dict[str, Any]:
    return {
        "na_policy": NA_POLICY,
        "missing_fields": missing_fields,
        "imputed_fields": imputed_fields,
        "processed_at": datetime.now().isoformat(),
    }
