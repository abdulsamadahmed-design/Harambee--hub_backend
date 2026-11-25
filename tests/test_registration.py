from datetime import datetime, timedelta, timezone

import time
import itsdangerous.timed

import pytest

from app.extensions import db
from app.models.user import User
from app.routes.registration_routes import generate_verification_token


def valid_registration_data():
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
        "phone": "0712345678",
        "role": "contributor"
    }


def test_successful_registration(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        lambda email, url: True
    )

    response = client.post(
        "/api/auth/register",
        json=valid_registration_data()
    )

    assert response.status_code == 201
    assert response.json["email_sent"] is True
    assert response.json["user"]["email"] == "test@example.com"
    assert "password" not in response.json["user"]
    assert "password_hash" not in response.json["user"]

    with app.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        assert user is not None
        assert user.email_verified is False
        assert user.password_hash != "password123"
        assert user.check_password("password123")


def test_registration_missing_fields(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com"}
    )

    assert response.status_code == 422


def test_registration_invalid_email(client):
    data = valid_registration_data()
    data["email"] = "not-an-email"

    response = client.post("/api/auth/register", json=data)

    assert response.status_code == 422


def test_registration_invalid_role(client):
    data = valid_registration_data()
    data["role"] = "admin"

    response = client.post("/api/auth/register", json=data)

    assert response.status_code == 422


def test_registration_short_password(client):
    data = valid_registration_data()
    data["password"] = "12345"

    response = client.post("/api/auth/register", json=data)

    assert response.status_code == 422


def test_registration_duplicate_email(client, app, monkeypatch):
    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        lambda email, url: True
    )

    client.post("/api/auth/register", json=valid_registration_data())

    response = client.post(
        "/api/auth/register",
        json=valid_registration_data()
    )

    assert response.status_code == 409


def test_registration_email_failure(client, monkeypatch):
    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        lambda email, url: False
    )

    response = client.post(
        "/api/auth/register",
        json=valid_registration_data()
    )

    assert response.status_code == 201
    assert response.json["email_sent"] is False


def test_successful_email_verification(client, app):
    with app.app_context():
        user = User(
            name="Test User",
            email="verify@example.com",
            role="contributor"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        token = generate_verification_token(user.email)

    response = client.get(f"/api/auth/verify-email/{token}")

    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="verify@example.com").first()
        assert user.email_verified is True


def test_invalid_email_verification_token(client):
    response = client.get("/api/auth/verify-email/invalid-token")

    assert response.status_code == 400


def test_expired_email_verification_token(client, app, monkeypatch):
    real_time = time.time

    with app.app_context():
        with monkeypatch.context() as patch:
            patch.setattr(
                itsdangerous.timed.time,
                "time",
                lambda: real_time() - 7200
            )
            token = generate_verification_token("expired@example.com")

    response = client.get(f"/api/auth/verify-email/{token}")

    assert response.status_code == 400

def test_resend_verification_sends_email_to_unverified_user(
    client, make_user, monkeypatch
):
    user = make_user(
        email="resend@example.com",
        email_verified=False
    )

    captured = {}

    def fake_send(email, url):
        captured["email"] = email
        captured["url"] = url
        return True

    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        fake_send
    )

    response = client.post(
        "/api/auth/resend-verification",
        json={"email": "resend@example.com"}
    )

    assert response.status_code == 200
    assert captured["email"] == user.email
    assert "/api/auth/verify-email/" in captured["url"]
    assert user.last_verification_sent_at is not None


def test_resend_verification_respects_60_second_cooldown(
    client, make_user, monkeypatch
):
    user = make_user(
        email="cooldown@example.com",
        email_verified=False
    )

    user.last_verification_sent_at = (
        datetime.now(timezone.utc) - timedelta(seconds=30)
    )
    db.session.commit()

    sent = []

    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        lambda email, url: sent.append(email) or True
    )

    response = client.post(
        "/api/auth/resend-verification",
        json={"email": user.email}
    )

    assert response.status_code == 200
    assert sent == []


def test_resend_verification_does_not_send_to_verified_user(
    client, make_user, monkeypatch
):
    user = make_user(email="verified@example.com")

    sent = []

    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        lambda email, url: sent.append(email) or True
    )

    response = client.post(
        "/api/auth/resend-verification",
        json={"email": user.email}
    )

    assert response.status_code == 200
    assert sent == []


def test_resend_verification_unknown_email_returns_generic_response(
    client, monkeypatch
):
    sent = []

    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        lambda email, url: sent.append(email) or True
    )

    response = client.post(
        "/api/auth/resend-verification",
        json={"email": "unknown@example.com"}
    )

    assert response.status_code == 200
    assert sent == []


def test_resend_verification_rejects_invalid_email(client):
    response = client.post(
        "/api/auth/resend-verification",
        json={"email": "not-an-email"}
    )

    assert response.status_code == 422


def test_registration_cooldown_blocks_immediate_resend(
    client, monkeypatch
):
    sent = []

    monkeypatch.setattr(
        "app.routes.registration_routes.send_verification_email",
        lambda email, url: sent.append(email) or True
    )

    registration = client.post(
        "/api/auth/register",
        json=valid_registration_data()
    )

    assert registration.status_code == 201
    assert len(sent) == 1

    resend = client.post(
        "/api/auth/resend-verification",
        json={"email": "test@example.com"}
    )

    assert resend.status_code == 200
    assert len(sent) == 1
