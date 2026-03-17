import pytest

from ude_platform.enrichment import enrich_arrondissement, logements_sociaux_evolution_fallback


def test_enrich_uses_pipeline_loyers():
    arr = {
        "arrondissement": 6,
        "loyers": {"loyer_m2_median": 32.5, "methode": "encadrement_loyers_paris"},
        "revenus_moyens": {"revenu_median_menage": 40000},
        "evolution_annuelle": [{"annee": 2024, "prix_m2_median": 12000}],
    }
    out = enrich_arrondissement(arr, year=2024)
    assert out["loyers"]["loyer_m2_median"] == 32.5
    assert out["accessibilite_logement"]["loyer_m2_median"] == 32.5
    assert out["accessibilite_logement"]["part_revenu_loyer_50m2_pct"] > 0


def test_enrich_fallback_loyer_from_prix():
    arr = {
        "arrondissement": 1,
        "revenus_moyens": {"revenu_median_menage": 35000},
        "evolution_annuelle": [{"annee": 2024, "prix_m2_median": 9600}],
    }
    out = enrich_arrondissement(arr, year=2024)
    assert out["loyers"]["methode"] == "estimation_marche_prix_vente"
    assert out["loyers"]["loyer_m2_median"] == pytest.approx(30.0, rel=0.01)


def test_logements_sociaux_evolution_from_pipeline():
    evolution = [
        {"annee": 2018, "logements_sociaux_pct": 20.0, "logements_livres": 100},
        {"annee": 2024, "logements_sociaux_pct": 22.0, "logements_livres": 50},
    ]
    arr = {"arrondissement": 13, "logements_sociaux_evolution": evolution}
    out = enrich_arrondissement(arr)
    assert out["logements_sociaux_evolution"] == evolution


def test_logements_sociaux_evolution_fallback_shape():
    series = logements_sociaux_evolution_fallback(13)
    assert len(series) == 7
    assert series[0]["annee"] == 2018
    assert series[-1]["logements_sociaux_pct"] == pytest.approx(28.5, rel=0.01)


def test_pollution_local_index_varies_by_density():
    base = {"indice_atmo": 4.0, "qualite": "moyenne"}
    low = enrich_arrondissement({
        "arrondissement": 16,
        "pollution_qualite_air": base,
        "densite_population": {"densite_km2": 9000},
        "transports_publics": {"total_transports": 30},
    })
    high = enrich_arrondissement({
        "arrondissement": 11,
        "pollution_qualite_air": base,
        "densite_population": {"densite_km2": 35000},
        "transports_publics": {"total_transports": 65},
    })
    low_idx = low["pollution_qualite_air"]["indice_atmo_local"]
    high_idx = high["pollution_qualite_air"]["indice_atmo_local"]
    assert low_idx < high_idx
    assert low["pollution_qualite_air"]["indice_atmo_paris"] == 4.0
