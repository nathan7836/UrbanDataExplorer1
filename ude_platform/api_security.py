"""Authentification optionnelle et quotas API (gouvernance)."""

from __future__ import annotations

import os
import time
from collections import defaultdict
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

UDE_API_KEY = os.getenv("UDE_API_KEY", "").strip()
API_RATE_LIMIT = int(os.getenv("API_RATE_LIMIT", "100"))  # requetes / minute / IP
API_RATE_WINDOW_SEC = int(os.getenv("API_RATE_WINDOW_SEC", "60"))
API_DAILY_LIMIT = int(os.getenv("API_DAILY_LIMIT", "500"))  # requetes / jour / IP (strict)

# Limites specifiques par type d'endpoint (par minute)
ENDPOINT_LIMITS = {
    "/export": 5,         # Exports tres limites (fichiers lourds)
    "/geo-points": 10,    # Points geo (requetes couteuses)
    "/comparaison": 15,   # Comparaisons
    "/arrondissements": 20,  # Donnees principales
    "/timeline": 15,      # Timeline
    "/ranking": 15,       # Classements
}

PUBLIC_PATHS = {
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/platform/freshness",
    "/dashboard",
}

# Stockage des statistiques d'utilisation
_usage_stats: Dict[str, Dict] = defaultdict(lambda: {
    "requests_today": 0,
    "last_reset": datetime.now().date().isoformat(),
    "blocked_count": 0,
})


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _extract_api_key(request: Request) -> Optional[str]:
    header = request.headers.get("x-api-key") or request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.headers.get("x-api-key") or request.query_params.get("api_key")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Quota avance par IP : limite par minute, par jour, et par endpoint."""

    def __init__(self, app, limit: int = API_RATE_LIMIT, window_sec: int = API_RATE_WINDOW_SEC):
        super().__init__(app)
        self.limit = limit
        self.window_sec = window_sec
        self.daily_limit = API_DAILY_LIMIT
        self._hits: Dict[str, List[float]] = defaultdict(list)
        self._daily_hits: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "date": ""})
        self._endpoint_hits: Dict[str, List[float]] = defaultdict(list)

    def _get_endpoint_limit(self, path: str) -> Optional[int]:
        """Retourne la limite specifique pour un endpoint."""
        for prefix, limit in ENDPOINT_LIMITS.items():
            if path.startswith(prefix):
                return limit
        return None

    def _allow_minute(self, key: str) -> Tuple[bool, int]:
        """Verifie la limite par minute."""
        now = time.time()
        window_start = now - self.window_sec
        hits = [t for t in self._hits[key] if t > window_start]
        if len(hits) >= self.limit:
            self._hits[key] = hits
            return False, 0
        hits.append(now)
        self._hits[key] = hits
        return True, self.limit - len(hits)

    def _allow_daily(self, ip: str) -> Tuple[bool, int]:
        """Verifie la limite journaliere."""
        today = datetime.now().date().isoformat()
        daily = self._daily_hits[ip]
        if daily["date"] != today:
            daily["count"] = 0
            daily["date"] = today
        if daily["count"] >= self.daily_limit:
            return False, 0
        daily["count"] += 1
        return True, self.daily_limit - daily["count"]

    def _allow_endpoint(self, ip: str, path: str) -> Tuple[bool, int]:
        """Verifie la limite specifique par endpoint."""
        endpoint_limit = self._get_endpoint_limit(path)
        if endpoint_limit is None:
            return True, -1

        key = f"{ip}:{path.split('/')[1]}"
        now = time.time()
        window_start = now - self.window_sec
        hits = [t for t in self._endpoint_hits[key] if t > window_start]
        if len(hits) >= endpoint_limit:
            self._endpoint_hits[key] = hits
            return False, 0
        hits.append(now)
        self._endpoint_hits[key] = hits
        return True, endpoint_limit - len(hits)

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        # Chemins publics sans limite
        if path in PUBLIC_PATHS or path.startswith("/dashboard"):
            return await call_next(request)

        ip = _client_ip(request)

        # Verification limite journaliere
        daily_ok, daily_remaining = self._allow_daily(ip)
        if not daily_ok:
            _usage_stats[ip]["blocked_count"] += 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Quota journalier depasse : {self.daily_limit} requetes / jour",
                    "retry_after": "demain",
                    "type": "daily_limit",
                },
                headers={
                    "Retry-After": "86400",
                    "X-RateLimit-Daily-Limit": str(self.daily_limit),
                },
            )

        # Verification limite par endpoint
        endpoint_ok, endpoint_remaining = self._allow_endpoint(ip, path)
        if not endpoint_ok:
            endpoint_limit = self._get_endpoint_limit(path)
            _usage_stats[ip]["blocked_count"] += 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Limite endpoint depassee : {endpoint_limit} requetes / {self.window_sec}s",
                    "retry_after_sec": self.window_sec,
                    "type": "endpoint_limit",
                },
                headers={
                    "Retry-After": str(self.window_sec),
                    "X-RateLimit-Endpoint-Limit": str(endpoint_limit),
                },
            )

        # Verification limite par minute
        minute_ok, minute_remaining = self._allow_minute(ip)
        if not minute_ok:
            _usage_stats[ip]["blocked_count"] += 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Quota depasse : {self.limit} requetes / {self.window_sec}s par IP",
                    "retry_after_sec": self.window_sec,
                    "type": "minute_limit",
                },
                headers={
                    "Retry-After": str(self.window_sec),
                    "X-RateLimit-Limit": str(self.limit),
                },
            )

        # Mise a jour des stats
        _usage_stats[ip]["requests_today"] = self._daily_hits[ip]["count"]

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(minute_remaining)
        response.headers["X-RateLimit-Daily-Remaining"] = str(daily_remaining)
        return response


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Clé API optionnelle (UDE_API_KEY). Si vide, auth désactivée (démo locale)."""

    async def dispatch(self, request: Request, call_next: Callable):
        if not UDE_API_KEY or request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        key = _extract_api_key(request)
        if key != UDE_API_KEY:
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Clé API requise : header X-API-Key ou ?api_key= (voir /platform/governance)",
                },
            )
        return await call_next(request)


def governance_quotas_doc() -> Dict[str, object]:
    return {
        "auth": {
            "active": bool(UDE_API_KEY),
            "header": "X-API-Key",
            "query_param": "api_key",
            "note": "Desactivee si UDE_API_KEY non defini (developpement)",
        },
        "rate_limit": {
            "minute": {
                "limit_per_ip": API_RATE_LIMIT,
                "window_sec": API_RATE_WINDOW_SEC,
            },
            "daily": {
                "limit_per_ip": API_DAILY_LIMIT,
            },
            "endpoints": ENDPOINT_LIMITS,
            "headers": [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Daily-Remaining",
                "Retry-After",
            ],
        },
        "sql_governance": {
            "role_lecture": "ude_reader",
            "droits": "SELECT uniquement sur vues et tables metier",
        },
    }


def get_usage_stats(ip: Optional[str] = None) -> Dict[str, object]:
    """Retourne les statistiques d'utilisation."""
    if ip:
        return dict(_usage_stats.get(ip, {}))
    return {
        "total_ips_tracked": len(_usage_stats),
        "stats_by_ip": {k: dict(v) for k, v in list(_usage_stats.items())[:20]},
    }
