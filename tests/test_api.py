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


def test_mongo_geo_points_bbox_validation(client):
    response = client.get("/mongo/geo-points?min_lon=2.3")
    assert response.status_code == 400
    assert "bbox" in response.json()["detail"].lower()


def test_mongo_geo_points_limit_validation(client):
    response = client.get("/mongo/geo-points?limit=0")
    assert response.status_code == 400
