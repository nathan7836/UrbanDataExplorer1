"""
Script pour exporter les tables prêtes pour la visualisation.
Génère des fichiers Parquet, CSV et GeoJSON avec :
- Prix médian par arrondissement et par année
- Variation annuelle (%)
- Données socio-éco fusionnées (revenus, densité, pollution, délits)
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TableExporter:
    """Classe pour exporter les tables prêtes pour la visualisation."""

    @staticmethod
    def _flatten_typologie(typologie: Dict) -> Dict[str, float]:
        """Extrait les % par type de logement depuis la structure Gold."""
        repartition = typologie.get("repartition_pieces") or {}
        if not repartition and isinstance(typologie.get("Studio"), (int, float)):
            repartition = typologie
        return {
            "typologie_studio": float(repartition.get("Studio", 0) or 0),
            "typologie_t2": float(repartition.get("T2", 0) or 0),
            "typologie_t3": float(repartition.get("T3", 0) or 0),
            "typologie_t4": float(repartition.get("T4", 0) or 0),
            "typologie_t5plus": float(repartition.get("T5+", 0) or 0),
            "typologie_appartements_pct": float(
                (typologie.get("type_logement") or {}).get("appartements", 0) or 0
            ),
            "typologie_maisons_pct": float(
                (typologie.get("type_logement") or {}).get("maisons", 0) or 0
            ),
            "surface_moyenne_m2": float(
                (typologie.get("statistiques") or {}).get("surface_moyenne_m2", 0) or 0
            ),
        }
    
    def __init__(self, gold_data_file: str = "data/gold/real_estate_data_gold_latest.json"):
        self.gold_data_file = Path(gold_data_file)
        self.output_dir = Path("data/export")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data = None
    
    def load_gold_data(self) -> bool:
        """Charge les données Gold."""
        try:
            if not self.gold_data_file.exists():
                logger.error(f"Fichier Gold non trouve: {self.gold_data_file}")
                return False
            
            with open(self.gold_data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            logger.info(f"[OK] Donnees Gold chargees depuis {self.gold_data_file}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du chargement des donnees: {e}")
            return False
    
    def create_prix_table(self) -> pd.DataFrame:
        """
        Crée une table avec prix médian par arrondissement et par année.
        Inclut la variation annuelle (%).
        """
        logger.info("Creation de la table prix par arrondissement et annee...")
        
        rows = []
        arrondissements = self.data.get("arrondissements", [])
        
        for arr in arrondissements:
            arr_num = arr.get("arrondissement")
            nom = arr.get("nom")
            evolution_annuelle = arr.get("evolution_annuelle", [])
            
            # Trier par année
            evolution_sorted = sorted(evolution_annuelle, key=lambda x: x.get("annee", 0))
            
            for i, evol in enumerate(evolution_sorted):
                annee = evol.get("annee")
                prix_median = evol.get("prix_m2_median")
                nb_transactions = evol.get("nombre_transactions", 0)
                
                # Calculer la variation annuelle
                variation_annuelle = None
                if i > 0:
                    prix_precedent = evolution_sorted[i-1].get("prix_m2_median")
                    if prix_precedent and prix_precedent > 0 and prix_median:
                        variation_annuelle = round(((prix_median - prix_precedent) / prix_precedent) * 100, 2)
                
                rows.append({
                    "arrondissement": arr_num,
                    "nom": nom,
                    "annee": annee,
                    "prix_m2_median": prix_median,
                    "variation_annuelle_pourcentage": variation_annuelle,
                    "nombre_transactions": nb_transactions
                })
        
        df = pd.DataFrame(rows)
        logger.info(f"[OK] Table prix creee: {len(df)} lignes")
        return df
    
    def create_fusion_table(self) -> pd.DataFrame:
        """
        Crée une table fusionnée avec toutes les données socio-éco.
        Prix, revenus, densité, pollution, délits, logements sociaux.
        """
        logger.info("Creation de la table fusionnee (socio-eco)...")
        
        rows = []
        arrondissements = self.data.get("arrondissements", [])
        
        for arr in arrondissements:
            arr_num = arr.get("arrondissement")
            nom = arr.get("nom")
            code_insee = arr.get("code_insee")
            
            # Statistiques prix
            stats = arr.get("statistiques", {})
            prix_actuel = stats.get("prix_m2_actuel")
            prix_median = stats.get("prix_m2_median")
            prix_min = stats.get("prix_m2_min")
            prix_max = stats.get("prix_m2_max")
            prix_moyen = stats.get("prix_m2_moyen")
            
            # Évolution
            evolution = arr.get("evolution_calculee", {})
            variation_absolue = evolution.get("variation_absolue")
            variation_pourcentage = evolution.get("variation_pourcentage")
            tendance = evolution.get("tendance")
            
            # Tendances annuelles
            tendance_annuelle = arr.get("tendance_annuelle", {})
            variation_annuelle_moyenne = tendance_annuelle.get("variation_annuelle_moyenne")
            taux_croissance_annuel = tendance_annuelle.get("taux_croissance_annuel")
            
            # Logements sociaux
            logements_sociaux = arr.get("logements_sociaux_pourcentage", 0)
            
            typologie_cols = self._flatten_typologie(arr.get("typologie", {}))

            # Pollution
            pollution = arr.get("pollution_qualite_air", {})
            indice_atmo = pollution.get("indice_atmo")
            pm25 = pollution.get("pm25_moyen")
            pm10 = pollution.get("pm10_moyen")
            no2 = pollution.get("no2_moyen")
            qualite_air = pollution.get("qualite")
            
            # Délits
            delits = arr.get("delits_enregistres", {})
            total_delits = delits.get("total_delits")
            delits_par_1000 = delits.get("delits_par_1000_habitants")
            cambriolages = delits.get("cambriolages")
            vols = delits.get("vols")
            violences = delits.get("violences")
            
            # Revenus
            revenus = arr.get("revenus_moyens", {})
            revenu_median = revenus.get("revenu_median_menage")
            revenu_moyen = revenus.get("revenu_moyen_menage")
            niveau_vie = revenus.get("niveau_vie_median")
            
            # Densité
            densite = arr.get("densite_population", {})
            population = densite.get("population")
            densite_km2 = densite.get("densite_km2")
            superficie = densite.get("superficie_km2")
            
            rows.append({
                # Identifiants
                "arrondissement": arr_num,
                "nom": nom,
                "code_insee": code_insee,
                
                # Prix
                "prix_m2_actuel": prix_actuel,
                "prix_m2_median": prix_median,
                "prix_m2_min": prix_min,
                "prix_m2_max": prix_max,
                "prix_m2_moyen": prix_moyen,
                "variation_absolue": variation_absolue,
                "variation_pourcentage": variation_pourcentage,
                "tendance": tendance,
                "variation_annuelle_moyenne": variation_annuelle_moyenne,
                "taux_croissance_annuel": taux_croissance_annuel,
                
                # Social
                "logements_sociaux_pourcentage": logements_sociaux,
                **typologie_cols,

                # Pollution
                "indice_atmo": indice_atmo,
                "pm25_moyen": pm25,
                "pm10_moyen": pm10,
                "no2_moyen": no2,
                "qualite_air": qualite_air,
                
                # Délits
                "total_delits": total_delits,
                "delits_par_1000_habitants": delits_par_1000,
                "cambriolages": cambriolages,
                "vols": vols,
                "violences": violences,
                
                # Revenus
                "revenu_median_menage": revenu_median,
                "revenu_moyen_menage": revenu_moyen,
                "niveau_vie_median": niveau_vie,
                
                # Densité
                "population": population,
                "densite_km2": densite_km2,
                "superficie_km2": superficie
            })
        
        df = pd.DataFrame(rows)
        logger.info(f"[OK] Table fusionnee creee: {len(df)} lignes, {len(df.columns)} colonnes")
        return df
    
    def create_geojson(self, df: pd.DataFrame) -> Dict:
        """
        Crée un GeoJSON à partir de la table fusionnée.
        Utilise les coordonnées approximatives des arrondissements.
        """
        logger.info("Creation du GeoJSON...")
        
        coords_map = {
            1: [48.8606, 2.3376], 2: [48.8698, 2.3412], 3: [48.8630, 2.3624],
            4: [48.8546, 2.3522], 5: [48.8448, 2.3447], 6: [48.8448, 2.3327],
            7: [48.8566, 2.3186], 8: [48.8738, 2.3132], 9: [48.8738, 2.3392],
            10: [48.8738, 2.3624], 11: [48.8630, 2.3768], 12: [48.8448, 2.3768],
            13: [48.8322, 2.3522], 14: [48.8330, 2.3264], 15: [48.8412, 2.2995],
            16: [48.8534, 2.2654], 17: [48.8838, 2.3214], 18: [48.8932, 2.3447],
            19: [48.8838, 2.3768], 20: [48.8630, 2.3984],
        }
        geocoding_by_arr = {}
        if self.data:
            for arr in self.data.get("arrondissements", []):
                geo = arr.get("geocoding") or {}
                lon, lat = geo.get("longitude"), geo.get("latitude")
                if lon is not None and lat is not None:
                    geocoding_by_arr[int(arr["arrondissement"])] = [float(lat), float(lon)]

        features = []
        for _, row in df.iterrows():
            arr_num = int(row["arrondissement"])
            coords = geocoding_by_arr.get(arr_num) or coords_map.get(arr_num, [48.8566, 2.3522])
            
            # Créer les propriétés (toutes les colonnes sauf geometry)
            properties = row.to_dict()
            
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [coords[1], coords[0]]  # GeoJSON: [lon, lat]
                },
                "properties": properties
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        logger.info(f"[OK] GeoJSON cree: {len(features)} features")
        return geojson
    
    def export_all(self) -> bool:
        """Exporte toutes les tables dans les différents formats."""
        logger.info("=" * 60)
        logger.info("DEBUT DE L'EXPORT DES TABLES")
        logger.info("=" * 60)
        
        if not self.load_gold_data():
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parquet_path = None
        parquet_fusion_path = None
        parquet_ok = False

        # 1. Table prix par arrondissement et année
        df_prix = self.create_prix_table()
        
        # Export CSV
        csv_path = self.output_dir / f"prix_par_arrondissement_annee_{timestamp}.csv"
        df_prix.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"[OK] CSV exporte: {csv_path}")
        
        # Export Parquet
        try:
            parquet_path = self.output_dir / f"prix_par_arrondissement_annee_{timestamp}.parquet"
            latest_prix_parquet = self.output_dir / "prix_par_arrondissement_annee_latest.parquet"
            df_prix.to_parquet(parquet_path, index=False, engine='pyarrow')
            df_prix.to_parquet(latest_prix_parquet, index=False, engine='pyarrow')
            parquet_ok = True
            logger.info(f"[OK] Parquet exporte: {parquet_path}")
            logger.info(f"[OK] Parquet latest: {latest_prix_parquet}")
        except Exception as e:
            logger.warning(f"Impossible d'exporter en Parquet (pyarrow non installe?): {e}")
        
        # 2. Table fusionnée (socio-éco)
        df_fusion = self.create_fusion_table()
        
        # Export CSV
        csv_fusion_path = self.output_dir / f"donnees_fusionnees_{timestamp}.csv"
        df_fusion.to_csv(csv_fusion_path, index=False, encoding='utf-8')
        logger.info(f"[OK] CSV fusionne exporte: {csv_fusion_path}")
        
        # Export Parquet
        try:
            parquet_fusion_path = self.output_dir / f"donnees_fusionnees_{timestamp}.parquet"
            latest_fusion_parquet = self.output_dir / "donnees_fusionnees_latest.parquet"
            df_fusion.to_parquet(parquet_fusion_path, index=False, engine='pyarrow')
            df_fusion.to_parquet(latest_fusion_parquet, index=False, engine='pyarrow')
            parquet_ok = True
            logger.info(f"[OK] Parquet fusionne exporte: {parquet_fusion_path}")
            logger.info(f"[OK] Parquet fusionne latest: {latest_fusion_parquet}")
        except Exception as e:
            logger.warning(f"Impossible d'exporter en Parquet: {e}")
        
        # 3. GeoJSON
        geojson_data = self.create_geojson(df_fusion)
        geojson_path = self.output_dir / f"donnees_fusionnees_{timestamp}.geojson"
        with open(geojson_path, 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        logger.info(f"[OK] GeoJSON exporte: {geojson_path}")
        
        # Créer aussi des fichiers "latest"
        df_prix.to_csv(self.output_dir / "prix_par_arrondissement_annee_latest.csv", index=False, encoding='utf-8')
        df_fusion.to_csv(self.output_dir / "donnees_fusionnees_latest.csv", index=False, encoding='utf-8')
        with open(self.output_dir / "donnees_fusionnees_latest.geojson", 'w', encoding='utf-8') as f:
            json.dump(geojson_data, f, indent=2, ensure_ascii=False)
        
        logger.info("=" * 60)
        logger.info("[OK] EXPORT TERMINE AVEC SUCCES")
        logger.info("=" * 60)
        logger.info(f"\nFichiers exportes dans: {self.output_dir}")
        logger.info("  - prix_par_arrondissement_annee_latest.csv")
        logger.info("  - donnees_fusionnees_latest.csv")
        logger.info("  - donnees_fusionnees_latest.geojson")
        if parquet_ok:
            logger.info("  - prix_par_arrondissement_annee_latest.parquet")
            logger.info("  - donnees_fusionnees_latest.parquet")
        
        return True


def main():
    """Fonction principale."""
    exporter = TableExporter()
    exporter.export_all()


if __name__ == "__main__":
    main()

