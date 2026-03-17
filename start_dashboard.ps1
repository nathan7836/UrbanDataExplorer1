# Script PowerShell pour démarrer le dashboard

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Dashboard Immobilier Paris - Demarrage" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python detecte: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERREUR: Python n'est pas installe" -ForegroundColor Red
    exit 1
}

# Vérifier les données Gold
if (-not (Test-Path "data\gold\real_estate_data_gold_latest.json")) {
    Write-Host "Generation des donnees..." -ForegroundColor Yellow
    python pipeline.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERREUR: Impossible de generer les donnees" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Demarrage de l'API FastAPI..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "IMPORTANT:" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. L'API sera accessible sur: http://localhost:8000" -ForegroundColor White
Write-Host "2. Le dashboard sera ouvert automatiquement" -ForegroundColor White
Write-Host "3. Gardez cette fenetre ouverte" -ForegroundColor White
Write-Host ""
Write-Host "Appuyez sur Ctrl+C pour arreter" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Démarrer l'API en arrière-plan
$apiProcess = Start-Process python -ArgumentList "api.py" -PassThru -WindowStyle Minimized

# Attendre un peu pour que l'API démarre
Start-Sleep -Seconds 3

# Ouvrir le dashboard
$dashboardPath = Join-Path $PSScriptRoot "dashboard\index.html"
Start-Process $dashboardPath

Write-Host ""
Write-Host "Dashboard ouvert dans votre navigateur!" -ForegroundColor Green
Write-Host "API en cours d'execution (PID: $($apiProcess.Id))" -ForegroundColor Green
Write-Host ""
Write-Host "Pour arreter l'API, fermez cette fenetre ou appuyez sur Ctrl+C" -ForegroundColor Yellow
Write-Host ""

# Attendre que l'utilisateur appuie sur une touche
Read-Host "Appuyez sur Entree pour arreter l'API"

# Arrêter l'API
Stop-Process -Id $apiProcess.Id -Force
Write-Host "API arretee." -ForegroundColor Green

