"""Script de test pour vérifier que l'API peut démarrer."""
import sys
from pathlib import Path

# Vérifier les données
gold_file = Path("data/gold/real_estate_data_gold_latest.json")
if not gold_file.exists():
    print("ERREUR: Fichier Gold non trouvé!")
    print("Exécutez: python pipeline.py")
    sys.exit(1)

    print("[OK] Fichier Gold trouve")

# Vérifier les imports
try:
    import fastapi
    import uvicorn
    print("[OK] FastAPI et Uvicorn installes")
except ImportError as e:
    print(f"ERREUR: {e}")
    print("Installez avec: pip install -r requirements.txt")
    sys.exit(1)

# Tester le chargement des données
try:
    import json
    with open(gold_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"[OK] Donnees chargees: {len(data.get('arrondissements', []))} arrondissements")
except Exception as e:
    print(f"ERREUR lors du chargement: {e}")
    sys.exit(1)

print("\n[OK] Tout est OK! L'API peut demarrer.")
print("Démarrez avec: python api.py")

