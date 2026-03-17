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

REM Verifier si les donnees existent
if not exist "data\bronze\real_estate_data_latest.json" (
    echo Generation des donnees...
    python real_estate_fetcher.py
    if errorlevel 1 (
        echo ERREUR: Impossible de generer les donnees
        pause
        exit /b 1
    )
)

REM Demarrer l'API
echo.
echo Demarrage de l'API...
echo API disponible sur: http://localhost:8000
echo Documentation: http://localhost:8000/docs
echo.
echo Appuyez sur Ctrl+C pour arreter l'API
echo.

python api.py

pause

