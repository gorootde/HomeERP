"""Coverage for backend/routers/health.py (the external-monitoring probe)."""


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["version"] == "1.0.0"


def test_health_in_openapi(client):
    spec = client.get("/openapi.json").json()
    assert "/api/health" in spec["paths"]
    assert "health" in spec["paths"]["/api/health"]["get"]["tags"]


def test_health_degraded_when_db_down(client, monkeypatch):
    """A dead database keeps the endpoint at HTTP 200 but flips the fields so a
    keyword monitor (Uptime Kuma) can detect it."""
    from sqlalchemy.orm import Session

    def _boom(self, *_args, **_kwargs):
        raise RuntimeError("db gone")

    monkeypatch.setattr(Session, "execute", _boom)

    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "degraded", "version": "1.0.0", "database": "error"}
