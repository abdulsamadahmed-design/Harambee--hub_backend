from datetime import timedelta

import pytest
from flask import jsonify

from app.utils.decorators import roles_required


@pytest.fixture()
def guarded_client(app):
    """Adds two protected demo routes to the app and returns a test client."""

    @app.get("/_test/organizer")
    @roles_required("organizer")
    def organizer_only():
        return jsonify({"ok": True})

    @app.get("/_test/staff")
    @roles_required("organizer", "admin")
    def staff_only():
        return jsonify({"ok": True})

    return app.test_client()


def test_no_token_returns_401(guarded_client):
    response = guarded_client.get("/_test/organizer")
    assert response.status_code == 401


def test_malformed_token_is_rejected(guarded_client):
    response = guarded_client.get(
        "/_test/organizer", headers={"Authorization": "Bearer not-a-real-token"}
    )
    # Flask-JWT-Extended answers 422 by default. Tighten this to 401 once
    # errors.py registers an invalid_token_loader that returns 401.
    assert response.status_code in (401, 422)


def test_expired_token_returns_401(guarded_client, make_user, auth_header):
    user = make_user(role="organizer")
    headers = auth_header(user, expires_delta=timedelta(seconds=-1))
    response = guarded_client.get("/_test/organizer", headers=headers)
    assert response.status_code == 401


def test_wrong_role_returns_403_with_json_error(guarded_client, make_user, auth_header):
    contributor = make_user(role="contributor")
    response = guarded_client.get(
        "/_test/organizer", headers=auth_header(contributor)
    )
    assert response.status_code == 403
    assert "error" in response.get_json()


def test_right_role_returns_200(guarded_client, make_user, auth_header):
    organizer = make_user(role="organizer")
    response = guarded_client.get("/_test/organizer", headers=auth_header(organizer))
    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


@pytest.mark.parametrize("role", ["organizer", "admin"])
def test_any_of_several_allowed_roles_passes(guarded_client, make_user, auth_header, role):
    user = make_user(role=role)
    response = guarded_client.get("/_test/staff", headers=auth_header(user))
    assert response.status_code == 200


def test_role_outside_the_allowed_list_is_blocked(guarded_client, make_user, auth_header):
    contributor = make_user(role="contributor")
    response = guarded_client.get("/_test/staff", headers=auth_header(contributor))
    assert response.status_code == 403


def test_token_without_role_claim_returns_403(guarded_client, make_user, auth_header):
    organizer = make_user(role="organizer")
    headers = auth_header(organizer, with_role=False)
    response = guarded_client.get("/_test/organizer", headers=headers)
    assert response.status_code == 403
