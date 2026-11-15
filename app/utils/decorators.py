from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def roles_required(*allowed_roles):
    """Allow a route only for logged-in users whose role is in allowed_roles.

    Usage:
        @campaign_bp.route("/campaigns", methods=["POST"])
        @roles_required("organizer")
        def create_campaign():
            ...
    """

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
        

            verify_jwt_in_request()

            role = get_jwt().get("role")
            if role not in allowed_roles:
                return jsonify({"error": "You do not have permission to do this."}), 403

            return view(*args, **kwargs)

        return wrapper

    return decorator