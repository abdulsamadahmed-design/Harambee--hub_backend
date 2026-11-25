import pytest

from app.extensions import db
from app.models.campaign import Campaign
from app.models.pledge import Pledge


def create_campaign(organizer, title, status="active"):
    campaign = Campaign(
        title=title,
        description=f"Description for {title}",
        goal_amount=1000,
        organizer_id=organizer.id,
        status=status,
    )
    db.session.add(campaign)
    db.session.commit()
    return campaign


def create_pledge(campaign, amount, status):
    pledge = Pledge(
        campaign_id=campaign.id,
        amount=amount,
        status=status,
    )
    db.session.add(pledge)
    db.session.commit()
    return pledge


def test_organizer_dashboard_requires_authentication(client):
    response = client.get("/api/organizer/dashboard")

    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "contributor"])
def test_non_organizers_cannot_access_dashboard(
    client, make_user, auth_header, role
):
    user = make_user(role=role)

    response = client.get(
        "/api/organizer/dashboard",
        headers=auth_header(user),
    )

    assert response.status_code == 403


def test_organizer_dashboard_returns_own_statistics(
    client, make_user, auth_header
):
    organizer = make_user(role="organizer")
    other_organizer = make_user(
        role="organizer",
        email="other@example.com",
    )

    campaign_one = create_campaign(
        organizer, "School Project", "active"
    )
    campaign_two = create_campaign(
        organizer, "Hospital Project", "completed"
    )

    other_campaign = create_campaign(
        other_organizer, "Other Organizer Project", "active"
    )

    # Confirmed pledges belonging to this organizer.
    create_pledge(campaign_one, 125, "confirmed")
    create_pledge(campaign_two, 225, "confirmed")

    # These should not count as received contributions.
    create_pledge(campaign_one, 75, "pending")
    create_pledge(campaign_two, 500, "cancelled")

    # Another organizer's contribution must not be included.
    create_pledge(other_campaign, 1000, "confirmed")

    response = client.get(
        "/api/organizer/dashboard",
        headers=auth_header(organizer),
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data == {
        "total_campaigns": 2,
        "active_campaigns": 1,
        "total_contributions": 2,
        "total_amount_raised": 350.0,
    }


def test_organizer_dashboard_returns_zero_when_no_campaigns(
    client, make_user, auth_header
):
    organizer = make_user(role="organizer")

    response = client.get(
        "/api/organizer/dashboard",
        headers=auth_header(organizer),
    )

    assert response.status_code == 200

    assert response.get_json() == {
        "total_campaigns": 0,
        "active_campaigns": 0,
        "total_contributions": 0,
        "total_amount_raised": 0.0,
    }
