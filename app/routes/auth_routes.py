from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User
from app.utils.errors import error_response

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or "@" not in email or len(password) < 6:
        return error_response("Name, a valid email and a password of 6+ characters are required")
    if User.query.filter_by(email=email).first():
        return error_response("Email already registered", 409)

    role = "admin" if User.query.count() == 0 else "user"
    user = User(name=name, email=email, phone=data.get("phone"), role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(data.get("password") or ""):
        return error_response("Invalid email or password", 401)

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()})


@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    return jsonify(user.to_dict())


@auth_bp.post("/change-password")
@jwt_required()
def change_password():
    data = request.get_json() or {}
    user = db.session.get(User, int(get_jwt_identity()))

    if not user.check_password(data.get("old_password") or ""):
        return error_response("Old password is incorrect", 401)
    if len(data.get("new_password") or "") < 6:
        return error_response("New password must be 6+ characters")

    user.set_password(data["new_password"])
    db.session.commit()
    return jsonify({"message": "Password updated"})