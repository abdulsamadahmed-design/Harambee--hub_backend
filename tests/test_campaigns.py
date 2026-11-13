
from app.extensions import db
from app.models.campaign import Campaign


def test_list_campaigns_empty(client):
    response = client.get("/api/campaigns/")

    assert response.status_code == 200
    assert response.json["items"] == []
    assert response.json["total"] == 0


def test_get_campaign_not_found(client):
    response = client.get("/api/campaigns/999")

    assert response.status_code == 404


def test_create_campaign_requires_authentication(client):
    response = client.post(
        "/api/campaigns/",
        json={
            "title": "School Fundraiser",
            "description": "Raising money to support students with school fees.",
            "goal_amount": "50000.00"
        }
    )

    assert response.status_code == 401


def test_contributor_cannot_create_campaign(client, make_user, auth_header):
    contributor = make_user(role="contributor")

    response = client.post(
        "/api/campaigns/",
        headers=auth_header(contributor),
        json={
            "title": "School Fundraiser",
            "description": "Raising money to support students with school fees.",
            "goal_amount": "50000.00"
        }
    )

    assert response.status_code == 403


def test_organizer_can_create_campaign(client, make_user, auth_header):
    organizer = make_user(role="organizer")

    response = client.post(
        "/api/campaigns/",
        headers=auth_header(organizer),
        json={
            "title": "School Fundraiser",
            "description": "Raising money to support students with school fees.",
            "goal_amount": "50000.00"
        }
    )

    assert response.status_code == 201
    assert response.json["title"] == "School Fundraiser"
    assert response.json["organizer_id"] == organizer.id


def test_create_campaign_validation_error(client, make_user, auth_header):
    organizer = make_user(role="organizer")

    response = client.post(
        "/api/campaigns/",
        headers=auth_header(organizer),
        json={
            "title": "Hi",
            "goal_amount": "50000.00"
        }
    )

    assert response.status_code == 400
    assert "errors" in response.json


def test_list_campaigns_returns_campaigns(app, client, make_user):
    organizer = make_user(role="organizer")

    campaign = Campaign(
        title="School Fundraiser",
        description="Raising money to support students with school fees.",
        goal_amount=50000.00,
        organizer_id=organizer.id
    )

    db.session.add(campaign)
    db.session.commit()

    response = client.get("/api/campaigns/")

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["items"][0]["title"] == "School Fundraiser"
