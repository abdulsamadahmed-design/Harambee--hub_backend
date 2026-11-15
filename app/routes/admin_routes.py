from flask import Blueprint, jsonify
from sqlalchemy import func

from app.extensions import db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.pledge import Pledge
from app.utils.decorators import roles_required
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
