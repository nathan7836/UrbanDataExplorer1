"""
Pipeline complet : Génération Bronze -> Transformation Silver -> Transformation Gold
"""

import logging
from real_estate_fetcher import RealEstateDataFetcher
from data_processor import DataProcessor
from ude_platform.iris_metrics import build_iris_metrics

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_full_pipeline():
    """Exécute le pipeline complet."""
    logger.info("=" * 60)
    logger.info("DEMARRAGE DU PIPELINE COMPLET")
    logger.info("=" * 60)
    
    # Étape 1: Générer les données Bronze (fetch + fusion + géocodage BAN/Nominatim)
    logger.info("\n[ETAPE 1/4] Generation des donnees Bronze...")
    logger.info("-" * 60)
    fetcher = RealEstateDataFetcher()
    if not fetcher.fetch_real_estate_data():
        logger.error("ERREUR: Echec de la generation des donnees Bronze")
        return False

    # Étape 2: Calcul des indicateurs réellement disponibles à la maille IRIS.
    # Une indisponibilité externe ne bloque pas le snapshot arrondissement.
    logger.info("\n[ETAPE 2/4] Calcul des indicateurs natifs IRIS...")
    logger.info("-" * 60)
    try:
        build_iris_metrics()
    except Exception as exc:
        logger.warning("Calcul IRIS indisponible, conservation du dernier snapshot : %s", exc)
    
    # Étapes 3–4: Silver, Gold, export (dans DataProcessor)
    logger.info("\n[ETAPE 3/4] Transformation Bronze -> Silver -> Gold + export...")
    logger.info("-" * 60)
    processor = DataProcessor()
    if not processor.process_pipeline():
        logger.error("ERREUR: Echec du pipeline de traitement")
        return False
    
    logger.info("\n" + "=" * 60)
    logger.info("[OK] PIPELINE COMPLET TERMINE AVEC SUCCES")
    logger.info("=" * 60)
    logger.info("\nDonnees disponibles:")
    logger.info("  - Bronze: data/bronze/real_estate_data_latest.json")
    logger.info("  - Silver: data/silver/real_estate_data_silver_latest.json")
    logger.info("  - Gold:   data/gold/real_estate_data_gold_latest.json")
    logger.info("  - IRIS:   dashboard/static/data/paris_iris_metrics.json")
    logger.info("  - Export: data/export/donnees_fusionnees_latest.csv")
    logger.info("\nVous pouvez maintenant demarrer l'API avec: python api.py")
    
    return True


if __name__ == "__main__":
    run_full_pipeline()
