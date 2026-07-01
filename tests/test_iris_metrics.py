import json
from pathlib import Path

from ude_platform.iris_metrics import _geometry_area_km2, _point_in_geometry


METRICS = Path("dashboard/static/data/paris_iris_metrics.json")


def test_geometry_helpers_support_polygon_and_hole():
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [[2.0, 48.0], [2.1, 48.0], [2.1, 48.1], [2.0, 48.1], [2.0, 48.0]],
            [[2.04, 48.04], [2.06, 48.04], [2.06, 48.06], [2.04, 48.06], [2.04, 48.04]],
        ],
    }
    assert _point_in_geometry(2.02, 48.02, geometry)
    assert not _point_in_geometry(2.05, 48.05, geometry)
    assert _geometry_area_km2(geometry) > 0


def test_native_iris_snapshot_has_expected_coverage():
    payload = json.loads(METRICS.read_text(encoding="utf-8"))
    iris = payload["iris"]
    assert len(iris) == 992
    assert sum("population" in item for item in iris.values()) == 992
    assert sum("logements" in item for item in iris.values()) == 992
    assert sum("immobilier" in item for item in iris.values()) >= 800
    assert sum("vegetation" in item for item in iris.values()) >= 900
    assert payload["minimum_transactions_dvf"] == 3


def test_native_metrics_do_not_contain_parent_fallback():
    payload = json.loads(METRICS.read_text(encoding="utf-8"))
    forbidden = {"donnees_arrondissement_parent", "indicateurs_herites"}
    assert all(not forbidden.intersection(item) for item in payload["iris"].values())
