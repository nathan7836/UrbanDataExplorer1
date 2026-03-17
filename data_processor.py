"""
Pipeline de traitement des données : Bronze -> Silver -> Gold
Architecture Medallion (Bronze, Silver, Gold)
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from data_normalization import (
    build_data_quality,
    dedupe_records,
    is_missing,
    normalize_date,
    normalize_price,
    normalize_surface_m2,
    normalize_year,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataProcessor:
    """Classe pour transformer les données à travers les couches Bronze -> Silver -> Gold."""
    
    def __init__(self):
        self.bronze_dir = Path("data/bronze")
        self.silver_dir = Path("data/silver")
        self.gold_dir = Path("data/gold")
        
        # Créer les dossiers s'ils n'existent pas
        self.silver_dir.mkdir(parents=True, exist_ok=True)
        self.gold_dir.mkdir(parents=True, exist_ok=True)
    
    def load_bronze_data(self, filename: str = "real_estate_data_latest.json") -> Optional[Dict]:
        """Charge les données brutes depuis la couche Bronze."""
        filepath = self.bronze_dir / filename
        if not filepath.exists():
            logger.error(f"Fichier Bronze non trouve: {filepath}")
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"[OK] Donnees Bronze chargees depuis {filepath}")
            return data
        except Exception as e:
            logger.error(f"Erreur lors du chargement des donnees Bronze: {e}")
            return None
    
    def bronze_to_silver(self, bronze_data: Dict) -> Optional[Dict]:
        """
        Transforme les données Bronze en Silver (nettoyage).
        - Supprime les doublons
        - Valide les types de données
        - Corrige les valeurs aberrantes
        - Normalise les formats
        """
        logger.info("Transformation Bronze -> Silver (nettoyage)...")
        
        try:
            silver_data = {
                "timestamp": bronze_data.get("timestamp", datetime.now().isoformat()),
                "integration_report": bronze_data.get("integration_report", {}),
                "sources_updated_at": bronze_data.get("sources_updated_at"),
                "arrondissements": []
            }
            
            for arr in bronze_data.get("arrondissements", []):
                # Nettoyer les données de l'arrondissement
                cleaned_arr = self._clean_arrondissement_data(arr)
                if cleaned_arr:
                    silver_data["arrondissements"].append(cleaned_arr)
            
            logger.info(f"[OK] {len(silver_data['arrondissements'])} arrondissements nettoyes")
            return silver_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la transformation Bronze -> Silver: {e}")
            return None
    
    def _clean_arrondissement_data(self, arr: Dict) -> Optional[Dict]:
        """Nettoie les données d'un arrondissement."""
        try:
            # Validation du numéro d'arrondissement
            arr_num = arr.get("arrondissement")
            if not arr_num or arr_num < 1 or arr_num > 20:
                logger.warning(f"Arrondissement invalide: {arr_num}")
                return None
            
            # Nettoyer les prix/m²
            prix_cleaned = []
            prix_raw = arr.get("prix_m2_median", [])
            
            missing_fields: List[str] = []
            imputed_fields: List[str] = []

            for prix_item in prix_raw:
                if not isinstance(prix_item, dict):
                    continue
                d = normalize_date(prix_item.get("date"))
                p = normalize_price(prix_item.get("prix_m2"))
                if d and p is not None:
                    prix_cleaned.append({"date": d, "prix_m2": p})

            prix_cleaned = dedupe_records(prix_cleaned, lambda x: x["date"])
            prix_cleaned.sort(key=lambda x: x["date"])
            
            # Nettoyer le pourcentage de logements sociaux
            logements_sociaux = arr.get("logements_sociaux_pourcentage", 0)
            try:
                logements_sociaux = float(logements_sociaux)
                if logements_sociaux < 0:
                    logements_sociaux = 0
                elif logements_sociaux > 100:
                    logements_sociaux = 100
                logements_sociaux = round(logements_sociaux, 2)
            except (ValueError, TypeError):
                logements_sociaux = 0
            
            # Nettoyer la typologie (structure enrichie)
            typologie_raw = arr.get("typologie", {})
            typologie_cleaned = {}
            
            # Nettoyer le type de logement (appartement/maison)
            type_logement_raw = typologie_raw.get("type_logement", {})
            typologie_cleaned["type_logement"] = {
                "appartements": max(0, min(100, float(type_logement_raw.get("appartements", 0)))),
                "maisons": max(0, min(100, float(type_logement_raw.get("maisons", 0)))),
                "total_logements": max(0, int(type_logement_raw.get("total_logements", 0)))
            }
            
            # Normaliser les pourcentages type_logement
            total_type = typologie_cleaned["type_logement"]["appartements"] + typologie_cleaned["type_logement"]["maisons"]
            if total_type > 0 and total_type != 100:
                factor = 100 / total_type
                typologie_cleaned["type_logement"]["appartements"] = round(typologie_cleaned["type_logement"]["appartements"] * factor, 2)
                typologie_cleaned["type_logement"]["maisons"] = round(typologie_cleaned["type_logement"]["maisons"] * factor, 2)
            
            # Nettoyer la répartition par pièces
            repartition_raw = typologie_raw.get("repartition_pieces", {})
            typologie_cleaned["repartition_pieces"] = {}
            total_pieces = 0
            
            for typo in ["Studio", "T2", "T3", "T4", "T5+"]:
                value = repartition_raw.get(typo, 0)
                try:
                    value = max(0, min(100, float(value)))
                    typologie_cleaned["repartition_pieces"][typo] = round(value, 2)
                    total_pieces += value
                except (ValueError, TypeError):
                    typologie_cleaned["repartition_pieces"][typo] = 0
            
            # Normaliser les pourcentages répartition_pieces
            if total_pieces > 100:
                factor = 100 / total_pieces
                for typo in typologie_cleaned["repartition_pieces"]:
                    typologie_cleaned["repartition_pieces"][typo] = round(typologie_cleaned["repartition_pieces"][typo] * factor, 2)
            
            # Nettoyer le détail par nombre de pièces
            detail_raw = typologie_raw.get("detail_pieces", {})
            typologie_cleaned["detail_pieces"] = {}
            
            for piece_key in ["1_piece", "2_pieces", "3_pieces", "4_pieces", "5_et_plus_pieces"]:
                piece_data = detail_raw.get(piece_key, {})
                typologie_cleaned["detail_pieces"][piece_key] = {
                    "nombre": max(0, int(piece_data.get("nombre", 0))),
                    "pourcentage": max(0, min(100, float(piece_data.get("pourcentage", 0)))),
                    "type": piece_data.get("type", "")
                }
            
            # Nettoyer les statistiques
            stats_raw = typologie_raw.get("statistiques", {})
            surface_m2 = normalize_surface_m2(stats_raw.get("surface_moyenne_m2"))
            if surface_m2 is None:
                surface_m2 = normalize_surface_m2(arr.get("surface_moyenne_dvf_m2"))
            typologie_cleaned["statistiques"] = {
                "nombre_total_logements": max(0, int(stats_raw.get("nombre_total_logements", 0))),
                "logements_principaux": max(0, int(stats_raw.get("logements_principaux", 0))),
                "logements_secondaires": max(0, int(stats_raw.get("logements_secondaires", 0))),
                "logements_vacants": max(0, int(stats_raw.get("logements_vacants", 0))),
                "surface_moyenne_m2": surface_m2 if surface_m2 is not None else 0.0,
                "annee": int(stats_raw.get("annee", 2024))
            }
            
            # Nettoyer l'évolution
            evolution_cleaned = []
            evolution_raw = arr.get("evolution", [])
            
            for evol in evolution_raw:
                if not isinstance(evol, dict):
                    continue
                annee_int = normalize_year(evol.get("annee"))
                prix_float = normalize_price(evol.get("prix_m2_median"))
                if annee_int and prix_float is not None:
                    try:
                        nb_int = max(0, int(evol.get("nombre_transactions", 0)))
                    except (ValueError, TypeError):
                        nb_int = 0
                    evolution_cleaned.append({
                        "annee": annee_int,
                        "prix_m2_median": prix_float,
                        "nombre_transactions": nb_int,
                    })

            evolution_cleaned = dedupe_records(evolution_cleaned, lambda x: x["annee"])
            evolution_cleaned.sort(key=lambda x: x["annee"])

            geocoding_cleaned = self._clean_geocoding_data(arr.get("geocoding", {}))
            if not geocoding_cleaned.get("longitude"):
                missing_fields.append("geocoding")
            
            sources = arr.get("_sources", {})

            pollution_cleaned = self._clean_pollution_data(
                arr.get("pollution_qualite_air", {}),
                has_source=bool(sources.get("pollution_qualite_air")),
            )
            delits_cleaned = self._clean_delits_data(
                arr.get("delits_enregistres", {}),
                has_source=bool(sources.get("delits_enregistres")),
            )
            revenus_cleaned = self._clean_revenus_data(
                arr.get("revenus_moyens", {}),
                has_source=bool(sources.get("revenus_moyens")),
            )
            if revenus_cleaned.get("_missing"):
                missing_fields.append("revenus_moyens")
            densite_cleaned = self._clean_densite_data(arr.get("densite_population", {}))
            vegetation_cleaned = self._clean_vegetation_data(arr.get("vegetation_arbres", {}))
            transports_cleaned = self._clean_transports_data(arr.get("transports_publics", {}))
            loyers_cleaned = dict(arr.get("loyers") or {})
            logements_sociaux_evolution = arr.get("logements_sociaux_evolution")

            return {
                "arrondissement": arr_num,
                "nom": arr.get("nom", f"{arr_num}e"),
                "code_insee": arr.get("code_insee", f"751{arr_num:02d}"),
                "prix_m2_median": prix_cleaned,
                "logements_sociaux_pourcentage": logements_sociaux,
                "logements_sociaux_evolution": logements_sociaux_evolution,
                "loyers": loyers_cleaned,
                "typologie": typologie_cleaned,
                "evolution": evolution_cleaned,
                "pollution_qualite_air": pollution_cleaned,
                "delits_enregistres": delits_cleaned,
                "revenus_moyens": revenus_cleaned,
                "densite_population": densite_cleaned,
                "vegetation_arbres": vegetation_cleaned,
                "transports_publics": transports_cleaned,
                "geocoding": geocoding_cleaned,
                "_sources": sources,
                "metadata": {
                    "cleaned_at": datetime.now().isoformat(),
                    "nb_prix_records": len(prix_cleaned),
                    "nb_evolution_records": len(evolution_cleaned),
                    "data_quality": build_data_quality(missing_fields, imputed_fields),
                },
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage de l'arrondissement {arr.get('arrondissement')}: {e}")
            return None
    
    def _clean_geocoding_data(self, geocoding: Dict) -> Dict:
        """Nettoie les coordonnées géocodées (BAN / Nominatim / DVF)."""
        try:
            lon = float(geocoding.get("longitude"))
            lat = float(geocoding.get("latitude"))
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("coords invalides")
            return {
                "longitude": round(lon, 6),
                "latitude": round(lat, 6),
                "nb_points": max(0, int(geocoding.get("nb_points", 0))),
                "providers": geocoding.get("providers", {}),
                "annee": int(geocoding.get("annee", 2024)),
            }
        except Exception:
            return {
                "longitude": None,
                "latitude": None,
                "nb_points": 0,
                "providers": {},
                "annee": 2024,
            }

    def _clean_pollution_data(self, pollution: Dict, has_source: bool = True) -> Dict:
        """Nettoie les données de pollution/qualité de l'air."""
        if not pollution and not has_source:
            return {
                "indice_atmo": None,
                "pm25_moyen": None,
                "pm10_moyen": None,
                "no2_moyen": None,
                "date_mesure": None,
                "qualite": None,
                "_missing": True,
            }
        try:
            indice_atmo = pollution.get("indice_atmo", 5)
            pm25 = pollution.get("pm25_moyen", 15)
            pm10 = pollution.get("pm10_moyen", 25)
            no2 = pollution.get("no2_moyen", 40)
            
            # Valider les valeurs
            indice_atmo = max(1, min(10, float(indice_atmo)))
            pm25 = max(0, min(100, float(pm25)))
            pm10 = max(0, min(200, float(pm10)))
            no2 = max(0, min(200, float(no2)))
            
            return {
                "indice_atmo": round(indice_atmo, 1),
                "pm25_moyen": round(pm25, 2),
                "pm10_moyen": round(pm10, 2),
                "no2_moyen": round(no2, 2),
                "date_mesure": pollution.get("date_mesure", datetime.now().strftime("%Y-%m-%d")),
                "qualite": "bonne" if indice_atmo <= 3 else "moyenne" if indice_atmo <= 6 else "mauvaise"
            }
        except Exception:
            return {
                "indice_atmo": 5.0,
                "pm25_moyen": 15.0,
                "pm10_moyen": 25.0,
                "no2_moyen": 40.0,
                "date_mesure": datetime.now().strftime("%Y-%m-%d"),
                "qualite": "moyenne"
            }
    
    def _clean_delits_data(self, delits: Dict, has_source: bool = True) -> Dict:
        """Nettoie les données de délits."""
        if not delits and not has_source:
            return {
                "total_delits": None,
                "delits_par_1000_habitants": None,
                "cambriolages": None,
                "vols": None,
                "violences": None,
                "annee": None,
                "_missing": True,
            }
        try:
            total = max(0, int(delits.get("total_delits", 0)))
            par_1000 = max(0, float(delits.get("delits_par_1000_habitants", 0)))
            cambriolages = max(0, int(delits.get("cambriolages", 0)))
            vols = max(0, int(delits.get("vols", 0)))
            violences = max(0, int(delits.get("violences", 0)))
            
            return {
                "total_delits": total,
                "delits_par_1000_habitants": round(par_1000, 2),
                "cambriolages": cambriolages,
                "vols": vols,
                "violences": violences,
                "annee": int(delits.get("annee", 2024))
            }
        except Exception:
            return {
                "total_delits": 0,
                "delits_par_1000_habitants": 0.0,
                "cambriolages": 0,
                "vols": 0,
                "violences": 0,
                "annee": 2024
            }
    
    def _clean_revenus_data(self, revenus: Dict, has_source: bool = True) -> Dict:
        """Nettoie les données de revenus."""
        if not revenus or all(is_missing(revenus.get(k)) for k in ("revenu_median_menage", "revenu_moyen_menage")):
            if not has_source:
                return {
                    "revenu_median_menage": None,
                    "revenu_moyen_menage": None,
                    "niveau_vie_median": None,
                    "annee": None,
                    "_missing": True,
                }
        try:
            revenu_median = max(0, int(revenus.get("revenu_median_menage", 0)))
            revenu_moyen = max(0, int(revenus.get("revenu_moyen_menage", 0)))
            niveau_vie = max(0, int(revenus.get("niveau_vie_median", 0)))
            
            return {
                "revenu_median_menage": revenu_median,
                "revenu_moyen_menage": revenu_moyen,
                "niveau_vie_median": niveau_vie,
                "annee": int(revenus.get("annee", 2023))
            }
        except Exception:
            return {
                "revenu_median_menage": 0,
                "revenu_moyen_menage": 0,
                "niveau_vie_median": 0,
                "annee": 2023
            }
    
    def _clean_densite_data(self, densite: Dict) -> Dict:
        """Nettoie les données de densité de population."""
        try:
            population = max(0, int(densite.get("population", 0)))
            densite_km2 = max(0, int(densite.get("densite_km2", 0)))
            superficie = max(0.1, float(densite.get("superficie_km2", 1.0)))
            
            # Recalculer la densité si nécessaire
            if population > 0 and superficie > 0:
                densite_calculee = round(population / superficie, 0)
            else:
                densite_calculee = densite_km2
            
            return {
                "population": population,
                "densite_km2": int(densite_calculee),
                "superficie_km2": round(superficie, 2),
                "annee": int(densite.get("annee", 2023))
            }
        except Exception:
            return {
                "population": 0,
                "densite_km2": 0,
                "superficie_km2": 1.0,
                "annee": 2023
            }
    
    def _clean_vegetation_data(self, vegetation: Dict) -> Dict:
        """Nettoie les données de végétation et arbres."""
        try:
            nombre_arbres = max(0, int(vegetation.get("nombre_arbres", 0)))
            surface_espaces_verts = max(0, float(vegetation.get("surface_espaces_verts_ha", 0)))
            pourcentage_vegetation = max(0, min(100, float(vegetation.get("pourcentage_vegetation", 0))))
            arbres_par_km2 = max(0, int(vegetation.get("arbres_par_km2", 0)))
            parcs_et_jardins = max(0, int(vegetation.get("parcs_et_jardins", 0)))
            
            return {
                "nombre_arbres": nombre_arbres,
                "surface_espaces_verts_ha": round(surface_espaces_verts, 2),
                "pourcentage_vegetation": round(pourcentage_vegetation, 2),
                "arbres_par_km2": arbres_par_km2,
                "parcs_et_jardins": parcs_et_jardins,
                "annee": int(vegetation.get("annee", 2024))
            }
        except Exception:
            return {
                "nombre_arbres": 0,
                "surface_espaces_verts_ha": 0.0,
                "pourcentage_vegetation": 0.0,
                "arbres_par_km2": 0,
                "parcs_et_jardins": 0,
                "annee": 2024
            }
    
    def _clean_transports_data(self, transports: Dict) -> Dict:
        """Nettoie les données de transports publics."""
        try:
            stations_metro = max(0, int(transports.get("stations_metro", 0)))
            stations_rer = max(0, int(transports.get("stations_rer", 0)))
            arrets_bus = max(0, int(transports.get("arrets_bus", 0)))
            lignes_metro = max(0, int(transports.get("lignes_metro", 0)))
            lignes_bus = max(0, int(transports.get("lignes_bus", 0)))
            total_transports = stations_metro + stations_rer + arrets_bus
            
            return {
                "stations_metro": stations_metro,
                "stations_rer": stations_rer,
                "arrets_bus": arrets_bus,
                "lignes_metro": lignes_metro,
                "lignes_bus": lignes_bus,
                "total_transports": total_transports,
                "annee": int(transports.get("annee", 2024))
            }
        except Exception:
            return {
                "stations_metro": 0,
                "stations_rer": 0,
                "arrets_bus": 0,
                "lignes_metro": 0,
                "lignes_bus": 0,
                "total_transports": 0,
                "annee": 2024
            }
    
    def silver_to_gold(self, silver_data: Dict) -> Optional[Dict]:
        """
        Transforme les données Silver en Gold (données clean prêtes à utiliser).
        - Agrège les données
        - Calcule les métriques dérivées
        - Structure optimisée pour l'API
        - Ajoute des indicateurs calculés
        """
        logger.info("Transformation Silver -> Gold (donnees clean)...")
        
        try:
            gold_data = {
                "timestamp": silver_data.get("timestamp"),
                "generated_at": datetime.now().isoformat(),
                "integration_report": silver_data.get("integration_report", {}),
                "sources_updated_at": silver_data.get("sources_updated_at"),
                "summary": {
                    "nb_arrondissements": len(silver_data.get("arrondissements", [])),
                    "periode_min": None,
                    "periode_max": None
                },
                "arrondissements": []
            }
            
            all_dates = []
            
            for arr in silver_data.get("arrondissements", []):
                gold_arr = self._enrich_arrondissement_data(arr)
                if gold_arr:
                    gold_data["arrondissements"].append(gold_arr)
                    
                    # Collecter les dates pour le résumé
                    for prix in arr.get("prix_m2_median", []):
                        all_dates.append(prix.get("date"))
            
            # Mettre à jour le résumé
            if all_dates:
                all_dates.sort()
                gold_data["summary"]["periode_min"] = all_dates[0]
                gold_data["summary"]["periode_max"] = all_dates[-1]
            
            logger.info(f"[OK] {len(gold_data['arrondissements'])} arrondissements transformes en Gold")
            return gold_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la transformation Silver -> Gold: {e}")
            return None
    
    def _enrich_arrondissement_data(self, arr: Dict) -> Optional[Dict]:
        """Enrichit les données d'un arrondissement avec des métriques calculées."""
        try:
            prix_list = arr.get("prix_m2_median", [])
            evolution_list = arr.get("evolution", [])
            
            # Calculer les statistiques sur les prix
            prix_values = [p["prix_m2"] for p in prix_list]
            
            stats = {
                "prix_m2_actuel": prix_values[-1] if prix_values else None,
                "prix_m2_min": min(prix_values) if prix_values else None,
                "prix_m2_max": max(prix_values) if prix_values else None,
                "prix_m2_moyen": round(sum(prix_values) / len(prix_values), 2) if prix_values else None,
                "prix_m2_median": sorted(prix_values)[len(prix_values) // 2] if prix_values else None
            }
            
            # Calculer l'évolution du prix
            evolution_calc = None
            if len(prix_values) >= 2:
                prix_initial = prix_values[0]
                prix_final = prix_values[-1]
                evolution_calc = {
                    "variation_absolue": round(prix_final - prix_initial, 2),
                    "variation_pourcentage": round(((prix_final - prix_initial) / prix_initial) * 100, 2) if prix_initial > 0 else 0,
                    "tendance": "hausse" if prix_final > prix_initial else "baisse" if prix_final < prix_initial else "stable"
                }
            
            # Calculer la tendance annuelle
            tendance_annuelle = None
            if len(evolution_list) >= 2:
                evolution_list_sorted = sorted(evolution_list, key=lambda x: x["annee"])
                prix_annee_initial = evolution_list_sorted[0]["prix_m2_median"]
                prix_annee_final = evolution_list_sorted[-1]["prix_m2_median"]
                
                nb_annees = evolution_list_sorted[-1]["annee"] - evolution_list_sorted[0]["annee"]
                if nb_annees > 0:
                    tendance_annuelle = {
                        "variation_annuelle_moyenne": round(((prix_annee_final - prix_annee_initial) / nb_annees), 2),
                        "taux_croissance_annuel": round((((prix_annee_final / prix_annee_initial) ** (1/nb_annees)) - 1) * 100, 2) if prix_annee_initial > 0 else 0
                    }
            
            base = {
                "arrondissement": arr["arrondissement"],
                "nom": arr["nom"],
                "code_insee": arr["code_insee"],
                "statistiques": stats,
                "evolution_calculee": evolution_calc,
                "tendance_annuelle": tendance_annuelle,
                "logements_sociaux_pourcentage": arr["logements_sociaux_pourcentage"],
                "logements_sociaux_evolution": arr.get("logements_sociaux_evolution"),
                "loyers": arr.get("loyers", {}),
                "typologie": arr["typologie"],
                "prix_m2_historique": prix_list,
                "evolution_annuelle": evolution_list,
                # Indicateurs personnalisés
                "pollution_qualite_air": arr.get("pollution_qualite_air", {}),
                "delits_enregistres": arr.get("delits_enregistres", {}),
                "revenus_moyens": arr.get("revenus_moyens", {}),
                "densite_population": arr.get("densite_population", {}),
                "vegetation_arbres": arr.get("vegetation_arbres", {}),
                "transports_publics": arr.get("transports_publics", {}),
                "geocoding": arr.get("geocoding", {}),
                "_sources": arr.get("_sources", {}),
                "metadata": arr.get("metadata", {}),
            }
            from ude_platform.enrichment import enrich_arrondissement
            return enrich_arrondissement(base)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enrichissement de l'arrondissement {arr.get('arrondissement')}: {e}")
            return None
    
    def save_silver_data(self, silver_data: Dict) -> bool:
        """Sauvegarde les données Silver."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"real_estate_data_silver_{timestamp}.json"
            filepath = self.silver_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(silver_data, f, indent=2, ensure_ascii=False)
            
            # Sauvegarder aussi le fichier latest
            latest_filepath = self.silver_dir / "real_estate_data_silver_latest.json"
            with open(latest_filepath, 'w', encoding='utf-8') as f:
                json.dump(silver_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[OK] Donnees Silver sauvegardees dans {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde Silver: {e}")
            return False
    
    def save_gold_data(self, gold_data: Dict) -> bool:
        """Sauvegarde les données Gold."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"real_estate_data_gold_{timestamp}.json"
            filepath = self.gold_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(gold_data, f, indent=2, ensure_ascii=False)
            
            # Sauvegarder aussi le fichier latest
            latest_filepath = self.gold_dir / "real_estate_data_gold_latest.json"
            with open(latest_filepath, 'w', encoding='utf-8') as f:
                json.dump(gold_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"[OK] Donnees Gold sauvegardees dans {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde Gold: {e}")
            return False
    
    def process_pipeline(self, bronze_filename: str = "real_estate_data_latest.json") -> bool:
        """
        Exécute le pipeline complet : Bronze -> Silver -> Gold.
        
        Returns:
            True si le pipeline s'est exécuté avec succès
        """
        logger.info("=" * 60)
        logger.info("Demarrage du pipeline de traitement des donnees")
        logger.info("=" * 60)
        
        # 1. Charger les données Bronze
        bronze_data = self.load_bronze_data(bronze_filename)
        if not bronze_data:
            logger.error("Impossible de charger les donnees Bronze")
            return False
        
        # 2. Transformer Bronze -> Silver
        silver_data = self.bronze_to_silver(bronze_data)
        if not silver_data:
            logger.error("Impossible de transformer Bronze -> Silver")
            return False
        
        # 3. Sauvegarder Silver
        if not self.save_silver_data(silver_data):
            logger.error("Impossible de sauvegarder les donnees Silver")
            return False
        
        # 4. Transformer Silver -> Gold
        gold_data = self.silver_to_gold(silver_data)
        if not gold_data:
            logger.error("Impossible de transformer Silver -> Gold")
            return False
        
        # 5. Sauvegarder Gold
        if not self.save_gold_data(gold_data):
            logger.error("Impossible de sauvegarder les donnees Gold")
            return False

        try:
            from export_tables import TableExporter

            exporter = TableExporter(
                gold_data_file=str(self.gold_dir / "real_estate_data_gold_latest.json")
            )
            if exporter.export_all():
                logger.info("[OK] Export data/export termine")
            else:
                logger.warning("Export data/export non realise (Gold manquant ou erreur)")
        except Exception as e:
            logger.warning("Export data/export ignore : %s", e)

        try:
            from ude_platform.pipeline_orchestration import finalize_pipeline
            metrics = finalize_pipeline(self.gold_dir / "real_estate_data_gold_latest.json")
            logger.info("[OK] Plateforme RNCP : %s", metrics.get("steps"))
        except Exception as e:
            logger.warning("Finalisation plateforme : %s", e)
        
        logger.info("=" * 60)
        logger.info("[OK] Pipeline de traitement termine avec succes")
        logger.info("=" * 60)
        
        return True


def main():
    """Fonction principale."""
    processor = DataProcessor()
    processor.process_pipeline()


if __name__ == "__main__":
    main()

