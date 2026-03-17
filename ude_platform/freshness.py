"""Fraicheur des donnees et metadonnees analyse a l'instant T."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import time

from ude_platform import streaming as streaming_module

# Cache pour eviter les checks Kafka repetitifs (30s timeout)
_kafka_cache = {"available": None, "checked_at": 0}
_KAFKA_CACHE_TTL = 60  # Verifier Kafka max 1 fois par minute


def _kafka_available() -> bool:
    """Verifie si Kafka est disponible (avec cache)."""
    now = time.time()
    if _kafka_cache["available"] is not None and (now - _kafka_cache["checked_at"]) < _KAFKA_CACHE_TTL:
        return _kafka_cache["available"]

    try:
        from ude_platform.kafka_streaming import check_kafka
        result = check_kafka()
    except Exception:
        result = False

    _kafka_cache["available"] = result
    _kafka_cache["checked_at"] = now
    return result


def _parse_iso(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _age_human(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    if seconds < 60:
        return f"{int(seconds)} s"
    if seconds < 3600:
        return f"{int(seconds // 60)} min"
    if seconds < 86400:
        return f"{int(seconds // 3600)} h"
    return f"{int(seconds // 86400)} j"


def build_freshness(
    data: Dict[str, Any],
    gold_path: Path,
    cache_version: int,
    query_latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Construit le bloc fraîcheur pour l'API et le dashboard."""
    now = datetime.now(timezone.utc)
    generated_at = data.get("generated_at") or data.get("timestamp")
    sources_at = data.get("sources_updated_at")
    gen_dt = _parse_iso(generated_at)
    src_dt = _parse_iso(sources_at)

    gold_mtime = None
    gold_age_sec = None
    if gold_path.exists():
        gold_mtime = datetime.fromtimestamp(gold_path.stat().st_mtime, tz=timezone.utc)
        gold_age_sec = (now - gold_mtime).total_seconds()

    snapshot_age_sec = None
    if gen_dt:
        if gen_dt.tzinfo is None:
            gen_dt = gen_dt.replace(tzinfo=timezone.utc)
        snapshot_age_sec = (now - gen_dt).total_seconds()

    integration = data.get("integration_report") or {}
    batch_steps = integration.get("pipeline_finalize") or {}

    return {
        "mode_analyse": "instant_t_sur_snapshot",
        "description": (
            "Batch (~1 min) pour rafraîchir le Gold ; à chaque requête API, "
            "les indicateurs métier sont recalculés sur le snapshot le plus récent."
        ),
        "snapshot": {
            "generated_at": generated_at,
            "sources_updated_at": sources_at,
            "age_seconds": round(snapshot_age_sec, 1) if snapshot_age_sec is not None else None,
            "age_human": _age_human(snapshot_age_sec),
            "gold_file_mtime": gold_mtime.isoformat() if gold_mtime else None,
            "gold_file_age_seconds": round(gold_age_sec, 1) if gold_age_sec is not None else None,
        },
        "batch": {
            "type": "medallion_periodique",
            "duree_typique_sec": 60,
            "duree_transformation_seule_sec": 0.2,
            "planification": ".github/workflows/pipeline-scheduled.yml",
            "derniere_finalisation": batch_steps if batch_steps else None,
        },
        "streaming": {
            "technologie": "Redis Streams + Apache Kafka",
            "role": "propagation post-batch (pipeline.completed → invalidation cache API)",
            "redis_disponible": streaming_module.check_redis(),
            "kafka_disponible": _kafka_available(),
            "temps_reel_analytique": False,
        },
        "api": {
            "data_backend": data.get("data_backend"),
            "cache_version": cache_version,
            "query_latency_ms": query_latency_ms,
            "latence_cible_ms": 500,
        },
        "queried_at": now.isoformat(),
    }


def attach_response_meta(
    payload: Dict[str, Any],
    data: Dict[str, Any],
    gold_path: Path,
    cache_version: int,
    query_latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Ajoute timestamp et fraîcheur à une réponse API."""
    out = dict(payload)
    out["timestamp"] = data.get("timestamp")
    out["generated_at"] = data.get("generated_at")
    out["sources_updated_at"] = data.get("sources_updated_at")
    out["freshness"] = build_freshness(data, gold_path, cache_version, query_latency_ms)
    return out
