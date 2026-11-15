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


def test_organizer_cannot_list_users(client, make_user, auth_header):
    organizer = make_user(role="organizer")

    response = client.get(
        "/api/admin/users",
        headers=auth_header(organizer)
    )

    assert response.status_code == 403


def test_user_without_role_claim_cannot_list_users(
    client, make_user, auth_header
):
    admin = make_user(role="admin")

    response = client.get(
        "/api/admin/users",
        headers=auth_header(admin, with_role=False)
    )

    assert response.status_code == 403


def test_admin_can_list_users(client, make_user, auth_header):
    admin = make_user(role="admin")
    make_user(role="contributor")
    make_user(role="organizer")

    response = client.get(
        "/api/admin/users",
        headers=auth_header(admin)
    )

    assert response.status_code == 200

    data = response.get_json()

    assert data["total"] == 3
    assert data["page"] == 1
    assert data["per_page"] == 10
    assert data["pages"] == 1
    assert len(data["items"]) == 3

    for user in data["items"]:
        assert "id" in user
        assert "name" in user
        assert "email" in user
        assert "role" in user
        assert "password_hash" not in user


def test_admin_users_pagination(client, make_user, auth_header):
    admin = make_user(role="admin")

    for number in range(12):
        make_user(
            role="contributor",
            name="Contributor {}".format(number)
        )

    response = client.get(
        "/api/admin/users?page=2&per_page=5",
        headers=auth_header(admin)
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


def test_admin_users_rejects_invalid_page(client, make_user, auth_header):
    admin = make_user(role="admin")

    response = client.get(
        "/api/admin/users?page=abc",
        headers=auth_header(admin)
    )

    assert response.status_code == 400
