import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_platform_freshness(client):
    response = client.get("/platform/freshness")
    if response.status_code == 503:
        pytest.skip("Gold non disponible")
    assert response.status_code == 200
    body = response.json()
    assert body["mode_analyse"] == "instant_t_sur_snapshot"
    assert "batch" in body
    assert "streaming" in body
    assert body["api"]["query_latency_ms"] is not None
    assert body["snapshot"]["generated_at"] or body["snapshot"]["gold_file_mtime"]


def test_platform_governance(client):
    response = client.get("/platform/governance")
    assert response.status_code == 200
    body = response.json()
    assert "rate_limit" in body
    assert "auth" in body
    assert body["rate_limit"]["limit_per_ip"] >= 1


def test_arrondissements_includes_freshness(client):
    response = client.get("/arrondissements?annee=2024")
    if response.status_code == 503:
        pytest.skip("Gold non disponible")
    assert response.status_code == 200
    body = response.json()
    assert "freshness" in body
    assert "generated_at" in body
    assert len(body["arrondissements"]) == 20


def test_rate_limit_headers(client):
    response = client.get("/platform/governance")
    assert response.status_code == 200
    assert response.headers.get("x-ratelimit-limit")
