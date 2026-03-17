"""
Script d'automatisation pour récupérer des données depuis plusieurs APIs.
Stocke les données brutes dans le dossier data/bronze.
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_fetcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataFetcher:
    """Classe pour récupérer des données depuis plusieurs APIs."""
    
    def __init__(self, output_dir: str = "data/bronze"):
        """
        Initialise le DataFetcher.
        
        Args:
            output_dir: Répertoire de sortie pour stocker les données brutes
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DataFetcher/1.0'
        })
    
    def fetch_api_data(
        self,
        api_name: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        method: str = 'GET',
        timeout: int = 30
    ) -> Optional[Dict]:
        """
        Récupère des données depuis une API.
        
        Args:
            api_name: Nom de l'API (pour le logging et le nom de fichier)
            url: URL de l'endpoint API
            params: Paramètres de requête (optionnel)
            headers: Headers HTTP personnalisés (optionnel)
            method: Méthode HTTP (GET, POST, etc.)
            timeout: Timeout en secondes
        
        Returns:
            Données JSON ou None en cas d'erreur
        """
        try:
            logger.info(f"Récupération des données depuis {api_name}...")
            
            # Préparer les headers
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
            
            # Effectuer la requête
            if method.upper() == 'GET':
                response = self.session.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=timeout
                )
            elif method.upper() == 'POST':
                response = self.session.post(
                    url,
                    json=params,
                    headers=request_headers,
                    timeout=timeout
                )
            else:
                logger.error(f"Méthode HTTP non supportée: {method}")
                return None
            
            # Vérifier le code de statut HTTP
            response.raise_for_status()
            
            # Parser la réponse JSON
            try:
                data = response.json()
                logger.info(f"[OK] Donnees recuperees avec succes depuis {api_name}")
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Erreur de parsing JSON pour {api_name}: {e}")
                logger.debug(f"Contenu de la réponse: {response.text[:500]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout lors de la récupération depuis {api_name}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"Erreur HTTP {e.response.status_code} pour {api_name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur de requête pour {api_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erreur inattendue pour {api_name}: {e}")
            return None
    
    def save_data(
        self,
        data: Any,
        api_name: str,
        format: str = 'json'
    ) -> bool:
        """
        Sauvegarde les données dans le dossier bronze.
        
        Args:
            data: Données à sauvegarder
            api_name: Nom de l'API (pour le nom de fichier)
            format: Format de sauvegarde ('json' ou 'csv')
        
        Returns:
            True si la sauvegarde a réussi, False sinon
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            if format.lower() == 'json':
                filename = f"{api_name}_{timestamp}.json"
                filepath = self.output_dir / filename
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"[OK] Donnees sauvegardees dans {filepath}")
                return True
                
            elif format.lower() == 'csv':
                filename = f"{api_name}_{timestamp}.csv"
                filepath = self.output_dir / filename
                
                # Convertir en DataFrame si ce n'est pas déjà le cas
                if isinstance(data, dict):
                    # Si c'est une liste dans le dict, prendre la première liste
                    if isinstance(data, dict) and len(data) == 1:
                        key = list(data.keys())[0]
                        if isinstance(data[key], list):
                            df = pd.DataFrame(data[key])
                        else:
                            df = pd.DataFrame([data])
                    else:
                        df = pd.DataFrame([data])
                elif isinstance(data, list):
                    df = pd.DataFrame(data)
                else:
                    df = pd.DataFrame([data])
                
                df.to_csv(filepath, index=False, encoding='utf-8')
                logger.info(f"[OK] Donnees sauvegardees dans {filepath}")
                return True
            else:
                logger.error(f"Format non supporté: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des données pour {api_name}: {e}")
            return False
    
    def validate_data(self, data: Any, api_name: str) -> bool:
        """
        Valide que les données ne sont pas vides ou manquantes.
        
        Args:
            data: Données à valider
            api_name: Nom de l'API (pour le logging)
        
        Returns:
            True si les données sont valides, False sinon
        """
        if data is None:
            logger.warning(f"Données vides pour {api_name}")
            return False
        
        if isinstance(data, dict):
            if len(data) == 0:
                logger.warning(f"Données vides (dict vide) pour {api_name}")
                return False
        elif isinstance(data, list):
            if len(data) == 0:
                logger.warning(f"Données vides (liste vide) pour {api_name}")
                return False
        
        logger.info(f"[OK] Donnees validees pour {api_name}")
        return True
    
    def fetch_and_save(
        self,
        api_name: str,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        method: str = 'GET',
        format: str = 'json',
        timeout: int = 30
    ) -> bool:
        """
        Récupère les données depuis une API et les sauvegarde.
        
        Args:
            api_name: Nom de l'API
            url: URL de l'endpoint
            params: Paramètres de requête
            headers: Headers HTTP personnalisés
            method: Méthode HTTP
            format: Format de sauvegarde ('json' ou 'csv')
            timeout: Timeout en secondes
        
        Returns:
            True si l'opération a réussi, False sinon
        """
        # Récupérer les données
        data = self.fetch_api_data(api_name, url, params, headers, method, timeout)
        
        # Valider les données
        if not self.validate_data(data, api_name):
            return False
        
        # Sauvegarder les données
        return self.save_data(data, api_name, format)


def main():
    """Fonction principale pour exécuter la récupération de données."""
    
    try:
        from config import APIS_CONFIG, OUTPUT_DIR
    except ImportError:
        logger.warning("Fichier config.py non trouvé, utilisation de la configuration par défaut")
        OUTPUT_DIR = "data/bronze"
        APIS_CONFIG = [
            {
                "name": "example_api_1",
                "url": "https://jsonplaceholder.typicode.com/posts",
                "params": {"_limit": 10},
                "format": "json"
            }
        ]
    
    fetcher = DataFetcher(output_dir=OUTPUT_DIR)
    
    apis_config = APIS_CONFIG
    
    logger.info("=" * 60)
    logger.info("Début de la récupération des données")
    logger.info("=" * 60)
    
    results = []
    for api_config in apis_config:
        success = fetcher.fetch_and_save(
            api_name=api_config["name"],
            url=api_config["url"],
            params=api_config.get("params"),
            headers=api_config.get("headers"),
            method=api_config.get("method", "GET"),
            format=api_config.get("format", "json"),
            timeout=api_config.get("timeout", 30)
        )
        results.append({
            "api": api_config["name"],
            "success": success
        })
    
    # Résumé
    logger.info("=" * 60)
    logger.info("Résumé de la récupération")
    logger.info("=" * 60)
    for result in results:
        status = "[OK] SUCCES" if result["success"] else "[ERREUR] ECHEC"
        logger.info(f"{result['api']}: {status}")
    
    successful = sum(1 for r in results if r["success"])
    logger.info(f"\nTotal: {successful}/{len(results)} APIs récupérées avec succès")


if __name__ == "__main__":
    main()

