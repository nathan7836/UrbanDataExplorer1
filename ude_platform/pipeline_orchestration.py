"""
Orchestration pipeline : métriques de performance, sync BDD, lake, streaming.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict

from ude_platform.lake_storage import sync_lake_to_minio
from ude_platform.parquet_lake import export_prix_partitioned
from ude_platform.streaming import publish_pipeline_completed
from ude_platform.sync_databases import load_gold, sync_gold_to_databases

logger = logging.getLogger(__name__)


def run_step(name: str, fn: Callable[[], bool], metrics: Dict[str, Any]) -> bool:
    t0 = time.perf_counter()
    ok = fn()
    metrics["steps"][name] = {
        "ok": ok,
        "duration_sec": round(time.perf_counter() - t0, 2),
    }
    return ok


def finalize_pipeline(gold_path=None) -> Dict[str, Any]:
    """Post-traitement après Gold : Parquet, Postgres, Mongo, MinIO, Redis."""
    metrics: Dict[str, Any] = {"steps": {}, "started_at": time.time()}
    gold = load_gold(gold_path)

    export_prix_partitioned(gold)
    metrics["steps"]["parquet_partitioned"] = {"ok": True}

    sync_result = sync_gold_to_databases(gold_path)
    metrics["steps"]["postgres"] = {"ok": sync_result.get("postgres", False)}
    metrics["steps"]["mongo_geo_points"] = {"ok": sync_result.get("mongo_geo_points", False)}

    uploaded = sync_lake_to_minio()
    metrics["steps"]["minio_lake"] = {"ok": uploaded > 0, "files": uploaded}

    metrics["finished_at"] = time.time()
    metrics["total_sec"] = round(metrics["finished_at"] - metrics["started_at"], 2)
    publish_pipeline_completed(metrics)

    if gold_path:
        path = Path(gold_path)
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload.setdefault("integration_report", {})["pipeline_finalize"] = metrics
                path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("[Orchestration] Métriques non persistées dans Gold : %s", e)

    logger.info("[Orchestration] Finalisation : %s", metrics)
    return metrics
