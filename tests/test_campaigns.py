
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
    assert response.json["status"] == "active"


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


def test_create_campaign_returns_502_when_image_upload_fails(
    client, make_user, auth_header, monkeypatch
):
    from io import BytesIO
    from app.routes import campaign_routes

    organizer = make_user(role="organizer")

    def fail_upload(image_file):
        raise RuntimeError("Cloudinary is unavailable")

    monkeypatch.setattr(campaign_routes, "upload_image", fail_upload)

    response = client.post(
        "/api/campaigns/",
        headers=auth_header(organizer),
        data={
            "title": "School Fundraiser",
            "description": "Raising money to support students with school fees.",
            "goal_amount": "50000.00",
            "image": (BytesIO(b"fake image data"), "school.jpg"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 502
    assert response.json["error"] == "Image upload failed. Please try again."
    assert Campaign.query.count() == 0


def test_client_cannot_set_campaign_image_url(client, make_user, auth_header):
    organizer = make_user(role="organizer")

    response = client.post(
        "/api/campaigns/",
        headers=auth_header(organizer),
        json={
            "title": "School Fundraiser",
            "description": "Raising money to support students with school fees.",
            "goal_amount": "50000.00",
            "image_url": "https://example.com/fake.jpg"
        }
    )

    assert response.status_code == 400
    assert "image_url" in response.json["errors"]
    assert Campaign.query.count() == 0


def test_create_campaign_rejects_request_over_6mb(
    client, make_user, auth_header
):
    from io import BytesIO

    organizer = make_user(role="organizer")

    response = client.post(
        "/api/campaigns/",
        headers=auth_header(organizer),
        data={
            "title": "School Fundraiser",
            "description": "Raising money to support students with school fees.",
            "goal_amount": "50000.00",
            "image": (
                BytesIO(b"\xff\xd8\xff" + b"x" * (6 * 1024 * 1024)),
                "large.jpg",
            ),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 413
    assert response.json["error"] == (
        "Request is too large. Maximum size is 6 MB."
    )
    assert Campaign.query.count() == 0


def test_list_campaigns_rejects_invalid_page(client):
    response = client.get("/api/campaigns/?page=abc")

    assert response.status_code == 422
    assert "error" in response.json


def test_organizer_can_update_own_campaign(client, make_user, auth_header):
    organizer = make_user(role="organizer")
    campaign = Campaign(
        title="Old Campaign",
        description="This is the original campaign description.",
        goal_amount=50000,
        organizer_id=organizer.id,
    )
    db.session.add(campaign)
    db.session.commit()

    response = client.patch(
        "/api/campaigns/{}".format(campaign.id),
        headers=auth_header(organizer),
        json={"title": "Updated Campaign"},
    )

    assert response.status_code == 200
    assert response.json["title"] == "Updated Campaign"


def test_organizer_cannot_update_another_organizers_campaign(
    client, make_user, auth_header
):
    owner = make_user(role="organizer")
    other_organizer = make_user(role="organizer")

    campaign = Campaign(
        title="Owner Campaign",
        description="This campaign belongs to another organizer.",
        goal_amount=50000,
        organizer_id=owner.id,
    )
    db.session.add(campaign)
    db.session.commit()

    response = client.patch(
        "/api/campaigns/{}".format(campaign.id),
        headers=auth_header(other_organizer),
        json={"title": "Unauthorized Change"},
    )

    assert response.status_code == 403
    db.session.refresh(campaign)
    assert campaign.title == "Owner Campaign"


def test_organizer_can_delete_own_campaign_without_pledges(
    client, make_user, auth_header
):
    organizer = make_user(role="organizer")
    campaign = Campaign(
        title="Campaign to Delete",
        description="This campaign has no pledge records.",
        goal_amount=50000,
        organizer_id=organizer.id,
    )
    db.session.add(campaign)
    db.session.commit()

    response = client.delete(
        "/api/campaigns/{}".format(campaign.id),
        headers=auth_header(organizer),
    )

    assert response.status_code == 200
    assert db.session.get(Campaign, campaign.id) is None


def test_organizer_cannot_delete_another_organizers_campaign(
    client, make_user, auth_header
):
    owner = make_user(role="organizer")
    other_organizer = make_user(role="organizer")

    campaign = Campaign(
        title="Owner Campaign",
        description="This campaign belongs to another organizer.",
        goal_amount=50000,
        organizer_id=owner.id,
    )
    db.session.add(campaign)
    db.session.commit()

    response = client.delete(
        "/api/campaigns/{}".format(campaign.id),
        headers=auth_header(other_organizer),
    )

    assert response.status_code == 403
    assert db.session.get(Campaign, campaign.id) is not None


def test_campaign_with_pledge_history_cannot_be_deleted(
    client, make_user, auth_header
):
    from app.models.pledge import Pledge

    organizer = make_user(role="organizer")
    campaign = Campaign(
        title="Fundraiser with Pledge",
        description="This campaign already has a pledge record.",
        goal_amount=50000,
        organizer_id=organizer.id,
    )
    db.session.add(campaign)
    db.session.flush()

    pledge = Pledge(
        campaign_id=campaign.id,
        amount=1000,
        status="pending",
    )
    db.session.add(pledge)
    db.session.commit()

    response = client.delete(
        "/api/campaigns/{}".format(campaign.id),
        headers=auth_header(organizer),
    )

    assert response.status_code == 409
    assert db.session.get(Campaign, campaign.id) is not None
    assert db.session.get(Pledge, pledge.id) is not None


def test_list_campaigns_filters_by_search(client, make_user):
    organizer = make_user(role="organizer")

    matching = Campaign(
        title="School Fundraiser",
        description="Helping students pay school fees.",
        goal_amount=50000,
        organizer_id=organizer.id,
    )
    other = Campaign(
        title="Hospital Support",
        description="Helping patients access treatment.",
        goal_amount=80000,
        organizer_id=organizer.id,
    )
    db.session.add_all([matching, other])
    db.session.commit()

    response = client.get("/api/campaigns/?search=school")

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["items"][0]["title"] == "School Fundraiser"


def test_list_campaigns_searches_description(client, make_user):
    organizer = make_user(role="organizer")

    campaign = Campaign(
        title="Community Support",
        description="Providing books for rural students.",
        goal_amount=50000,
        organizer_id=organizer.id,
    )
    db.session.add(campaign)
    db.session.commit()

    response = client.get("/api/campaigns/?search=rural")

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["items"][0]["title"] == "Community Support"


def test_list_campaigns_filters_by_status(client, make_user):
    organizer = make_user(role="organizer")

    active = Campaign(
        title="Active Campaign",
        description="This campaign is currently active.",
        goal_amount=50000,
        status="active",
        organizer_id=organizer.id,
    )
    closed = Campaign(
        title="Closed Campaign",
        description="This campaign is already closed.",
        goal_amount=50000,
        status="closed",
        organizer_id=organizer.id,
    )
    db.session.add_all([active, closed])
    db.session.commit()

    response = client.get("/api/campaigns/?status=active")

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["items"][0]["title"] == "Active Campaign"


def test_list_campaigns_completed_filter_matches_closed_status(
    client, make_user
):
    organizer = make_user(role="organizer")

    campaign = Campaign(
        title="Closed Campaign",
        description="This campaign is already closed.",
        goal_amount=50000,
        status="closed",
        organizer_id=organizer.id,
    )
    db.session.add(campaign)
    db.session.commit()

    response = client.get("/api/campaigns/?status=completed")

    assert response.status_code == 200
    assert response.json["total"] == 1
    assert response.json["items"][0]["status"] == "closed"


def test_list_campaigns_sorts_by_highest_goal(client, make_user):
    organizer = make_user(role="organizer")

    low = Campaign(
        title="Low Goal",
        description="This campaign has a smaller goal.",
        goal_amount=10000,
        organizer_id=organizer.id,
    )
    high = Campaign(
        title="High Goal",
        description="This campaign has a larger goal.",
        goal_amount=90000,
        organizer_id=organizer.id,
    )
    db.session.add_all([low, high])
    db.session.commit()

    response = client.get("/api/campaigns/?sort=goal-high")

    assert response.status_code == 200
    assert response.json["items"][0]["title"] == "High Goal"


def test_list_campaigns_sorts_by_lowest_goal(client, make_user):
    organizer = make_user(role="organizer")

    low = Campaign(
        title="Low Goal",
        description="This campaign has a smaller goal.",
        goal_amount=10000,
        organizer_id=organizer.id,
    )
    high = Campaign(
        title="High Goal",
        description="This campaign has a larger goal.",
        goal_amount=90000,
        organizer_id=organizer.id,
    )
    db.session.add_all([low, high])
    db.session.commit()

    response = client.get("/api/campaigns/?sort=goal-low")

    assert response.status_code == 200
    assert response.json["items"][0]["title"] == "Low Goal"


def test_list_campaigns_sorts_by_ending_date_with_missing_dates_last(
    client, make_user
):
    from datetime import datetime, timezone, timedelta

    organizer = make_user(role="organizer")
    soon = Campaign(
        title="Ending Soon",
        description="This campaign ends soon.",
        goal_amount=50000,
        end_date=datetime.now(timezone.utc) + timedelta(days=2),
        organizer_id=organizer.id,
    )
    later = Campaign(
        title="Ending Later",
        description="This campaign ends later.",
        goal_amount=50000,
        end_date=datetime.now(timezone.utc) + timedelta(days=10),
        organizer_id=organizer.id,
    )
    no_date = Campaign(
        title="No End Date",
        description="This campaign has no end date.",
        goal_amount=50000,
        end_date=None,
        organizer_id=organizer.id,
    )
    db.session.add_all([no_date, later, soon])
    db.session.commit()

    response = client.get("/api/campaigns/?sort=ending")

    assert response.status_code == 200
    titles = [item["title"] for item in response.json["items"]]
    assert titles == ["Ending Soon", "Ending Later", "No End Date"]


def test_list_campaigns_rejects_invalid_sort(client):
    response = client.get("/api/campaigns/?sort=unknown")

    assert response.status_code == 422
    assert "error" in response.json


def test_list_campaigns_paginates_after_filtering(client, make_user):
    organizer = make_user(role="organizer")

    campaigns = [
        Campaign(
            title="School Campaign {}".format(number),
            description="Supporting students with school fees.",
            goal_amount=50000,
            organizer_id=organizer.id,
        )
        for number in range(3)
    ]
    other = Campaign(
        title="Hospital Campaign",
        description="Supporting patients in hospitals.",
        goal_amount=50000,
        organizer_id=organizer.id,
    )
    db.session.add_all(campaigns + [other])
    db.session.commit()

    response = client.get(
        "/api/campaigns/?search=school&page=1&per_page=2"
    )

    assert response.status_code == 200
    assert response.json["total"] == 3
    assert response.json["pages"] == 2
    assert len(response.json["items"]) == 2
