"""Enrichissement métier : accessibilité, loyers, évolution logements sociaux."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

LOYER_PRIX_RATIO = 320.0  # repli si pas de données encadrement

_LOGEMENTS_SOCIAUX_TAUX_2024: Dict[int, float] = {
    1: 14.2, 2: 11.8, 3: 15.1, 4: 17.5, 5: 22.3,
    6: 14.8, 7: 11.2, 8: 10.5, 9: 16.4, 10: 19.1,
    11: 17.2, 12: 22.8, 13: 28.5, 14: 20.3, 15: 21.6,
    16: 9.8, 17: 13.9, 18: 21.4, 19: 24.2, 20: 26.1,
}


def _prix_m2_for_year(arr: Dict[str, Any], year: Optional[int] = None) -> Optional[float]:
    y = year or 2024
    for ev in arr.get("evolution_annuelle") or []:
        if ev.get("annee") == y and ev.get("prix_m2_median"):
            return float(ev["prix_m2_median"])
    stats = arr.get("statistiques") or {}
    if stats.get("prix_m2_actuel"):
        return float(stats["prix_m2_actuel"])
    return None


def logements_sociaux_evolution_fallback(arr_num: int, years: List[int] = None) -> List[Dict[str, Any]]:
    """Série de repli si le pipeline n'a pas fourni l'évolution open data."""
    years = years or list(range(2018, 2025))
    taux_2024 = _LOGEMENTS_SOCIAUX_TAUX_2024.get(arr_num, 21.0)
    taux_2018 = round(taux_2024 - 1.8, 2)
    span = max(len(years) - 1, 1)
    return [
        {
            "annee": y,
            "logements_sociaux_pct": round(
                taux_2018 + (taux_2024 - taux_2018) * (i / span), 2
            ),
        }
        for i, y in enumerate(sorted(years))
    ]


def _pollution_local_index(arr: Dict[str, Any], pollution: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy inter-arrondissements : indice Paris (Citeair) ajusté par densité et transports."""
    pol = dict(pollution)
    base = float(pol.get("indice_atmo") or 5)
    dens = (arr.get("densite_population") or {}).get("densite_km2")
    trans = (arr.get("transports_publics") or {}).get("total_transports") or 0
    if dens:
        dens_norm = max(0.0, min(1.0, (float(dens) - 8000) / 30000))
        trans_norm = max(0.0, min(1.0, (float(trans) - 26) / 43))
        factor = 0.88 + (0.6 * dens_norm + 0.4 * trans_norm) * 0.24
        pol["indice_atmo_local"] = round(min(10.0, max(1.0, base * factor)), 2)
        pol["indice_atmo_paris"] = base
        pol["methode_local"] = (
            "Indice Citeair Paris ajusté par densité et offre de transports (proxy arrondissement)"
        )
    else:
        pol["indice_atmo_local"] = base
    return pol


def enrich_arrondissement(arr: Dict[str, Any], year: Optional[int] = None) -> Dict[str, Any]:
    """Ajoute accessibilité, loyers, surface, évolution logements sociaux."""
    out = dict(arr)
    arr_num = int(arr.get("arrondissement", 0))
    prix_m2 = _prix_m2_for_year(arr, year)
    revenu = (arr.get("revenus_moyens") or {}).get("revenu_median_menage")
    typologie = arr.get("typologie") or {}
    stats = arr.get("statistiques") or {}
    surface = typologie.get("surface_moyenne_m2") or stats.get("surface_moyenne_m2")

    loyers = dict(arr.get("loyers") or {})
    if not loyers.get("loyer_m2_median") and prix_m2:
        loyers["loyer_m2_median"] = round(prix_m2 / LOYER_PRIX_RATIO, 2)
        loyers["methode"] = "estimation_marche_prix_vente"
    out["loyers"] = loyers

    loyer_m2 = loyers.get("loyer_m2_median")
    access: Dict[str, Any] = dict(arr.get("accessibilite_logement") or {})
    if prix_m2 and revenu and revenu > 0:
        access["mois_revenu_pour_50m2_achat"] = round((prix_m2 * 50) / (revenu / 12), 1)
        access["prix_m2_reference"] = round(prix_m2, 0)
    if loyer_m2 and revenu and revenu > 0:
        access["mois_revenu_pour_50m2_location"] = round(
            (loyer_m2 * 50 * 12) / (revenu / 12), 1
        )
        access["part_revenu_loyer_50m2_pct"] = round((loyer_m2 * 50 * 12 / revenu) * 100, 1)
        access["loyer_m2_median"] = loyer_m2
    if surface:
        access["surface_moyenne_m2"] = round(float(surface), 1)
    out["accessibilite_logement"] = access

    if arr.get("pollution_qualite_air"):
        out["pollution_qualite_air"] = _pollution_local_index(arr, arr["pollution_qualite_air"])

    if arr.get("logements_sociaux_evolution"):
        out["logements_sociaux_evolution"] = arr["logements_sociaux_evolution"]
    else:
        out["logements_sociaux_evolution"] = logements_sociaux_evolution_fallback(arr_num)

    return out


def enrich_all(arrondissements: List[Dict[str, Any]], year: Optional[int] = None) -> List[Dict[str, Any]]:
    return [enrich_arrondissement(a, year) for a in arrondissements]
