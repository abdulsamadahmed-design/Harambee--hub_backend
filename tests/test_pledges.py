from datetime import datetime, timezone

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db
from app.routes.pledge_routes import pledge_bp
from app.models.user import User

try:
    from app.models.campaign import Campaign

    CAMPAIGN_AVAILABLE = True
except ImportError:
    Campaign = None
    CAMPAIGN_AVAILABLE = False


@pytest.fixture()
def app():
    application = create_app()
    application.config.update(TESTING=True)
    with application.app_context():
        db.create_all()
        if "pledges" not in application.blueprints:
            application.register_blueprint(pledge_bp)
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def _make_user(app, email, role="contributor"):
    with app.app_context():
        user = User(email=email, name=email.split("@")[0], role=role)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        return user.id


def _make_campaign(app, organizer_id, status="open"):
    with app.app_context():
        campaign = Campaign(
            title="Test Wedding",
            description="Test campaign",
            goal_amount=100000,
            status=status,
            organizer_id=organizer_id,
            end_date=datetime.now(timezone.utc),
        )
        db.session.add(campaign)
        db.session.commit()
        return campaign.id


def _headers(app, user_id):
    with app.app_context():
        token = create_access_token(identity=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def _create_pledge(client, app, campaign_id, contributor_id, **payload):
    return client.post(
        f"/api/pledges/campaign/{campaign_id}",
        json={"amount": 500, **payload},
        headers=_headers(app, contributor_id),
    )




@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_create_pledge_requires_auth(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    campaign_id = _make_campaign(app, organizer_id)
    response = client.post(
        f"/api/pledges/campaign/{campaign_id}", json={"amount": 100}
    )
    assert response.status_code == 401


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_create_pledge_success(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    response = _create_pledge(
        client, app, campaign_id, contributor_id, message="Congrats"
    )
    assert response.status_code == 201
    assert response.get_json()["pledge"]["status"] == "pending"
    assert response.get_json()["pledge"]["amount"] == 500.0


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_create_pledge_validation_and_role(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    invalid = _create_pledge(
        client, app, campaign_id, contributor_id, amount=-5
    )
    assert invalid.status_code == 422

    organizer_response = client.post(
        f"/api/pledges/campaign/{campaign_id}",
        json={"amount": 100},
        headers=_headers(app, organizer_id),
    )
    assert organizer_response.status_code == 403


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_closed_or_missing_campaign_rejected(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id, status="closed")
    headers = _headers(app, contributor_id)

    response = client.post(
        f"/api/pledges/campaign/{campaign_id}",
        json={"amount": 100},
        headers=headers,
    )
    assert response.status_code == 409
    assert client.post(
        "/api/pledges/campaign/999", json={"amount": 100}, headers=headers
    ).status_code == 404


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_anonymous_identity_hidden_public_and_visible_to_organizer(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)
    _create_pledge(client, app, campaign_id, contributor_id, is_anonymous=True)

    public = client.get(f"/api/pledges/campaign/{campaign_id}").get_json()
    assert public["pledges"][0]["contributor"] is None

    managed = client.get(
        f"/api/pledges/campaign/{campaign_id}/manage",
        headers=_headers(app, organizer_id),
    )
    assert managed.status_code == 200
    assert managed.get_json()["pledges"][0]["contributor"]["id"] == contributor_id


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_confirm_updates_raised_amount_and_requires_authorization(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    other_id = _make_user(app, "other@example.com")
    campaign_id = _make_campaign(app, organizer_id)
    created = _create_pledge(
        client, app, campaign_id, contributor_id, amount=750
    ).get_json()["pledge"]

    forbidden = client.post(
        f"/api/pledges/{created['id']}/confirm",
        headers=_headers(app, other_id),
    )
    assert forbidden.status_code == 403

    confirmed = client.post(
        f"/api/pledges/{created['id']}/confirm",
        headers=_headers(app, organizer_id),
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["raised_amount"] == 750.0


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_update_and_cancel_pending_pledge(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)
    headers = _headers(app, contributor_id)
    pledge_id = _create_pledge(
        client, app, campaign_id, contributor_id
    ).get_json()["pledge"]["id"]

    updated = client.patch(
        f"/api/pledges/{pledge_id}",
        json={"amount": 600, "message": "Updated"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.get_json()["pledge"]["amount"] == 600.0

    cancelled = client.delete(f"/api/pledges/{pledge_id}", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.get_json()["pledge"]["status"] == "cancelled"


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_lists_are_paginated_and_cancelled_pledges_are_private(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)
    headers = _headers(app, contributor_id)
    response = _create_pledge(client, app, campaign_id, contributor_id)
    pledge_id = response.get_json()["pledge"]["id"]
    client.delete(f"/api/pledges/{pledge_id}", headers=headers)

    public = client.get(f"/api/pledges/campaign/{campaign_id}?page=1&per_page=5")
    assert public.status_code == 200
    assert public.get_json()["total"] == 0
    assert public.get_json()["per_page"] == 5

    private_status = client.get(
        f"/api/pledges/campaign/{campaign_id}?status=cancelled"
    )
    assert private_status.status_code == 422


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_user_pledge_list_and_confirmed_pledge_cannot_be_cancelled(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)
    pledge_id = _create_pledge(
        client, app, campaign_id, contributor_id
    ).get_json()["pledge"]["id"]

    mine = client.get(
        "/api/pledges/mine", headers=_headers(app, contributor_id)
    )
    assert mine.status_code == 200
    assert mine.get_json()["count"] == 1

    client.post(
        f"/api/pledges/{pledge_id}/confirm",
        headers=_headers(app, organizer_id),
    )
    cancelled = client.delete(
        f"/api/pledges/{pledge_id}",
        headers=_headers(app, contributor_id),
    )
    assert cancelled.status_code == 409


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_get_pledge_requires_relationship_access(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    other_id = _make_user(app, "other@example.com")
    campaign_id = _make_campaign(app, organizer_id)
    pledge_id = _create_pledge(
        client, app, campaign_id, contributor_id
    ).get_json()["pledge"]["id"]

    assert client.get(
        f"/api/pledges/{pledge_id}", headers=_headers(app, other_id)
    ).status_code == 403
    assert client.get(
        f"/api/pledges/{pledge_id}", headers=_headers(app, contributor_id)
    ).status_code == 200


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_update_requires_nonempty_valid_data(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)
    pledge_id = _create_pledge(
        client, app, campaign_id, contributor_id
    ).get_json()["pledge"]["id"]
    headers = _headers(app, contributor_id)

    assert client.patch(
        f"/api/pledges/{pledge_id}", json={}, headers=headers
    ).status_code == 422
    assert client.patch(
        f"/api/pledges/{pledge_id}",
        json={"amount": -2},
        headers=headers,
    ).status_code == 422
