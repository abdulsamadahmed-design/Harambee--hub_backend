import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func

from app.extensions import db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.pledge import Pledge
from app.models.password_recovery_code import PasswordRecoveryCode

from app.utils.decorators import roles_required
from app.utils.email import send_email
from app.utils.errors import error_response
from app.utils.pagination import paginate_query


admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/api/admin"
)


@admin_bp.get("/users")
@roles_required("admin")
def list_users():
    """Return a paginated list of users."""
    try:
        result = paginate_query(
            User.query.order_by(User.id.asc()),
            serializer=lambda user: user.to_dict()
        )

        return jsonify(result), 200

    except ValueError as error:
        return error_response(str(error), 422)


@admin_bp.post("/users/<int:user_id>/recovery-code")
@roles_required("admin")
def generate_recovery_code(user_id):
    """Generate and email a one-time password recovery code."""

    user = db.session.get(User, user_id)

    if not user:
        return error_response("User not found", 404)

    now = datetime.now(timezone.utc)

    # Generate a cryptographically secure recovery code.
    code = secrets.token_urlsafe(16)

    # Store only the SHA-256 hash of the code.
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()

    # Invalidate any previous unused recovery codes for this user.
    PasswordRecoveryCode.query.filter_by(
        user_id=user.id,
        used_at=None
    ).update(
        {"used_at": now},
        synchronize_session=False
    )

    recovery = PasswordRecoveryCode(
        user_id=user.id,
        created_by_admin_id=int(get_jwt_identity()),
        code_hash=code_hash,
        expires_at=now + timedelta(minutes=15),
    )

    db.session.add(recovery)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response(
            "Unable to generate recovery code",
            500
        )

    body = (
        f"Hello {user.name},\n\n"
        "An administrator has requested a password recovery code "
        "for your Harambee Hub account.\n\n"
        f"Your recovery code is: {code}\n\n"
        "This code expires in 15 minutes and can only be used once.\n\n"
        "If you did not expect this email, contact the Harambee Hub "
        "administration team."
    )

    email_sent = send_email(
        user.email,
        "Harambee Hub Password Recovery",
        body
    )

    if not email_sent:
        recovery.used_at = datetime.now(timezone.utc)
        db.session.commit()

        return error_response(
            "Recovery email could not be sent. Please try again.",
            502
        )

    return jsonify({
        "message": "Recovery code sent to the user's registered email.",
        "expires_in_minutes": 15
    }), 200
@admin_bp.get("/dashboard")
@roles_required("admin")
def dashboard_stats():
    """Return platform statistics for administrators."""

    users_by_role = {
        role or "unassigned": count
        for role, count in db.session.query(
            User.role, func.count(User.id)
        ).group_by(User.role).all()
    }

    campaigns_by_status = {
        status: count
        for status, count in db.session.query(
            Campaign.status, func.count(Campaign.id)
        ).group_by(Campaign.status).all()
    }

    pledges_by_status = {
        status: count
        for status, count in db.session.query(
            Pledge.status, func.count(Pledge.id)
        ).group_by(Pledge.status).all()
    }

    total_pledged = db.session.query(
        func.coalesce(func.sum(Pledge.amount), 0)
    ).filter(Pledge.status.in_(["pending", "confirmed"])).scalar()

    total_confirmed = db.session.query(
        func.coalesce(func.sum(Pledge.amount), 0)
    ).filter(Pledge.status == "confirmed").scalar()

    return jsonify({
        "users_by_role": users_by_role,
        "campaigns_by_status": campaigns_by_status,
        "total_pledged": str(total_pledged),
        "total_confirmed": str(total_confirmed),
        "pledges_by_status": pledges_by_status,
    }), 200
