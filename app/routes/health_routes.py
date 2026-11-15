from flask import Blueprint, jsonify
from app.extensions import db
from app.utils.errors import error_response

health_bp = Blueprint("health", __name__, url_prefix="/api")


# GET /api/health: hosting sites call this to check that the app is alive
@health_bp.get("/health")
def health():
    try:
        # Ask the database a tiny question to prove the connection works
        db.session.execute(db.text("SELECT 1"))
    except Exception:
        return error_response("Database unavailable", 503)
    return jsonify({"status": "ok"})
