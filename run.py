"""
Script pour démarrer facilement l'API et générer les données.
"""

import subprocess
import sys
import os
from pathlib import Path

def check_data_exists():
    """Vérifie si les données Gold existent."""
    data_file = Path("data/gold/real_estate_data_gold_latest.json")
    return data_file.exists()

def check_gold_data_exists():
    """Vérifie si les données Gold existent."""
    from pathlib import Path
    gold_file = Path("data/gold/real_estate_data_gold_latest.json")
    return gold_file.exists()

def generate_data():
    """Génère les données et exécute le pipeline complet."""
    print("📊 Exécution du pipeline complet (Bronze -> Silver -> Gold)...")
    try:
        from pipeline import run_full_pipeline
        if run_full_pipeline():
            print("✅ Pipeline exécuté avec succès!")
            return True
        else:
            print("❌ Erreur lors de l'exécution du pipeline")
            return False
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du pipeline: {e}")
        return False

def start_api():
    """Démarre l'API FastAPI."""
    print("🚀 Démarrage de l'API...")
    port = int(os.getenv("API_PORT", "8001"))
    print(f"📍 API disponible sur: http://localhost:{port}")
    print(f"📚 Documentation: http://localhost:{port}/docs")
    print("\nAppuyez sur Ctrl+C pour arrêter l'API\n")
    
    try:
        import uvicorn
        uvicorn.run("api:app", host="0.0.0.0", port=port, reload=True)
    except KeyboardInterrupt:
        print("\n\n👋 Arrêt de l'API")
    except Exception as e:
        print(f"❌ Erreur lors du démarrage de l'API: {e}")

def main():
    """Fonction principale."""
    print("=" * 60)
    print("🏠 Dashboard Immobilier Paris - Démarrage")
    print("=" * 60)
    
    # Vérifier si les données Gold existent
    if not check_data_exists():
        print("⚠️  Aucune donnée Gold trouvée. Exécution du pipeline complet...")
        if not generate_data():
            print("❌ Impossible d'exécuter le pipeline. Vérifiez les dépendances.")
            sys.exit(1)
    else:
        print("✅ Données Gold trouvées")
    
    # Démarrer l'API
    start_api()

if __name__ == "__main__":
    main()

