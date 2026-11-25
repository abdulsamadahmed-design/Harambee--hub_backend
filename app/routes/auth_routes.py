import hashlib

from datetime import datetime, timezone

from marshmallow import ValidationError

from app.models.password_recovery_code import PasswordRecoveryCode
from app.schemas.auth_schema import PasswordResetSchema

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from marshmallow import ValidationError

from app.extensions import db
from app.models.user import User
from app.schemas.auth_schema import LoginSchema
from app.utils.errors import error_response


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    try:
        data = LoginSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({
            "error": "Validation failed",
            "details": err.messages,
        }), 422

    email = data["email"]
    password = data["password"]

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return error_response("Invalid email or password", 401)

    if not user.email_verified:
        return error_response("Please verify your email before logging in", 403)

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )

    refresh_token = create_refresh_token(
        identity=str(user.id),
    )


    return jsonify({
        "token": token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    }), 200

@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    if not user:
        return error_response("User not found", 404)

    new_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )

    return jsonify({
        "token": new_token
    }), 200

@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    if not user:
        return error_response("User not found", 404)

    return jsonify(user.to_dict()), 200


@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    data = request.get_json() or {}

    user = db.session.get(User, int(get_jwt_identity()))

    if not user:
        return error_response("User not found", 404)

    if not user.check_password(data.get("old_password") or ""):
        return error_response("Old password is incorrect", 401)

    new_password = data.get("new_password") or ""

    if len(new_password) < 8:
        return error_response(
            "New password must be at least 8 characters",
            400
        )

    user.set_password(new_password)
    db.session.commit()

    return jsonify({"message": "Password updated"}), 200

@auth_bp.post("/reset-password")
def reset_password():
    """Reset a user's password using a valid recovery code."""

    try:
        data = PasswordResetSchema().load(
            request.get_json(silent=True) or {}
        )
    except ValidationError as err:
        return jsonify({
            "error": "Validation failed",
            "details": err.messages,
        }), 422

    email = data["email"]
    code = data["code"]
    new_password = data["new_password"]

    user = User.query.filter_by(email=email).first()

    if not user:
        return error_response(
            "Invalid or expired recovery code",
            400
        )

    code_hash = hashlib.sha256(
        code.encode("utf-8")
    ).hexdigest()

    recovery = PasswordRecoveryCode.query.filter_by(
        user_id=user.id,
        code_hash=code_hash,
        used_at=None
    ).with_for_update().first()

    if not recovery:
        return error_response(
            "Invalid or expired recovery code",
            400
        )

    now = datetime.now(timezone.utc)
    expires_at = recovery.expires_at

    # Handle naive datetimes returned by SQLite during tests.
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        return error_response(
            "Invalid or expired recovery code",
            400
        )

    user.set_password(new_password)
    recovery.used_at = now

    # Invalidate any other outstanding codes for this user.
    PasswordRecoveryCode.query.filter(
        PasswordRecoveryCode.user_id == user.id,
        PasswordRecoveryCode.used_at.is_(None),
        PasswordRecoveryCode.id != recovery.id,
    ).update(
        {"used_at": now},
        synchronize_session=False
    )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return error_response(
            "Unable to reset password",
            500
        )

    return jsonify({
        "message": "Password reset successfully. You can now log in."
    }), 200
