import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body


def test_arrondissements_list(client):
    response = client.get("/arrondissements")
    if response.status_code == 503:
        pytest.skip("Gold non disponible")
    assert response.status_code == 200
    data = response.json()
    assert "arrondissements" in data
    assert len(data["arrondissements"]) == 20
    first = data["arrondissements"][0]
    assert (first.get("vegetation_arbres") or {}).get("nombre_arbres", 0) > 0
    assert (first.get("transports_publics") or {}).get("total_transports", 0) > 0


def test_iris_list_uses_official_grid_and_native_indicators(client):
    response = client.get("/iris?arrondissement=3&annee=2024")
    if response.status_code == 503:
        pytest.skip("Gold non disponible")
    assert response.status_code == 200
    body = response.json()
    assert body["maille"] == "IRIS"
    assert body["nombre"] > 1
    assert all(item["arrondissement"] == 3 for item in body["iris"])
    assert all(item["indicateurs_niveau"] == "iris" for item in body["iris"])
    assert all(len(item["code_iris"]) == 9 for item in body["iris"])
    assert any(item["population"] is not None for item in body["iris"])
    assert any(item["prix_m2"] is not None for item in body["iris"])


def test_iris_geojson_and_detail(client):
    geo_response = client.get("/iris/geojson?arrondissement=1")
    assert geo_response.status_code == 200
    geojson = geo_response.json()
    assert geojson["type"] == "FeatureCollection"
    assert geojson["features"]
    code_iris = geojson["features"][0]["properties"]["code_iris"]

    detail_response = client.get(f"/iris/{code_iris}")
    if detail_response.status_code == 503:
        pytest.skip("Gold non disponible")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["code_iris"] == code_iris
    assert detail["donnees_arrondissement_parent"]["arrondissement"] == 1


def test_iris_rejects_invalid_arrondissement(client):
    response = client.get("/iris?arrondissement=21")
    assert response.status_code == 400


def test_mongo_geo_points_bbox_validation(client):
    response = client.get("/mongo/geo-points?min_lon=2.3")
    assert response.status_code == 400
    assert "bbox" in response.json()["detail"].lower()


def test_mongo_geo_points_limit_validation(client):
    response = client.get("/mongo/geo-points?limit=0")
    assert response.status_code == 400
