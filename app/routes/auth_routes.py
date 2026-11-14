
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

from app.extensions import db
from app.models.user import User
from app.utils.errors import error_response


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# LOGIN
@auth_bp.post("/login")
def login():
    data = request.get_json() or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return error_response("Invalid email or password", 401)

    token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )

    return jsonify({
        "token": token,
        "user": user.to_dict()
    }), 200


# GET CURRENT LOGGED-IN USER
@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))

    if not user:
        return error_response("User not found", 404)

    return jsonify(user.to_dict()), 200


# CHANGE PASSWORD
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
