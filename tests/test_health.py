from app.extensions import db


def test_health_returns_ok_without_a_token(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_reports_503_when_the_database_is_down(client, monkeypatch):
    def broken_execute(*args, **kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr(db.session, "execute", broken_execute)

    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.get_json() == {"status": "error", "database": "unreachable"}


def test_health_does_not_leak_error_details(client, monkeypatch):
    def broken_execute(*args, **kwargs):
        raise RuntimeError("password=super-secret host=10.0.0.5")

    monkeypatch.setattr(db.session, "execute", broken_execute)

    body = client.get("/api/health").get_data(as_text=True)
    assert "super-secret" not in body
    assert "10.0.0.5" not in body


def test_health_only_allows_get(client):
    assert client.post("/api/health").status_code == 405
