from app import create_app


def test_cors_allows_configured_frontend(monkeypatch):
    origin = "https://frontend.example.com"
    monkeypatch.setenv("FRONTEND_URL", origin)

    app = create_app()
    response = app.test_client().options(
        "/api/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("Access-Control-Allow-Origin") == origin


def test_cors_rejects_unconfigured_frontend(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "https://frontend.example.com")

    app = create_app()
    response = app.test_client().options(
        "/api/health",
        headers={
            "Origin": "https://untrusted.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "Access-Control-Allow-Origin" not in response.headers
