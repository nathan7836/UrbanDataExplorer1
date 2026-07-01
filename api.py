from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Optional, Dict
from datetime import datetime
import json
import threading
import time
from pathlib import Path
import logging
import os

from ude_platform.config import DATA_BACKEND, GOLD_JSON, REDIS_URL
from ude_platform.data_access import load_gold_data
from ude_platform import streaming as streaming_module
from ude_platform.freshness import _kafka_available
from ude_platform.lake_storage import check_minio
from ude_platform.sync_databases import sync_gold_to_databases
from ude_platform.governance_catalog import catalogue_non_relationnel, catalogue_relationnel
from ude_platform.enrichment import enrich_all, enrich_arrondissement
from ude_platform.freshness import attach_response_meta, build_freshness
from ude_platform.api_security import (
    ApiKeyMiddleware,
    RateLimitMiddleware,
    governance_quotas_doc,
    get_usage_stats,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_PORT = int(os.getenv("API_PORT", "8001"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Démarrage : listener Redis optionnel (invalidation cache)."""
    t = threading.Thread(target=_redis_cache_listener, daemon=True)
    t.start()
    logger.info("API démarrée — backend données=%s, port=%s", DATA_BACKEND, API_PORT)
    yield


app = FastAPI(
    title="Urban Data Explorer API",
    version="3.0.0",
    description="API multi-services : PostgreSQL, MongoDB, Redis, Data Lake",
    lifespan=lifespan,
)

CACHE_INVALIDATE_CHANNEL = "ude:cache:invalidate"

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:8001,http://127.0.0.1:5500,http://localhost:5500",
).split(",")
app.add_middleware(GZipMiddleware, minimum_size=500)  # Compression des reponses > 500 bytes
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("data/gold")
LATEST_DATA_FILE = DATA_DIR / "real_estate_data_gold_latest.json"
IRIS_GEOJSON_FILE = Path("dashboard/static/data/paris_iris.geojson")
IRIS_METRICS_FILE = Path("dashboard/static/data/paris_iris_metrics.json")


_data_cache: Optional[Dict] = None
_data_cache_mtime: float = 0.0
_cache_version: int = 0


def clear_data_cache() -> None:
    global _data_cache, _data_cache_mtime, _cache_version
    _data_cache = None
    _data_cache_mtime = 0.0
    _cache_version += 1
    logger.info("Cache API invalidé (v%s)", _cache_version)


def load_data() -> Dict:
    global _data_cache, _data_cache_mtime
    try:
        if _data_cache is not None:
            return _data_cache

        _data_cache = load_gold_data(DATA_BACKEND)
        if LATEST_DATA_FILE.exists():
            _data_cache_mtime = LATEST_DATA_FILE.stat().st_mtime
        return _data_cache
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Aucune donnée Gold. Exécutez: python pipeline.py",
        )
    except Exception as e:
        logger.error("Erreur chargement données: %s", e)
        if LATEST_DATA_FILE.exists():
            with open(LATEST_DATA_FILE, encoding="utf-8") as f:
                _data_cache = json.load(f)
            _data_cache["data_backend"] = "json_fallback"
            return _data_cache
        raise HTTPException(status_code=500, detail=str(e))


def load_iris_geojson() -> Dict:
    """Charge le référentiel IRIS Paris embarqué avec l'application."""
    if not IRIS_GEOJSON_FILE.exists():
        raise HTTPException(status_code=503, detail="Référentiel IRIS indisponible")
    with IRIS_GEOJSON_FILE.open(encoding="utf-8") as stream:
        return json.load(stream)


def load_iris_metrics() -> Dict:
    """Charge les indicateurs calculés directement à la maille IRIS."""
    if not IRIS_METRICS_FILE.exists():
        raise HTTPException(status_code=503, detail="Indicateurs IRIS indisponibles")
    with IRIS_METRICS_FILE.open(encoding="utf-8") as stream:
        return json.load(stream)


def _iris_summary(feature: Dict, native: Optional[Dict], annee: Optional[int] = None) -> Dict:
    props = feature.get("properties") or {}
    native = native or {}
    year = str(annee or 2024)
    immobilier = (native.get("immobilier") or {}).get(year) or {}
    revenus = native.get("revenus") or {}
    population = native.get("population") or {}
    logements = native.get("logements") or {}
    vegetation = native.get("vegetation") or {}
    accessibilite = (native.get("accessibilite") or {}).get(year) or {}
    return {
        **props,
        "indicateurs_niveau": "iris",
        "annee_prix": int(year),
        "prix_m2": immobilier.get("prix_m2_median"),
        "nombre_transactions": immobilier.get("nombre_transactions"),
        "surface_mediane_m2": immobilier.get("surface_mediane_m2"),
        "population": population.get("population"),
        "densite_km2": population.get("densite_km2"),
        "niveau_vie_median": revenus.get("niveau_vie_median"),
        "taux_pauvrete": revenus.get("taux_pauvrete"),
        "logements_sociaux_pourcentage": logements.get("logements_sociaux_pourcentage"),
        "nombre_arbres": vegetation.get("nombre_arbres"),
        "mois_revenu_pour_50m2_achat": accessibilite.get("mois_revenu_pour_50m2_achat"),
        "donnees_natives": native,
    }


def _redis_cache_listener() -> None:
    """Consumer distribué : invalide le cache API après pipeline.completed."""
    try:
        import redis  # noqa: F401 — optionnel : pip install redis
    except ImportError:
        logger.info("Redis non installé — cache invalidation locale uniquement (pip install redis)")
        return
    try:
        client = redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = client.pubsub()
        pubsub.subscribe(CACHE_INVALIDATE_CHANNEL)
        for message in pubsub.listen():
            if message.get("type") == "message":
                clear_data_cache()
    except Exception as e:
        logger.warning("Redis cache listener arrêté : %s", e)


@app.get("/health")
async def health():
    """Santé des services (haute disponibilité / load balancer)."""
    pg_ok = mongo_ok = redis_ok = minio_ok = False
    try:
        import psycopg2
        from ude_platform.config import POSTGRES_URL
        conn = psycopg2.connect(POSTGRES_URL, connect_timeout=3)
        conn.close()
        pg_ok = True
    except Exception:
        pass
    try:
        from pymongo import MongoClient
        from ude_platform.config import MONGO_DB, MONGO_GEO_COLLECTION, MONGO_URL
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        mongo_ok = client[MONGO_DB][MONGO_GEO_COLLECTION].estimated_document_count() > 0
    except Exception:
        pass
    redis_ok = streaming_module.check_redis()
    kafka_ok = _kafka_available()
    minio_ok = check_minio()
    gold_ok = LATEST_DATA_FILE.exists()
    status = "healthy" if gold_ok and (pg_ok or mongo_ok) else "degraded"
    return {
        "status": status,
        "services": {
            "postgres": pg_ok,
            "mongo": mongo_ok,
            "redis": redis_ok,
            "kafka": kafka_ok,
            "minio_lake": minio_ok,
            "gold_file": gold_ok,
        },
        "data_backend": DATA_BACKEND,
        "cache_version": _cache_version,
    }


def _last_pipeline_metrics() -> Optional[Dict]:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from ude_platform.config import POSTGRES_READER_URL
        conn = psycopg2.connect(POSTGRES_READER_URL, connect_timeout=3)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT status, finished_at, metrics_json
            FROM pipeline_runs
            ORDER BY finished_at DESC NULLS LAST
            LIMIT 1
            """
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return dict(row) if row else None
    except Exception:
        return None


@app.get("/platform/freshness")
async def platform_freshness():
    """
    Fraîcheur du snapshot + latence requête — argument « analyse à l'instant T ».
  Batch ~1 min ; indicateurs recalculés à chaque appel API.
    """
    t0 = time.perf_counter()
    data = load_data()
    query_ms = round((time.perf_counter() - t0) * 1000, 1)
    body = build_freshness(data, LATEST_DATA_FILE, _cache_version, query_ms)
    last_run = _last_pipeline_metrics()
    if last_run:
        body["batch"]["dernier_run_sql"] = {
            "status": last_run.get("status"),
            "finished_at": last_run.get("finished_at").isoformat()
            if last_run.get("finished_at")
            else None,
            "metrics": last_run.get("metrics_json"),
        }
    return body


@app.get("/platform/governance")
async def platform_governance():
    """Quotas API et gouvernance d'acces (complete /bdd/relationnelle)."""
    out = governance_quotas_doc()
    out["bdd_relationnelle"] = "/bdd/relationnelle"
    out["bdd_non_relationnelle"] = "/bdd/non-relationnelle"
    return out


@app.get("/platform/quota-usage")
async def platform_quota_usage(request: Request):
    """
    Statistiques d'utilisation des quotas API.
    Affiche les requetes effectuees et les blocages par IP.
    """
    from ude_platform.api_security import _client_ip
    ip = _client_ip(request)
    return {
        "your_ip": ip,
        "your_usage": get_usage_stats(ip),
        "global_stats": get_usage_stats(),
        "limits": governance_quotas_doc()["rate_limit"],
    }


@app.get("/platform/metrics")
async def platform_metrics():
    """Indicateurs de performance pipeline et API."""
    t0 = time.perf_counter()
    load_data()
    api_load_ms = round((time.perf_counter() - t0) * 1000, 1)
    last_run = _last_pipeline_metrics()
    return {
        "api": {
            "cache_version": _cache_version,
            "gold_load_ms": api_load_ms,
            "rate_limit": governance_quotas_doc()["rate_limit"],
        },
        "pipeline": last_run,
        "streaming": {
            "redis_ok": streaming_module.check_redis(),
            "stream": os.getenv("REDIS_STREAM", "ude:pipeline:events"),
            "kafka_ok": _kafka_available(),
            "kafka_topic": os.getenv("KAFKA_TOPIC", "ude.pipeline.events"),
        },
    }


@app.get("/platform/streaming")
async def platform_streaming():
    """Catalogue streaming Redis + Kafka (compétence RNCP)."""
    from ude_platform.kafka_streaming import streaming_catalogue

    return {
        "redis": {
            "disponible": streaming_module.check_redis(),
            "stream": os.getenv("REDIS_STREAM", "ude:pipeline:events"),
        },
        **streaming_catalogue(),
    }


@app.get("/platform/status")
async def platform_status():
    """État de la plateforme data (lake, BDD, streaming)."""
    return {
        "architecture": "Medallion + PostgreSQL + MongoDB + MinIO + Redis Streams + Kafka",
        "data_zones": ["data/bronze", "data/silver", "data/gold", "data/export"],
        "health": (await health()),
    }


@app.post("/platform/sync")
async def platform_sync():
    """Synchronise Gold → PostgreSQL + MongoDB (+ MinIO si disponible)."""
    if not LATEST_DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="Gold introuvable")
    result = sync_gold_to_databases(LATEST_DATA_FILE)
    clear_data_cache()
    streaming_module.publish_pipeline_completed({"sync": result})
    return {"sync": result}


@app.get("/bdd/relationnelle")
async def bdd_relationnelle():
    """
    Compétence RNCP — BDD relationnelle : conception, gouvernance, accès universel.
    """
    out = catalogue_relationnel()
    out["api_governance"] = governance_quotas_doc()
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from ude_platform.config import POSTGRES_READER_URL
        conn = psycopg2.connect(POSTGRES_READER_URL, connect_timeout=3)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM governance_access ORDER BY role_name")
        out["governance_matrix"] = cur.fetchall()
        cur.execute(
            "SELECT objet, type, description FROM v_catalogue_donnees ORDER BY type, objet"
        )
        out["catalogue_sql"] = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS n FROM arrondissements")
        out["rows_arrondissements"] = cur.fetchone()["n"]
        cur.close()
        conn.close()
        out["statut"] = "connecte"
    except Exception as e:
        out["statut"] = "deconnecte"
        out["erreur"] = str(e)
        out["action"] = "docker compose up -d postgres && python scripts/sync_platform.py"
    return out


@app.get("/bdd/non-relationnelle")
async def bdd_non_relationnelle():
    """
    Compétence RNCP — BDD non-relationnelle : mise à disposition des données.
    """
    out = catalogue_non_relationnel()
    try:
        from pymongo import MongoClient
        from ude_platform.config import MONGO_DB, MONGO_GEO_COLLECTION, MONGO_URL
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        db = client[MONGO_DB]
        col = db[MONGO_GEO_COLLECTION]
        out["collection"] = MONGO_GEO_COLLECTION
        out["document_count"] = col.count_documents({})
        out["indexes"] = [
            {"name": idx["name"], "keys": idx["key"]}
            for idx in col.list_indexes()
        ]
        meta = db["metadata"].find_one({"_id": "geo_points_catalog"}, {"_id": 0})
        out["metadata"] = meta
        out["types"] = list(col.aggregate([{"$group": {"_id": "$type", "n": {"$sum": 1}}}]))
        out["statut"] = "connecte"
    except Exception as e:
        out["statut"] = "deconnecte"
        out["erreur"] = str(e)
        out["action"] = "docker compose up -d mongo && python scripts/sync_platform.py"
    return out


@app.get("/sql/vues")
async def sql_vues():
    """Liste des vues SQL accessibles en lecture (ude_reader)."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from ude_platform.config import POSTGRES_READER_URL
        conn = psycopg2.connect(POSTGRES_READER_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT table_name AS vue, 'vue_metier' AS type
            FROM information_schema.views
            WHERE table_schema = 'public' AND table_name LIKE 'v_%'
            ORDER BY table_name
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"vues": rows, "acces": "ude_reader (lecture seule)"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"PostgreSQL: {e}")


@app.get("/sql/accessibilite")
async def sql_accessibilite():
    """Exemple requête SQL gouvernance (lecture seule ude_reader)."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from ude_platform.config import POSTGRES_READER_URL
        conn = psycopg2.connect(POSTGRES_READER_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM v_accessibilite_prix_revenu ORDER BY arrondissement")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return {"view": "v_accessibilite_prix_revenu", "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"PostgreSQL: {e}")


@app.get("/mongo/geo-points")
async def mongo_geo_points(
    arrondissement: Optional[int] = None,
    type: Optional[str] = None,
    min_lon: Optional[float] = None,
    min_lat: Optional[float] = None,
    max_lon: Optional[float] = None,
    max_lat: Optional[float] = None,
    limit: int = 500,
):
    """Points géolocalisés (Bronze → Mongo) : DVF, adresses géocodées."""
    if limit < 1 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit entre 1 et 2000")
    bbox_params = [min_lon, min_lat, max_lon, max_lat]
    if any(v is not None for v in bbox_params) and not all(v is not None for v in bbox_params):
        raise HTTPException(
            status_code=400,
            detail="bbox incomplète : fournir min_lon, min_lat, max_lon et max_lat",
        )
    if bbox_params[0] is not None and min_lon >= max_lon:
        raise HTTPException(status_code=400, detail="min_lon doit être < max_lon")
    if bbox_params[1] is not None and min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="min_lat doit être < max_lat")

    query: Dict = {}
    if arrondissement is not None:
        if arrondissement < 1 or arrondissement > 20:
            raise HTTPException(status_code=400, detail="arrondissement entre 1 et 20")
        query["arrondissement"] = arrondissement
    if type:
        query["type"] = type
    if bbox_params[0] is not None:
        query["location.coordinates.0"] = {"$gte": min_lon, "$lte": max_lon}
        query["location.coordinates.1"] = {"$gte": min_lat, "$lte": max_lat}
    try:
        from pymongo import MongoClient
        from ude_platform.config import MONGO_DB, MONGO_GEO_COLLECTION, MONGO_URL
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        col = client[MONGO_DB][MONGO_GEO_COLLECTION]
        docs = list(col.find(query, {"_id": 0}).limit(limit))
        return {
            "collection": MONGO_GEO_COLLECTION,
            "source": "data/bronze (DVF + géocodage), pas le Gold agrégé",
            "count": len(docs),
            "query": query,
            "bbox": (
                {"min_lon": min_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": max_lat}
                if bbox_params[0] is not None
                else None
            ),
            "points": docs,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MongoDB: {e}")


@app.get("/mongo/arrondissements")
async def mongo_arrondissements_deprecated():
    """Déprécié : Gold n'est plus en Mongo. Utilisez /mongo/geo-points et Postgres pour le Gold."""
    raise HTTPException(
        status_code=410,
        detail="Gold retiré de MongoDB. GET /mongo/geo-points (points Bronze) ; Gold via Postgres ou /arrondissements",
    )


@app.get("/mongo/arrondissements/{num}")
async def mongo_arrondissement_deprecated(num: int):
    """Déprécié — filtrer les points : GET /mongo/geo-points?arrondissement={num}"""
    return await mongo_geo_points(arrondissement=num, type=None, limit=500)


@app.get("/mongo/metadata")
async def mongo_metadata():
    """Catalogue de la couche géo NoSQL (stats, source Bronze)."""
    try:
        from pymongo import MongoClient
        from ude_platform.config import MONGO_DB, MONGO_URL
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000)
        meta = client[MONGO_DB]["metadata"].find_one({"_id": "geo_points_catalog"}, {"_id": 0})
        if not meta:
            raise HTTPException(
                status_code=404,
                detail="metadata absente — python scripts/sync_platform.py",
            )
        return meta
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MongoDB: {e}")


@app.get("/")
async def root():
    """Endpoint racine."""
    return {
        "message": "Urban Data Explorer API",
        "version": "3.0.0",
        "dashboard": "/dashboard/",
        "architecture": "Medallion + PostgreSQL + MongoDB + MinIO + Redis",
        "data_layer": "Gold (données clean et enrichies)",
        "endpoints": {
            "/arrondissements": "Liste tous les arrondissements",
            "/arrondissements/{num}": "Détails d'un arrondissement",
            "/iris": "Liste des 992 IRIS et indicateurs calculés à cette maille",
            "/iris/{code_iris}": "Détail des indicateurs natifs d'un IRIS",
            "/iris/geojson": "Contours IRIS officiels IGN-INSEE",
            "/prix-m2": "Prix/m² avec statistiques (min, max, moyen, médian)",
            "/logements-sociaux": "Part de logements sociaux",
            "/typologie": "Typologie des logements",
            "/evolution": "Évolution dans le temps avec tendances",
            "/compare": "Comparer deux arrondissements",
            "/comparaison": "Comparer deux arrondissements (alias)",
            "/prix": "Prix médian par arrondissement et par année (avec variation annuelle %)",
            "/timeline": "Timeline (évolution temporelle) pour un arrondissement",
            "/summary": "Résumé global des données",
            "/pollution": "Pollution / Qualité de l'air",
            "/delits": "Délits enregistrés",
            "/revenus": "Revenus moyens",
            "/densite": "Densité de population",
            "/sources": "Traçabilité des sources de données",
            "/bdd/relationnelle": "Compétence BDD relationnelle (gouvernance + catalogue)",
            "/bdd/non-relationnelle": "Compétence BDD non-relationnelle (mise à disposition)",
            "/sql/vues": "Vues SQL lecture seule",
            "/sql/accessibilite": "Exemple vue accessibilité prix/revenu",
            "/accessibilite": "Accessibilité logement (mois revenu / 50 m²)",
            "/loyers": "Loyers estimés par arrondissement",
            "/mongo/geo-points": "Points géolocalisés Bronze → Mongo (NoSQL)",
            "/platform/freshness": "Fraîcheur snapshot + latence (analyse instant T)",
            "/platform/governance": "Auth API, quotas, rôles SQL",
            "/platform/metrics": "Métriques pipeline et latence API",
        }
    }


@app.get("/sources")
async def get_sources():
    """Retourne le rapport d'intégration et les métadonnées par indicateur."""
    data = load_data()
    sample_sources = {}
    for arr in data.get("arrondissements", [])[:1]:
        sample_sources = arr.get("_sources", {})
        break
    return {
        "integration_report": data.get("integration_report", {}),
        "sources_updated_at": data.get("sources_updated_at"),
        "timestamp": data.get("timestamp"),
        "indicateurs_exemple": sample_sources,
    }


@app.get("/iris")
async def get_iris(arrondissement: Optional[int] = None, annee: Optional[int] = None):
    """Liste le référentiel IRIS et ses indicateurs calculés à cette maille."""
    if arrondissement is not None and not 1 <= arrondissement <= 20:
        raise HTTPException(status_code=400, detail="arrondissement entre 1 et 20")
    iris = load_iris_geojson()
    metrics_payload = load_iris_metrics()
    metrics = metrics_payload.get("iris", {})
    rows = []
    for feature in iris.get("features", []):
        numéro = feature.get("properties", {}).get("arrondissement")
        if arrondissement is not None and numéro != arrondissement:
            continue
        code = feature.get("properties", {}).get("code_iris")
        rows.append(_iris_summary(feature, metrics.get(code), annee))
    return {
        "maille": "IRIS",
        "nombre": len(rows),
        "annee": annee,
        "source": metrics_payload.get("sources", {}),
        "avertissement": (
            "Les indicateurs retournés sont calculés à l'IRIS. Une valeur null "
            "signifie que la source est absente ou que le seuil minimal de trois "
            "transactions DVF n'est pas atteint."
        ),
        "iris": rows,
    }


@app.get("/iris/geojson")
async def get_iris_geojson(arrondissement: Optional[int] = None):
    """Retourne les contours IRIS officiels, filtrables par arrondissement."""
    if arrondissement is not None and not 1 <= arrondissement <= 20:
        raise HTTPException(status_code=400, detail="arrondissement entre 1 et 20")
    iris = load_iris_geojson()
    features = iris.get("features", [])
    if arrondissement is not None:
        features = [
            feature
            for feature in features
            if feature.get("properties", {}).get("arrondissement") == arrondissement
        ]
    return {
        "type": "FeatureCollection",
        "metadata": iris.get("metadata", {}),
        "features": features,
    }


@app.get("/iris/{code_iris}")
async def get_iris_detail(code_iris: str, annee: Optional[int] = None):
    """Retourne les indicateurs natifs d'un IRIS et le parent pour contexte."""
    iris = load_iris_geojson()
    feature = next(
        (
            item
            for item in iris.get("features", [])
            if item.get("properties", {}).get("code_iris") == code_iris
        ),
        None,
    )
    if feature is None:
        raise HTTPException(status_code=404, detail="IRIS non trouvé")
    numéro = feature["properties"]["arrondissement"]
    metrics_payload = load_iris_metrics()
    native = metrics_payload.get("iris", {}).get(code_iris)
    data = load_data()
    parent = next(
        (
            item
            for item in enrich_all(data.get("arrondissements", []), annee)
            if item["arrondissement"] == numéro
        ),
        None,
    )
    return {
        **_iris_summary(feature, native, annee),
        "donnees_arrondissement_parent": parent,
        "source": metrics_payload.get("sources", {}),
    }


@app.get("/arrondissements")
async def get_arrondissements(annee: Optional[int] = None):
    """Retourne la liste de tous les arrondissements avec données enrichies."""
    t0 = time.perf_counter()
    data = load_data()
    arrs = enrich_all(data.get("arrondissements", []), annee)
    query_ms = round((time.perf_counter() - t0) * 1000, 1)
    return attach_response_meta(
        {
            "arrondissements": arrs,
            "data_backend": data.get("data_backend"),
            "annee": annee,
        },
        data,
        LATEST_DATA_FILE,
        _cache_version,
        query_ms,
    )


@app.get("/arrondissements/{arr_num}")
async def get_arrondissement(arr_num: int):
    """Retourne les données détaillées d'un arrondissement."""
    if arr_num < 1 or arr_num > 20:
        raise HTTPException(status_code=400, detail="Numéro d'arrondissement invalide (1-20)")
    
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    arr_data = next((arr for arr in arrondissements if arr["arrondissement"] == arr_num), None)
    
    if not arr_data:
        raise HTTPException(status_code=404, detail=f"Arrondissement {arr_num} non trouvé")
    
    return enrich_arrondissement(arr_data)


@app.get("/prix-m2")
async def get_prix_m2(arrondissement: Optional[int] = None, date: Optional[str] = None):
    """
    Retourne les prix/m² médians (données Gold avec statistiques).
    
    Query params:
    - arrondissement: Filtrer par arrondissement (1-20)
    - date: Filtrer par date (format: YYYY-MM)
    """
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        stats = arr.get("statistiques", {})
        prix_historique = arr.get("prix_m2_historique", [])
        
        if date:
            prix_historique = [p for p in prix_historique if p["date"].startswith(date)]
        
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "prix_m2_actuel": stats.get("prix_m2_actuel"),
            "prix_m2_median": stats.get("prix_m2_median"),
            "prix_m2_min": stats.get("prix_m2_min"),
            "prix_m2_max": stats.get("prix_m2_max"),
            "prix_m2_moyen": stats.get("prix_m2_moyen"),
            "historique": prix_historique,
            "evolution": arr.get("evolution_calculee")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/prix")
async def get_prix(annee: Optional[int] = None, arrondissement: Optional[int] = None):
    """
    Retourne le prix médian par arrondissement et par année.
    
    Query params:
    - annee: Filtrer par année (ex: 2023)
    - arrondissement: Filtrer par arrondissement (1-20)
    """
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        evolution_annuelle = arr.get("evolution_annuelle", [])
        
        if annee:
            # Filtrer par année
            evolution_filtered = [e for e in evolution_annuelle if e.get("annee") == annee]
            if not evolution_filtered:
                continue
            
            for evol in evolution_filtered:
                result.append({
                    "arrondissement": arr["arrondissement"],
                    "nom": arr["nom"],
                    "annee": evol.get("annee"),
                    "prix_m2_median": evol.get("prix_m2_median"),
                    "nombre_transactions": evol.get("nombre_transactions")
                })
        else:
            # Retourner toutes les années
            for evol in evolution_annuelle:
                # Calculer la variation annuelle
                annee_courante = evol.get("annee")
                prix_courant = evol.get("prix_m2_median")
                
                # Trouver l'année précédente
                evolution_sorted = sorted(evolution_annuelle, key=lambda x: x.get("annee", 0))
                index_courant = next((i for i, e in enumerate(evolution_sorted) if e.get("annee") == annee_courante), -1)
                
                variation_annuelle = None
                if index_courant > 0:
                    prix_precedent = evolution_sorted[index_courant - 1].get("prix_m2_median")
                    if prix_precedent and prix_precedent > 0:
                        variation_annuelle = round(((prix_courant - prix_precedent) / prix_precedent) * 100, 2)
                
                result.append({
                    "arrondissement": arr["arrondissement"],
                    "nom": arr["nom"],
                    "annee": annee_courante,
                    "prix_m2_median": prix_courant,
                    "nombre_transactions": evol.get("nombre_transactions"),
                    "variation_annuelle_pourcentage": variation_annuelle
                })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/logements-sociaux")
async def get_logements_sociaux(arrondissement: Optional[int] = None):
    """Part de logements sociaux + série d'évolution 2018–2024."""
    data = load_data()
    arrondissements = enrich_all(data.get("arrondissements", []))
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "logements_sociaux_pourcentage": arr.get("logements_sociaux_pourcentage", 0),
            "evolution": arr.get("logements_sociaux_evolution", []),
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/loyers")
async def get_loyers(arrondissement: Optional[int] = None, annee: Optional[int] = None):
    """Loyers estimés (m²/mois) et ratio avec revenus."""
    data = load_data()
    result = []
    for arr in enrich_all(data.get("arrondissements", []), annee):
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "loyers": arr.get("loyers", {}),
            "accessibilite_logement": arr.get("accessibilite_logement", {}),
        })
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/accessibilite")
async def get_accessibilite(arrondissement: Optional[int] = None, annee: Optional[int] = None):
    """Indicateurs accessibilité logement (mois de revenu pour 50 m²)."""
    data = load_data()
    rows = []
    for arr in enrich_all(data.get("arrondissements", []), annee):
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        rows.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            **(arr.get("accessibilite_logement") or {}),
        })
    return {"data": rows, "annee": annee, "timestamp": data.get("timestamp")}


@app.get("/typologie")
async def get_typologie(arrondissement: Optional[int] = None):
    """Retourne la répartition détaillée par typologie de logements (appartement/maison, nombre de pièces)."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        typologie = arr.get("typologie", {})
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "type_logement": typologie.get("type_logement", {}),
            "repartition_pieces": typologie.get("repartition_pieces", {}),
            "detail_pieces": typologie.get("detail_pieces", {}),
            "statistiques": typologie.get("statistiques", {})
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/evolution")
async def get_evolution(arrondissement: Optional[int] = None):
    """Retourne l'évolution des prix dans le temps (données Gold enrichies)."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "evolution_annuelle": arr.get("evolution_annuelle", []),
            "evolution_calculee": arr.get("evolution_calculee"),
            "tendance_annuelle": arr.get("tendance_annuelle")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/comparaison")
async def comparaison_arrondissements(arr1: int, arr2: int):
    """
    Compare deux arrondissements (alias de /compare).
    
    Query params:
    - arr1: Numéro du premier arrondissement (1-20)
    - arr2: Numéro du deuxième arrondissement (1-20)
    """
    return await compare_arrondissements_internal(arr1, arr2)


@app.get("/compare")
async def compare_arrondissements(arr1: int, arr2: int):
    """
    Compare deux arrondissements.
    
    Query params:
    - arr1: Numéro du premier arrondissement (1-20)
    - arr2: Numéro du deuxième arrondissement (1-20)
    """
    return await compare_arrondissements_internal(arr1, arr2)


async def compare_arrondissements_internal(arr1: int, arr2: int):
    """
    Compare deux arrondissements.
    
    Query params:
    - arr1: Numéro du premier arrondissement (1-20)
    - arr2: Numéro du deuxième arrondissement (1-20)
    """
    if arr1 < 1 or arr1 > 20 or arr2 < 1 or arr2 > 20:
        raise HTTPException(status_code=400, detail="Numéro d'arrondissement invalide (1-20)")
    
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    arr1_data = next((arr for arr in arrondissements if arr["arrondissement"] == arr1), None)
    arr2_data = next((arr for arr in arrondissements if arr["arrondissement"] == arr2), None)
    
    if not arr1_data or not arr2_data:
        raise HTTPException(status_code=404, detail="Arrondissement non trouvé")
    
    # Récupérer les statistiques (données Gold)
    stats1 = arr1_data.get("statistiques", {})
    stats2 = arr2_data.get("statistiques", {})
    
    latest_prix1 = stats1.get("prix_m2_actuel")
    latest_prix2 = stats2.get("prix_m2_actuel")
    
    comparison = {
        "arrondissement_1": {
            "num": arr1,
            "nom": arr1_data["nom"],
            "statistiques": stats1,
            "prix_m2_actuel": latest_prix1,
            "logements_sociaux_pourcentage": arr1_data.get("logements_sociaux_pourcentage", 0),
            "typologie": arr1_data.get("typologie", {}),
            "evolution": arr1_data.get("evolution_calculee"),
            "tendance_annuelle": arr1_data.get("tendance_annuelle")
        },
        "arrondissement_2": {
            "num": arr2,
            "nom": arr2_data["nom"],
            "statistiques": stats2,
            "prix_m2_actuel": latest_prix2,
            "logements_sociaux_pourcentage": arr2_data.get("logements_sociaux_pourcentage", 0),
            "typologie": arr2_data.get("typologie", {}),
            "evolution": arr2_data.get("evolution_calculee"),
            "tendance_annuelle": arr2_data.get("tendance_annuelle")
        },
        "differences": {
            "prix_m2_diff": round(latest_prix1 - latest_prix2, 2) if latest_prix1 and latest_prix2 else None,
            "prix_m2_diff_pourcentage": round(((latest_prix1 - latest_prix2) / latest_prix2 * 100), 2) if latest_prix1 and latest_prix2 else None,
            "logements_sociaux_diff": round(arr1_data.get("logements_sociaux_pourcentage", 0) - arr2_data.get("logements_sociaux_pourcentage", 0), 2)
        }
    }
    
    return comparison


@app.get("/summary")
async def get_summary():
    """Retourne un résumé global des données Gold."""
    data = load_data()
    summary = data.get("summary", {})
    arrondissements = data.get("arrondissements", [])
    
    # Calculer des statistiques globales
    all_prix_actuels = [
        arr.get("statistiques", {}).get("prix_m2_actuel")
        for arr in arrondissements
        if arr.get("statistiques", {}).get("prix_m2_actuel")
    ]
    
    global_stats = {}
    if all_prix_actuels:
        global_stats = {
            "prix_m2_moyen_global": round(sum(all_prix_actuels) / len(all_prix_actuels), 2),
            "prix_m2_min_global": min(all_prix_actuels),
            "prix_m2_max_global": max(all_prix_actuels),
            "prix_m2_median_global": sorted(all_prix_actuels)[len(all_prix_actuels) // 2]
        }
    
    return {
        "summary": summary,
        "global_stats": global_stats,
        "nb_arrondissements": len(arrondissements),
        "timestamp": data.get("timestamp"),
        "generated_at": data.get("generated_at")
    }


@app.get("/pollution")
async def get_pollution(arrondissement: Optional[int] = None):
    """Retourne les données de pollution / qualité de l'air."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        pollution = arr.get("pollution_qualite_air", {})
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "indice_atmo": pollution.get("indice_atmo"),
            "pm25_moyen": pollution.get("pm25_moyen"),
            "pm10_moyen": pollution.get("pm10_moyen"),
            "no2_moyen": pollution.get("no2_moyen"),
            "qualite": pollution.get("qualite"),
            "date_mesure": pollution.get("date_mesure")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/delits")
async def get_delits(arrondissement: Optional[int] = None):
    """Retourne les données de délits enregistrés."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        delits = arr.get("delits_enregistres", {})
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "total_delits": delits.get("total_delits"),
            "delits_par_1000_habitants": delits.get("delits_par_1000_habitants"),
            "cambriolages": delits.get("cambriolages"),
            "vols": delits.get("vols"),
            "violences": delits.get("violences"),
            "annee": delits.get("annee")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/revenus")
async def get_revenus(arrondissement: Optional[int] = None):
    """Retourne les données de revenus moyens."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        revenus = arr.get("revenus_moyens", {})
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "revenu_median_menage": revenus.get("revenu_median_menage"),
            "revenu_moyen_menage": revenus.get("revenu_moyen_menage"),
            "niveau_vie_median": revenus.get("niveau_vie_median"),
            "annee": revenus.get("annee")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/densite")
async def get_densite(arrondissement: Optional[int] = None):
    """Retourne les données de densité de population."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        densite = arr.get("densite_population", {})
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "population": densite.get("population"),
            "densite_km2": densite.get("densite_km2"),
            "superficie_km2": densite.get("superficie_km2"),
            "annee": densite.get("annee")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/vegetation")
async def get_vegetation(arrondissement: Optional[int] = None):
    """Retourne les données de végétation et arbres."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        vegetation = arr.get("vegetation_arbres", {})
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "nombre_arbres": vegetation.get("nombre_arbres"),
            "surface_espaces_verts_ha": vegetation.get("surface_espaces_verts_ha"),
            "pourcentage_vegetation": vegetation.get("pourcentage_vegetation"),
            "arbres_par_km2": vegetation.get("arbres_par_km2"),
            "parcs_et_jardins": vegetation.get("parcs_et_jardins"),
            "annee": vegetation.get("annee")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/transports")
async def get_transports(arrondissement: Optional[int] = None):
    """Retourne les données de transports publics."""
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    result = []
    for arr in arrondissements:
        if arrondissement and arr["arrondissement"] != arrondissement:
            continue
        
        transports = arr.get("transports_publics", {})
        result.append({
            "arrondissement": arr["arrondissement"],
            "nom": arr["nom"],
            "stations_metro": transports.get("stations_metro"),
            "stations_rer": transports.get("stations_rer"),
            "arrets_bus": transports.get("arrets_bus"),
            "lignes_metro": transports.get("lignes_metro"),
            "lignes_bus": transports.get("lignes_bus"),
            "total_transports": transports.get("total_transports"),
            "annee": transports.get("annee")
        })
    
    return {"data": result, "timestamp": data.get("timestamp")}


@app.get("/timeline")
async def get_timeline(arr: int):
    """
    Retourne la timeline (évolution temporelle) pour un arrondissement.
    
    Query params:
    - arr: Numéro de l'arrondissement (1-20)
    """
    if arr < 1 or arr > 20:
        raise HTTPException(status_code=400, detail="Numéro d'arrondissement invalide (1-20)")
    
    data = load_data()
    arrondissements = data.get("arrondissements", [])
    
    arr_data = next((a for a in arrondissements if a["arrondissement"] == arr), None)
    
    if not arr_data:
        raise HTTPException(status_code=404, detail=f"Arrondissement {arr} non trouvé")
    
    # Récupérer l'historique des prix
    prix_historique = arr_data.get("prix_m2_historique", [])
    
    # Organiser par année et mois
    timeline_data = []
    for prix in prix_historique:
        date_str = prix.get("date", "")
        if date_str:
            year = int(date_str.split("-")[0])
            month = int(date_str.split("-")[1])
            timeline_data.append({
                "date": date_str,
                "annee": year,
                "mois": month,
                "prix_m2": prix.get("prix_m2")
            })
    
    # Trier par date
    timeline_data.sort(key=lambda x: (x["annee"], x["mois"]))
    
    # Calculer les variations
    for i in range(1, len(timeline_data)):
        prix_actuel = timeline_data[i]["prix_m2"]
        prix_precedent = timeline_data[i-1]["prix_m2"]
        if prix_precedent and prix_precedent > 0:
            timeline_data[i]["variation_mensuelle"] = round(((prix_actuel - prix_precedent) / prix_precedent) * 100, 2)
        else:
            timeline_data[i]["variation_mensuelle"] = None
    
    return {
        "arrondissement": arr,
        "nom": arr_data["nom"],
        "timeline": timeline_data,
        "evolution_calculee": arr_data.get("evolution_calculee"),
        "tendance_annuelle": arr_data.get("tendance_annuelle")
    }


DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard"
if DASHBOARD_DIR.is_dir():
    app.mount(
        "/dashboard",
        StaticFiles(directory=str(DASHBOARD_DIR), html=True),
        name="dashboard",
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = API_PORT
    logger.info("Écoute sur http://127.0.0.1:%s — docs: /docs", port)
    uvicorn.run(app, host=host, port=port)
