
from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from app.extensions import db
from app.models.user import User
from app.schemas.registration_schema import RegistrationSchema
from app.utils.email import send_verification_email
from app.utils.errors import error_response


registration_bp = Blueprint(
    "registration",
    __name__,
    url_prefix="/api/auth"
)

registration_schema = RegistrationSchema()


def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(
        current_app.config["JWT_SECRET_KEY"],
        salt="harambee-email-verification"
    )
    return serializer.dumps(email)


def verify_email_token(token):
    serializer = URLSafeTimedSerializer(
        current_app.config["JWT_SECRET_KEY"],
        salt="harambee-email-verification"
    )

    try:
        email = serializer.loads(token, max_age=3600)
        return email
    except (BadSignature, SignatureExpired):
        return None


@registration_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}

    try:
        validated_data = registration_schema.load(data)
    except ValidationError as error:
        return jsonify({"errors": error.messages}), 422

    email = validated_data["email"].strip().lower()

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        return error_response("Email already registered", 409)

    user = User(
        name=validated_data["name"].strip(),
        email=email,
        phone=validated_data.get("phone"),
        role=validated_data["role"]
    )

    user.set_password(validated_data["password"])

    try:
        db.session.add(user)
        db.session.commit()

        token = generate_verification_token(user.email)

        verification_url = (
            f"{request.host_url.rstrip('/')}"
            f"/api/auth/verify-email/{token}"
        )

        email_sent = send_verification_email(
            user.email,
            verification_url
        )

        return jsonify({
            "message": (
                "Registration successful. Please check your email "
                "to verify your account."
            ),
            "email_sent": email_sent,
            "user": user.to_dict()
        }), 201

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Registration failed.")
        return error_response("Registration failed. Please try again.", 500)


@registration_bp.get("/verify-email/<token>")
def verify_email(token):
    email = verify_email_token(token)

    if not email:
        return error_response(
            "Verification link is invalid or has expired.",
            400
        )

    user = User.query.filter_by(email=email).first()

    if not user:
        return error_response("User not found.", 404)

    if user.email_verified:
        return jsonify({
            "message": "Email is already verified."
        }), 200

    try:
        user.email_verified = True
        db.session.commit()

        return jsonify({
            "message": "Email verified successfully."
        }), 200

    except Exception:
        db.session.rollback()
        current_app.logger.exception("Email verification failed.")
        return error_response(
            "Could not verify email. Please try again.",
            500
        )
