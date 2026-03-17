# Démo soutenance — Urban Data Explorer
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== 1. Infra (Postgres + Mongo + Redis + Kafka) ===" -ForegroundColor Cyan
docker compose up -d postgres mongo redis kafka kafka-consumer

Write-Host "=== 2. Sync BDD (Gold -> SQL + geo_points) ===" -ForegroundColor Cyan
python scripts/sync_platform.py

Write-Host "=== 3. Vérifications API (TestClient) ===" -ForegroundColor Cyan
python -c "
from fastapi.testclient import TestClient
from api import app
c = TestClient(app)
for p in ['/health','/bdd/relationnelle','/bdd/non-relationnelle','/mongo/geo-points?limit=2']:
    r = c.get(p)
    print(p, r.status_code)
"

Write-Host "=== 4. Lancer l'API (port 8001) ===" -ForegroundColor Cyan
Write-Host "Puis ouvrir dashboard/index.html (Live Server port 5500)" -ForegroundColor Yellow
$env:API_PORT = "8001"
python api.py
