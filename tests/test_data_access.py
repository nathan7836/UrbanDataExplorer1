from ude_platform.data_access import _merge_json_supplements


def test_merge_json_supplements_restores_vegetation_and_transports():
    sql_arrs = [
        {
            "arrondissement": 6,
            "nom": "6e",
            "pollution_qualite_air": {"indice_atmo": 1.2},
        }
    ]
    out = _merge_json_supplements(sql_arrs)
    veg = out[0].get("vegetation_arbres") or {}
    trans = out[0].get("transports_publics") or {}
    assert veg.get("nombre_arbres", 0) > 0
    assert trans.get("total_transports", 0) > 0
    assert out[0]["pollution_qualite_air"].get("pm25_moyen") is not None
