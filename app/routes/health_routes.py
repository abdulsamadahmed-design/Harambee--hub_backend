from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from app.extensions import db

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.get("/health")
def health():
    """Tell a host (or a person) whether the API and its database are alive.

    Public on purpose: hosting platforms call it without a token. It returns
    no secrets and no internal error details.
    """
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:
        current_app.logger.exception("Health check failed: database unreachable")
        return jsonify({"status": "error", "database": "unreachable"}), 503

    return jsonify({"status": "ok", "database": "ok"}), 200
