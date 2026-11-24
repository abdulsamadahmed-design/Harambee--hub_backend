from datetime import datetime, timezone

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.user import User

try:
    from app.models.campaign import Campaign

    CAMPAIGN_AVAILABLE = True
except ImportError:
    Campaign = None
    CAMPAIGN_AVAILABLE = False


def _make_user(app, email, role="contributor"):
    with app.app_context():
        user = User(email=email, name=email.split("@")[0], role=role)
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()
        return user.id


def _make_campaign(app, organizer_id, status="active"):
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
def test_contributor_full_name_visible_in_public_and_organizer_pledge_lists(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    created = _create_pledge(
        client, app, campaign_id, contributor_id
    )
    assert created.status_code == 201

    public = client.get(f"/api/pledges/campaign/{campaign_id}")
    assert public.status_code == 200
    public_pledge = public.get_json()["items"][0]
    assert public_pledge["contributor"]["id"] == contributor_id
    assert public_pledge["contributor"]["name"] == "contributor"
    assert "is_anonymous" not in public_pledge

    managed = client.get(
        f"/api/pledges/campaign/{campaign_id}/manage",
        headers=_headers(app, organizer_id),
    )
    assert managed.status_code == 200
    managed_pledge = managed.get_json()["items"][0]
    assert managed_pledge["contributor"]["name"] == "contributor"
    assert "is_anonymous" not in managed_pledge


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


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_remind_pledge_returns_error_when_email_fails(
    client, app, monkeypatch
):
    from app.routes import pledge_routes

    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    pledge_id = _create_pledge(
        client, app, campaign_id, contributor_id
    ).get_json()["pledge"]["id"]

    monkeypatch.setattr(
        pledge_routes, "send_email", lambda *args: False
    )

    response = client.post(
        f"/api/pledges/{pledge_id}/remind",
        headers=_headers(app, organizer_id),
    )

    assert response.status_code == 502
    assert response.get_json()["error"] == (
        "Failed to send pledge reminder"
    )


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_pledge_can_be_created_for_api_created_campaign(
    client, app, make_user, auth_header
):
    organizer = make_user(role="organizer")
    contributor = make_user(role="contributor")

    campaign_response = client.post(
        "/api/campaigns/",
        headers=auth_header(organizer),
        json={
            "title": "Community Library",
            "description": "Raising funds to build a community library.",
            "goal_amount": "50000.00",
        },
    )

    assert campaign_response.status_code == 201
    campaign = campaign_response.get_json()
    assert campaign["status"] == "active"

    pledge_response = client.post(
        f"/api/pledges/campaign/{campaign['id']}",
        headers=auth_header(contributor),
        json={"amount": 500},
    )

    assert pledge_response.status_code == 201
    assert pledge_response.get_json()["pledge"]["status"] == "pending"


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not available"
)
def test_pledge_lists_reject_invalid_page(client, app):
    organizer_id = _make_user(app, "organizer@example.com", "organizer")
    contributor_id = _make_user(app, "contributor@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    public_response = client.get(
        f"/api/pledges/campaign/{campaign_id}?page=abc"
    )

    mine_response = client.get(
        "/api/pledges/mine?page=abc",
        headers=_headers(app, contributor_id),
    )

    manage_response = client.get(
        f"/api/pledges/campaign/{campaign_id}/manage?page=abc",
        headers=_headers(app, organizer_id),
    )

    assert public_response.status_code == 422
    assert mine_response.status_code == 422
    assert manage_response.status_code == 422


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
@pytest.mark.parametrize("role", ["organizer", "contributor"])
def test_pledge_management_creation_endpoint_is_removed(
    client, app, role
):
    user_id = _make_user(app, f"{role}@example.com", role)
    response = client.post(
        "/api/pledges/campaign/1/manage",
        json={"amount": 1000},
        headers=_headers(app, user_id),
    )

    assert response.status_code == 405


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_organizer_can_cancel_pending_pledge_on_own_campaign(
    client, app
):
    from app.models.pledge import Pledge

    organizer_id = _make_user(app, "owner@example.com", "organizer")
    contributor_id = _make_user(app, "supporter@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    created = _create_pledge(client, app, campaign_id, contributor_id)
    pledge_id = created.json["pledge"]["id"]

    response = client.delete(
        f"/api/pledges/{pledge_id}",
        headers=_headers(app, organizer_id),
    )

    assert response.status_code == 200

    with app.app_context():
        pledge = db.session.get(Pledge, pledge_id)
        assert pledge.status == "cancelled"


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_other_organizer_cannot_cancel_pledge(client, app):
    organizer_id = _make_user(app, "owner@example.com", "organizer")
    other_id = _make_user(app, "other@example.com", "organizer")
    contributor_id = _make_user(app, "supporter@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    created = _create_pledge(client, app, campaign_id, contributor_id)
    pledge_id = created.json["pledge"]["id"]

    response = client.delete(
        f"/api/pledges/{pledge_id}",
        headers=_headers(app, other_id),
    )

    assert response.status_code == 403

    from app.models.pledge import Pledge

    with app.app_context():
        pledge = db.session.get(Pledge, pledge_id)
        assert pledge.status == "pending"


@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE, reason="campaign.py not merged yet (M3)"
)
def test_organizer_cannot_cancel_confirmed_pledge(client, app):
    organizer_id = _make_user(app, "owner@example.com", "organizer")
    contributor_id = _make_user(app, "supporter@example.com")
    campaign_id = _make_campaign(app, organizer_id)

    created = _create_pledge(client, app, campaign_id, contributor_id)
    pledge_id = created.json["pledge"]["id"]

    confirmed = client.post(
        f"/api/pledges/{pledge_id}/confirm",
        headers=_headers(app, organizer_id),
    )
    assert confirmed.status_code == 200

    cancelled = client.delete(
        f"/api/pledges/{pledge_id}",
        headers=_headers(app, organizer_id),
    )

    assert cancelled.status_code == 409

@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE,
    reason="campaign.py not merged yet (M3)",
)
def test_organizer_pledges_only_show_own_campaigns(client, app):
    organizer_id = _make_user(app, "owner@example.com", "organizer")
    other_id = _make_user(app, "other@example.com", "organizer")
    contributor_id = _make_user(app, "supporter@example.com")

    own_campaign = _make_campaign(app, organizer_id)
    other_campaign = _make_campaign(app, other_id)

    own_pledge = _create_pledge(
        client, app, own_campaign, contributor_id
    )
    other_pledge = _create_pledge(
        client, app, other_campaign, contributor_id
    )

    response = client.get(
        "/api/pledges/",
        headers=_headers(app, organizer_id),
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["total"] == 1
    assert data["items"][0]["id"] == own_pledge.json["pledge"]["id"]
    assert data["items"][0]["id"] != other_pledge.json["pledge"]["id"]
    assert data["items"][0]["campaign"]["id"] == own_campaign

@pytest.mark.skipif(
    not CAMPAIGN_AVAILABLE,
    reason="campaign.py not merged yet (M3)",
)
def test_other_organizer_cannot_view_manage_or_confirm_pledge(client, app):
    owner_id = _make_user(app, "owner@example.com", "organizer")
    other_id = _make_user(app, "other@example.com", "organizer")
    contributor_id = _make_user(app, "supporter@example.com")

    campaign_id = _make_campaign(app, owner_id)
    created = _create_pledge(client, app, campaign_id, contributor_id)
    pledge_id = created.json["pledge"]["id"]
    headers = _headers(app, other_id)

    view_response = client.get(
        f"/api/pledges/{pledge_id}", headers=headers
    )
    manage_response = client.get(
        f"/api/pledges/campaign/{campaign_id}/manage", headers=headers
    )
    confirm_response = client.post(
        f"/api/pledges/{pledge_id}/confirm", headers=headers
    )

    assert view_response.status_code == 403
    assert manage_response.status_code == 403
    assert confirm_response.status_code == 403
