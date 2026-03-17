# Démarrage local : Docker (Postgres + Mongo), sync plateforme, API
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Docker (postgres, mongo)..." -ForegroundColor Cyan
docker compose up -d postgres mongo

Write-Host "==> Sync plateforme (Postgres + Mongo geo_points)..." -ForegroundColor Cyan
python scripts/sync_platform.py

Write-Host "==> API sur http://localhost:8001 (Ctrl+C pour arrêter)" -ForegroundColor Cyan
$env:API_PORT = "8001"
python api.py
