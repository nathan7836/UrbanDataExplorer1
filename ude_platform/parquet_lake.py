"""
Mise en scène analytique — Parquet partitionné par année (perf + grande échelle).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from ude_platform.config import DATA_ROOT

logger = logging.getLogger(__name__)

PARTITION_DIR = DATA_ROOT / "gold" / "parquet" / "prix_annuel"


def export_prix_partitioned(gold: Dict[str, Any]) -> Path:
    """Écrit prix_annuel partitionné annee=YYYY (Hive-style)."""
    rows: List[dict] = []
    for arr in gold.get("arrondissements", []):
        for evol in arr.get("evolution_annuelle", []):
            rows.append({
                "arrondissement": arr["arrondissement"],
                "nom": arr.get("nom"),
                "code_insee": arr.get("code_insee"),
                "annee": int(evol["annee"]),
                "prix_m2_median": evol.get("prix_m2_median"),
                "nombre_transactions": evol.get("nombre_transactions"),
            })
    if not rows:
        logger.warning("[Parquet] Aucune ligne prix à exporter")
        return PARTITION_DIR

    df = pd.DataFrame(rows)
    PARTITION_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PARTITION_DIR, partition_cols=["annee"], index=False, engine="pyarrow")
    logger.info("[Parquet] Partitionné : %s (annees %s)", PARTITION_DIR, df["annee"].unique().tolist())
    return PARTITION_DIR


def read_partitioned_prix(annee: int = None) -> pd.DataFrame:
    """Lecture analytique partitionnée (pyarrow)."""
    path = PARTITION_DIR
    if not path.exists():
        return pd.DataFrame()
    if annee is not None:
        sub = path / f"annee={annee}"
        if sub.exists():
            return pd.read_parquet(sub)
    return pd.read_parquet(path)
