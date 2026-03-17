"""
Fichier de configuration pour les APIs.
Modifiez ce fichier pour ajouter vos propres endpoints API.
"""

# Configuration des APIs
APIS_CONFIG = [
    {
        "name": "example_api_1",
        "url": "https://jsonplaceholder.typicode.com/posts",
        "params": {"_limit": 10},
        "headers": None,
        "method": "GET",
        "format": "json",  # 'json' ou 'csv'
        "timeout": 30
    },
    {
        "name": "example_api_2",
        "url": "https://jsonplaceholder.typicode.com/users",
        "params": None,
        "headers": None,
        "method": "GET",
        "format": "json",
        "timeout": 30
    }
]

# Configuration générale
OUTPUT_DIR = "data/bronze"
LOG_FILE = "data_fetcher.log"

