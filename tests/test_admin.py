def test_admin_users_requires_authentication(client):
    response = client.get("/api/admin/users")
    assert response.status_code == 401


def test_contributor_cannot_list_users(client, make_user, auth_header):
    contributor = make_user(role="contributor")
    response = client.get(
        "/api/admin/users",
        headers=auth_header(contributor)
    )
    assert response.status_code == 403


def test_organizer_can_list_users(client, make_user, auth_header):
    organizer = make_user(role="organizer")
    make_user(role="contributor")

    response = client.get(
        "/api/admin/users",
        headers=auth_header(organizer)
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["per_page"] == 10
    assert data["pages"] == 1
    assert len(data["items"]) == 2

    for user in data["items"]:
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert user["role"] in ("organizer", "contributor")
        assert "password_hash" not in user


def test_user_without_role_claim_cannot_list_users(
    client, make_user, auth_header
):
    organizer = make_user(role="organizer")
    response = client.get(
        "/api/admin/users",
        headers=auth_header(organizer, with_role=False)
    )
    assert response.status_code == 403


def test_organizer_users_pagination(client, make_user, auth_header):
    organizer = make_user(role="organizer")

    for number in range(12):
        make_user(role="contributor", name="Contributor {}".format(number))

    response = client.get(
        "/api/admin/users?page=2&per_page=5",
        headers=auth_header(organizer)
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["page"] == 2
    assert data["per_page"] == 5
    assert data["total"] == 13
    assert data["pages"] == 3
    assert len(data["items"]) == 5
    ids = [user["id"] for user in data["items"]]
    assert ids == sorted(ids)


def test_organizer_users_rejects_invalid_page(client, make_user, auth_header):
    organizer = make_user(role="organizer")
    response = client.get(
        "/api/admin/users?page=abc",
        headers=auth_header(organizer)
    )
    assert response.status_code == 422


def test_dashboard_requires_authentication(client):
    response = client.get("/api/admin/dashboard")
    assert response.status_code == 401


def test_contributor_cannot_access_dashboard(client, make_user, auth_header):
    contributor = make_user(role="contributor")
    response = client.get(
        "/api/admin/dashboard",
        headers=auth_header(contributor)
    )
    assert response.status_code == 403


def test_organizer_can_access_dashboard_and_view_statistics(
    client, make_user, auth_header
):
    from app.extensions import db
    from app.models.campaign import Campaign
    from app.models.pledge import Pledge

    organizer = make_user(role="organizer")
    make_user(role="contributor")

    campaign = Campaign(
        title="School Fundraiser",
        description="Raising money to support students with school fees.",
        goal_amount=100000,
        organizer_id=organizer.id,
        status="active"
    )
    db.session.add(campaign)
    db.session.commit()

    pledges = [
        Pledge(campaign_id=campaign.id, amount=10, status="pending"),
        Pledge(campaign_id=campaign.id, amount=20, status="confirmed"),
        Pledge(campaign_id=campaign.id, amount=30, status="cancelled"),
    ]
    db.session.add_all(pledges)
    db.session.commit()

    response = client.get(
        "/api/admin/dashboard",
        headers=auth_header(organizer)
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["users_by_role"] == {
        "organizer": 1,
        "contributor": 1
    }
    assert data["campaigns_by_status"] == {"active": 1}
    assert data["total_pledged"] == "60.00"
    assert data["total_confirmed"] == "20.00"
    assert data["pledges_by_status"] == {
        "pending": 1,
        "confirmed": 1,
        "cancelled": 1
    }


def test_seed_organizer_refuses_missing_credentials(app, monkeypatch):
    monkeypatch.delenv("ORGANIZER_EMAIL", raising=False)
    monkeypatch.delenv("ORGANIZER_PASSWORD", raising=False)

    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-organizer"])

    assert result.exit_code != 0
    assert "ORGANIZER_EMAIL and ORGANIZER_PASSWORD" in result.output


def test_seed_organizer_creates_verified_organizer(app, monkeypatch):
    from app.models.user import User

    monkeypatch.setenv("ORGANIZER_EMAIL", "organizer@example.com")
    monkeypatch.setenv("ORGANIZER_PASSWORD", "StrongPassword123!")

    runner = app.test_cli_runner()
    result = runner.invoke(args=["seed-organizer"])

    assert result.exit_code == 0
    assert "Organizer account created successfully." in result.output

    with app.app_context():
        organizer = User.query.filter_by(email="organizer@example.com").first()
        assert organizer is not None
        assert organizer.role == "organizer"
        assert organizer.email_verified is True
        assert organizer.check_password("StrongPassword123!")


def test_seed_organizer_does_not_reset_existing_password(app, monkeypatch):
    from app.models.user import User

    monkeypatch.setenv("ORGANIZER_EMAIL", "organizer@example.com")
    monkeypatch.setenv("ORGANIZER_PASSWORD", "OriginalPassword123!")

    runner = app.test_cli_runner()
    first_result = runner.invoke(args=["seed-organizer"])
    assert first_result.exit_code == 0

    with app.app_context():
        organizer = User.query.filter_by(email="organizer@example.com").first()
        original_hash = organizer.password_hash

    monkeypatch.setenv("ORGANIZER_PASSWORD", "DifferentPassword456!")
    second_result = runner.invoke(args=["seed-organizer"])

    assert second_result.exit_code == 0
    assert "Organizer already exists" in second_result.output

    with app.app_context():
        organizer = User.query.filter_by(email="organizer@example.com").first()
        assert organizer.password_hash == original_hash
        assert organizer.check_password("OriginalPassword123!")
        assert not organizer.check_password("DifferentPassword456!")
