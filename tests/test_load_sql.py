import statistics
import time

import pytest
from fastapi.testclient import TestClient

from api import app


def _postgres_available() -> bool:
    try:
        import psycopg2
        from ude_platform.config import POSTGRES_READER_URL

        conn = psycopg2.connect(POSTGRES_READER_URL, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.skipif(not _postgres_available(), reason="PostgreSQL requis (docker compose up postgres)")
def test_sql_accessibilite_load_integrity():
    """Tests de charge légers : intégrité + latence vue SQL."""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from ude_platform.config import POSTGRES_READER_URL

    conn = psycopg2.connect(POSTGRES_READER_URL, connect_timeout=3)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    durations = []
    last_rows = None

    for _ in range(50):
        t0 = time.perf_counter()
        cur.execute("SELECT * FROM v_accessibilite_prix_revenu ORDER BY arrondissement")
        rows = cur.fetchall()
        durations.append(time.perf_counter() - t0)
        last_rows = rows

    cur.close()
    conn.close()

    assert last_rows is not None
    assert len(last_rows) == 20
    for row in last_rows:
        assert row["arrondissement"] is not None
        if row["mois_revenu_pour_50m2"] is not None:
            assert row["mois_revenu_pour_50m2"] > 0

    p95 = statistics.quantiles(durations, n=20)[-1] if len(durations) >= 20 else max(durations)
    assert statistics.mean(durations) < 0.15, f"moyenne {statistics.mean(durations):.3f}s trop élevée"
    assert p95 < 0.5, f"p95 {p95:.3f}s trop élevé"


@pytest.mark.skipif(not _postgres_available(), reason="PostgreSQL requis")
def test_sql_governance_reader_select_only():
    import psycopg2
    from ude_platform.config import POSTGRES_READER_URL

    conn = psycopg2.connect(POSTGRES_READER_URL, connect_timeout=3)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM governance_access")
    assert cur.fetchone()[0] >= 2
    cur.close()
    conn.close()
