"""
Vérifie la connexion INSEE (.env) avant de lancer le pipeline.
Usage : python scripts/check_insee.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from public_data_integrations import _insee_access_token, _insee_headers
import requests


def main() -> int:
    token = _insee_access_token()
    if not token:
        print("ERREUR: Aucun identifiant INSEE dans .env")
        print("  - INSEE_API_KEY=<jeton>")
        print("  - ou INSEE_CONSUMER_KEY + INSEE_CONSUMER_SECRET")
        print("Obtenez vos clés sur https://portail-api.insee.fr/")
        return 1

    print("OK: jeton INSEE obtenu (longueur %d)" % len(token))

    headers = _insee_headers()
    test_url = (
        "https://api.insee.fr/donnees-locales/V0.1/donnees/"
        "geo-ARRONDISSEMENT_PLM@GEO2020RP2017/POP@GEO2020RP2017"
    )
    r = requests.get(test_url, headers=headers, timeout=30)
    print("Test API données locales:", r.status_code)
    if r.ok:
        print("OK: API INSEE accessible.")
        return 0
    print("Réponse:", r.text[:300])
    print("Le jeton est valide mais l'URL peut avoir changé — le pipeline tentera quand même les endpoints configurés.")
    return 0 if r.status_code in (200, 404) else 1


if __name__ == "__main__":
    raise SystemExit(main())
