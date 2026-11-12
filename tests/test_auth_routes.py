"""Tests for /api/auth/login, /me and /change-password, plus global errors.

Users are created straight in the database with the make_user fixture, NOT
through the register endpoint. Registration is owned by M2 and its behaviour
will change (email verification), so these tests must not depend on it.
Registration tests belong in tests/test_registration.py (M2).
"""
import pytest
from flask_jwt_extended import decode_token

EMAIL = "amina@example.com"
PASSWORD = "secret123"


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


# ---------- login ----------


def test_login_success_returns_token_and_user(client, make_user):
    make_user(role="organizer", email=EMAIL, password=PASSWORD)
    response = login(client)
    assert response.status_code == 200
    body = response.get_json()
    assert body["token"]
    assert body["user"]["email"] == EMAIL
    assert body["user"]["role"] == "organizer"


def test_login_never_returns_the_password_or_hash(client, make_user):
    make_user(email=EMAIL, password=PASSWORD)
    user = login(client).get_json()["user"]
    assert "password" not in user
    assert "password_hash" not in user


@pytest.mark.parametrize("role", ["organizer", "contributor", "admin"])
def test_login_token_contains_the_role_claim(client, make_user, role):
    make_user(role=role, email=EMAIL, password=PASSWORD)
    token = login(client).get_json()["token"]
    assert decode_token(token)["role"] == role


def test_login_email_is_case_and_space_insensitive(client, make_user):
    make_user(email=EMAIL, password=PASSWORD)
    assert login(client, email="  AMINA@example.com ").status_code == 200


def test_login_wrong_password_returns_401(client, make_user):
    make_user(email=EMAIL, password=PASSWORD)
    response = login(client, password="wrong-password")
    assert response.status_code == 401
    assert "error" in response.get_json()


def test_login_unknown_email_returns_401(client):
    assert login(client, email="nobody@example.com").status_code == 401


def test_login_gives_the_same_error_for_wrong_password_and_unknown_email(client, make_user):
    """The message must not reveal which of the two was wrong."""
    make_user(email=EMAIL, password=PASSWORD)
    wrong_password = login(client, password="wrong-password").get_json()
    unknown_email = login(client, email="nobody@example.com").get_json()
    assert wrong_password == unknown_email


def test_login_with_an_empty_body_is_rejected(client):
    response = client.post("/api/auth/login", json={})
    # 401 today. 422 once the route uses LoginSchema.
    assert response.status_code in (401, 422)
    assert "error" in response.get_json()


# ---------- me ----------


def test_me_returns_the_logged_in_user(client, make_user, auth_header):
    user = make_user(role="contributor", email=EMAIL)
    response = client.get("/api/auth/me", headers=auth_header(user))
    assert response.status_code == 200
    body = response.get_json()
    assert body["email"] == EMAIL
    assert body["role"] == "contributor"


def test_me_without_a_token_returns_401_json(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "error" in response.get_json()


# ---------- change password ----------


def test_change_password_success_then_login_with_new_password(client, make_user, auth_header):
    user = make_user(email=EMAIL, password=PASSWORD)
    response = client.post(
        "/api/auth/change-password",
        headers=auth_header(user),
        json={"old_password": PASSWORD, "new_password": "brand-new-pass"},
    )
    assert response.status_code == 200
    assert login(client, password="brand-new-pass").status_code == 200
    assert login(client, password=PASSWORD).status_code == 401


def test_change_password_with_wrong_old_password_returns_401(client, make_user, auth_header):
    user = make_user(email=EMAIL, password=PASSWORD)
    response = client.post(
        "/api/auth/change-password",
        headers=auth_header(user),
        json={"old_password": "not-my-password", "new_password": "brand-new-pass"},
    )
    assert response.status_code == 401


def test_change_password_with_short_new_password_returns_400(client, make_user, auth_header):
    user = make_user(email=EMAIL, password=PASSWORD)
    response = client.post(
        "/api/auth/change-password",
        headers=auth_header(user),
        json={"old_password": PASSWORD, "new_password": "abc"},
    )
    assert response.status_code == 400


def test_change_password_requires_a_token(client):
    response = client.post(
        "/api/auth/change-password",
        json={"old_password": PASSWORD, "new_password": "brand-new-pass"},
    )
    assert response.status_code == 401


# ---------- global error handling ----------


def test_unknown_url_returns_a_json_404(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_wrong_method_is_rejected_with_405(client):
    assert client.get("/api/auth/login").status_code == 405
