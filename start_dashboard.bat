@echo off
echo ========================================
echo Dashboard Immobilier Paris - Demarrage
echo ========================================
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo ERREUR: Python n'est pas installe ou pas dans le PATH
    pause
    exit /b 1
)

REM Verifier si les donnees Gold existent
if not exist "data\gold\real_estate_data_gold_latest.json" (
    echo Generation des donnees...
    python pipeline.py
    if errorlevel 1 (
        echo ERREUR: Impossible de generer les donnees
        pause
        exit /b 1
    )
)

echo.
echo Demarrage de l'API FastAPI...
echo.
echo ========================================
echo IMPORTANT:
echo ========================================
echo 1. L'API sera accessible sur: http://localhost:8000
echo 2. Le dashboard sera ouvert automatiquement dans votre navigateur
echo 3. Gardez cette fenetre ouverte pendant l'utilisation
echo.
echo Appuyez sur Ctrl+C pour arreter l'API
echo ========================================
echo.

REM Demarrer l'API en arriere-plan et ouvrir le dashboard
start "" python api.py
timeout /t 3 /nobreak >nul

REM Ouvrir le dashboard dans le navigateur
start "" "dashboard\index.html"

echo.
echo Dashboard ouvert dans votre navigateur!
echo.
pause

