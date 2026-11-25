import hashlib
import re
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.password_recovery_code import PasswordRecoveryCode


def create_recovery_code(user, raw_code, expires_at=None):
    """Create a recovery code directly for testing."""

    recovery = PasswordRecoveryCode(
        user_id=user.id,
        code_hash=hashlib.sha256(
            raw_code.encode("utf-8")
        ).hexdigest(),
        expires_at=expires_at or (
            datetime.now(timezone.utc) + timedelta(minutes=15)
        ),
    )

    db.session.add(recovery)
    db.session.commit()

    return recovery


def test_recovery_code_requires_admin(
    client, make_user, auth_header
):
    assert client.post(
        "/api/admin/users/1/recovery-code"
    ).status_code == 401

    organizer = make_user(role="organizer")

    response = client.post(
        "/api/admin/users/1/recovery-code",
        headers=auth_header(organizer),
    )

    assert response.status_code == 403


def test_admin_can_generate_and_email_recovery_code(
    client, make_user, auth_header, monkeypatch
):
    admin = make_user(role="admin")
    user = make_user(role="organizer")

    sent_email = {}

    def fake_send_email(to_email, subject, body):
        sent_email.update({
            "to": to_email,
            "subject": subject,
            "body": body,
        })
        return True

    monkeypatch.setattr(
        "app.routes.admin_routes.send_email",
        fake_send_email,
    )

    response = client.post(
        f"/api/admin/users/{user.id}/recovery-code",
        headers=auth_header(admin),
    )

    assert response.status_code == 200
    assert sent_email["to"] == user.email

    match = re.search(
        r"Your recovery code is: ([^\s]+)",
        sent_email["body"],
    )
    assert match is not None

    raw_code = match.group(1)

    assert raw_code not in response.get_data(as_text=True)

    recovery = PasswordRecoveryCode.query.filter_by(
        user_id=user.id
    ).first()

    assert recovery is not None
    assert recovery.code_hash == hashlib.sha256(
        raw_code.encode("utf-8")
    ).hexdigest()
    assert recovery.code_hash != raw_code
    assert recovery.created_by_admin_id == admin.id
    assert recovery.used_at is None


def test_admin_cannot_generate_code_for_missing_user(
    client, make_user, auth_header
):
    admin = make_user(role="admin")

    response = client.post(
        "/api/admin/users/99999/recovery-code",
        headers=auth_header(admin),
    )

    assert response.status_code == 404


def test_failed_recovery_email_invalidates_code(
    client, make_user, auth_header, monkeypatch
):
    admin = make_user(role="admin")
    user = make_user(role="organizer")

    monkeypatch.setattr(
        "app.routes.admin_routes.send_email",
        lambda *args, **kwargs: False,
    )

    response = client.post(
        f"/api/admin/users/{user.id}/recovery-code",
        headers=auth_header(admin),
    )

    assert response.status_code == 502

    recovery = PasswordRecoveryCode.query.filter_by(
        user_id=user.id
    ).first()

    assert recovery is not None
    assert recovery.used_at is not None


def test_reset_password_rejects_invalid_code(
    client, make_user
):
    user = make_user(
        email="recovery@example.com",
        password="old-password",
    )

    create_recovery_code(user, "valid-test-code")

    response = client.post(
        "/api/auth/reset-password",
        json={
            "email": user.email,
            "code": "incorrect-code",
            "new_password": "new-password-123",
        },
    )

    assert response.status_code == 400
    assert user.check_password("old-password")


def test_reset_password_rejects_expired_code(
    client, make_user
):
    user = make_user(
        email="expired@example.com",
        password="old-password",
    )

    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    create_recovery_code(
        user,
        "expired-test-code",
        expires_at=expired_at,
    )

    response = client.post(
        "/api/auth/reset-password",
        json={
            "email": user.email,
            "code": "expired-test-code",
            "new_password": "new-password-123",
        },
    )

    assert response.status_code == 400
    assert user.check_password("old-password")


def test_reset_password_success_and_code_cannot_be_reused(
    client, make_user
):
    user = make_user(
        email="success@example.com",
        password="old-password",
    )

    recovery = create_recovery_code(
        user,
        "one-time-test-code",
    )

    other_recovery = create_recovery_code(
        user,
        "another-test-code",
    )

    payload = {
        "email": user.email,
        "code": "one-time-test-code",
        "new_password": "new-password-123",
    }

    response = client.post(
        "/api/auth/reset-password",
        json=payload,
    )

    assert response.status_code == 200

    db.session.refresh(recovery)
    db.session.refresh(other_recovery)

    assert recovery.used_at is not None
    assert other_recovery.used_at is not None
    assert user.check_password("new-password-123")

    # The same recovery code must not work a second time.
    second_response = client.post(
        "/api/auth/reset-password",
        json=payload,
    )

    assert second_response.status_code == 400

    # Confirm the new password works for normal login.
    login_response = client.post(
        "/api/auth/login",
        json={
            "email": user.email,
            "password": "new-password-123",
        },
    )

    assert login_response.status_code == 200


def test_reset_password_rejects_short_password(
    client, make_user
):
    user = make_user(email="short@example.com")

    response = client.post(
        "/api/auth/reset-password",
        json={
            "email": user.email,
            "code": "some-code",
            "new_password": "123",
        },
    )

    assert response.status_code == 422
