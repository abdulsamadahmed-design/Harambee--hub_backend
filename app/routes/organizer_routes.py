from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity
from sqlalchemy import func

from app.extensions import db
from app.models.campaign import Campaign
from app.models.pledge import Pledge
from app.utils.decorators import roles_required


organizer_bp = Blueprint(
    "organizer",
    __name__,
    url_prefix="/api/organizer"
)


@organizer_bp.get("/dashboard")
@roles_required("organizer")
def dashboard_stats():
    """Return statistics for the currently authenticated organizer."""

    organizer_id = int(get_jwt_identity())

    total_campaigns = db.session.scalar(
        db.select(func.count(Campaign.id)).where(
            Campaign.organizer_id == organizer_id
        )
    ) or 0

    active_campaigns = db.session.scalar(
        db.select(func.count(Campaign.id)).where(
            Campaign.organizer_id == organizer_id,
            Campaign.status == "active"
        )
    ) or 0

    contribution_stats = db.session.execute(
        db.select(
            func.count(Pledge.id),
            func.coalesce(func.sum(Pledge.amount), 0)
        )
        .join(Campaign, Pledge.campaign_id == Campaign.id)
        .where(
            Campaign.organizer_id == organizer_id,
            Pledge.status == "confirmed"
        )
    ).one()

    total_contributions, total_amount_raised = contribution_stats

    return jsonify({
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "total_contributions": total_contributions,
        "total_amount_raised": float(total_amount_raised or 0)
    }), 200
