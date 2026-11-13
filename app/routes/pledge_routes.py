from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, g, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from marshmallow import ValidationError
from sqlalchemy import func

from app.extensions import db
from app.models.pledge import Pledge
from app.models.user import User
from app.schemas.pledge_schema import (
    pledge_create_schema,
    pledge_query_schema,
    pledge_update_schema,
)

try:
    from app.models.campaign import Campaign
except ImportError:
    Campaign = None

try:
    from app.utils.email import send_email
except ImportError:
    send_email = None

try:
    from app.utils.pagination import paginate
except ImportError:
    paginate = None

pledge_bp = Blueprint("pledges", __name__, url_prefix="/api/pledges")


def _current_user():
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None
    return db.session.get(User, user_id)


def _require_user(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = _current_user()
        if user is None:
            return jsonify({"error": "User not found"}), 401
        g.user = user
        return fn(*args, **kwargs)

    return wrapper


def _error(message, code=400, details=None):
    body = {"error": message}
    if details:
        body["details"] = details
    return jsonify(body), code


def _get_campaign(campaign_id):
    return db.session.get(Campaign, campaign_id)


def _raised_for(campaign_id):
    total = db.session.scalar(
        db.select(func.coalesce(func.sum(Pledge.amount), 0)).where(
            Pledge.campaign_id == campaign_id,
            Pledge.status == "confirmed",
        )
    )
    return float(total or 0)


def _status_counts(campaign_id):
    rows = db.session.execute(
        db.select(Pledge.status, func.count(Pledge.id))
        .where(Pledge.campaign_id == campaign_id)
        .group_by(Pledge.status)
    ).all()
    counts = {status: 0 for status in Pledge.VALID_STATUSES}
    counts.update({status: count for status, count in rows})
    return counts


def _page(query, page, per_page):
    page = max(int(page or 1), 1)
    per_page = min(max(int(per_page or 10), 1), 100)
    ordered_query = query.order_by(Pledge.created_at.desc())

    if paginate is not None:
        # The shared helper currently accepts a Flask-SQLAlchemy Query.
        if not hasattr(ordered_query, "paginate"):
            statement = ordered_query
            ordered_query = db.session.query(Pledge)
            if statement.whereclause is not None:
                ordered_query = ordered_query.filter(statement.whereclause)
            ordered_query = ordered_query.order_by(Pledge.created_at.desc())
        result = paginate(ordered_query, page=page, per_page=per_page)
        if isinstance(result, dict):
            return {
                "items": result.get("items", []),
                "page": result.get("page", page),
                "per_page": result.get("per_page", per_page),
                "total": result.get("total", 0),
                "pages": result.get("pages", 0),
            }
        return {
            "items": result.items,
            "page": result.page,
            "per_page": result.per_page,
            "total": result.total,
            "pages": result.pages,
        }

    pagination = db.paginate(
        ordered_query,
        page=page,
        per_page=per_page,
        error_out=False,
    )
    return {
        "items": pagination.items,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
    }


def _pagination_data(pagination):
    return {
        "page": pagination["page"],
        "per_page": pagination["per_page"],
        "total": pagination["total"],
        "pages": pagination["pages"],
    }


@pledge_bp.get("/campaign/<int:campaign_id>")
def list_campaign_pledges(campaign_id):
    """Public campaign pledge list, with anonymous contributor identity hidden."""
    if Campaign is None:
        return _error("Campaign module not available yet", 503)
    if _get_campaign(campaign_id) is None:
        return _error("Campaign not found", 404)

    try:
        query_data = pledge_query_schema.load(request.args.to_dict())
    except ValidationError as error:
        return _error("Invalid query", 422, error.messages)

    query = db.select(Pledge).where(
        Pledge.campaign_id == campaign_id,
        Pledge.status.in_(("pending", "confirmed")),
    )
    if query_data.get("status"):
        if query_data["status"] == "cancelled":
            return _error("Cancelled pledges are not public", 422)
        query = query.where(Pledge.status == query_data["status"])

    pagination = _page(query, query_data["page"], query_data["per_page"])
    return jsonify(
        {
            "campaign_id": campaign_id,
            "raised_amount": _raised_for(campaign_id),
            "count": pagination["total"],
            **_pagination_data(pagination),
            "pledges": [pledge.to_dict() for pledge in pagination["items"]],
        }
    ), 200


@pledge_bp.post("/campaign/<int:campaign_id>")
@_require_user
def create_pledge(campaign_id):
    if Campaign is None:
        return _error("Campaign module not available yet", 503)
    campaign = _get_campaign(campaign_id)
    if campaign is None:
        return _error("Campaign not found", 404)
    if campaign.status != "open":
        return _error("Campaign is closed", 409)
    if g.user.role != "contributor":
        return _error("Only contributors can create pledges", 403)

    try:
        data = pledge_create_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return _error("Invalid payload", 422, error.messages)

    pledge = Pledge(
        campaign_id=campaign_id,
        contributor_id=g.user.id,
        amount=data["amount"],
        message=data.get("message"),
        is_anonymous=data["is_anonymous"],
    )
    db.session.add(pledge)
    db.session.commit()
    return jsonify({"pledge": pledge.to_dict(viewer=g.user)}), 201


@pledge_bp.get("/mine")
@_require_user
def my_pledges():
    try:
        query_data = pledge_query_schema.load(request.args.to_dict())
    except ValidationError as error:
        return _error("Invalid query", 422, error.messages)

    query = db.select(Pledge).where(Pledge.contributor_id == g.user.id)
    if query_data.get("status"):
        query = query.where(Pledge.status == query_data["status"])
    pagination = _page(query, query_data["page"], query_data["per_page"])
    return jsonify(
        {
            "count": pagination["total"],
            **_pagination_data(pagination),
            "pledges": [
                pledge.to_dict(viewer=g.user) for pledge in pagination["items"]
            ],
        }
    ), 200


@pledge_bp.get("/<int:pledge_id>")
@_require_user
def get_pledge(pledge_id):
    pledge = db.session.get(Pledge, pledge_id)
    if pledge is None:
        return _error("Pledge not found", 404)
    if not _can_view(pledge, g.user):
        return _error("Forbidden", 403)
    return jsonify({"pledge": pledge.to_dict(viewer=g.user)}), 200


@pledge_bp.patch("/<int:pledge_id>")
@_require_user
def update_pledge(pledge_id):
    pledge = db.session.get(Pledge, pledge_id)
    if pledge is None:
        return _error("Pledge not found", 404)
    if pledge.contributor_id != g.user.id:
        return _error("Forbidden", 403)
    if pledge.status != "pending":
        return _error("Only pending pledges can be edited", 409)

    try:
        data = pledge_update_schema.load(request.get_json(silent=True) or {})
    except ValidationError as error:
        return _error("Invalid payload", 422, error.messages)

    for field in ("amount", "message"):
        if field in data:
            setattr(pledge, field, data[field])
    db.session.commit()
    return jsonify({"pledge": pledge.to_dict(viewer=g.user)}), 200


@pledge_bp.delete("/<int:pledge_id>")
@_require_user
def cancel_pledge(pledge_id):
    pledge = db.session.get(Pledge, pledge_id)
    if pledge is None:
        return _error("Pledge not found", 404)
    if pledge.contributor_id != g.user.id and g.user.role != "admin":
        return _error("Forbidden", 403)
    if pledge.status != "pending":
        return _error("Only pending pledges can be cancelled", 409)

    pledge.status = "cancelled"
    db.session.commit()
    return jsonify({"pledge": pledge.to_dict(viewer=g.user)}), 200


@pledge_bp.post("/<int:pledge_id>/confirm")
@_require_user
def confirm_pledge(pledge_id):
    pledge = db.session.get(Pledge, pledge_id)
    if pledge is None:
        return _error("Pledge not found", 404)
    if Campaign is None:
        return _error("Campaign module not available yet", 503)

    campaign = getattr(pledge, "campaign", None)
    is_organizer = (
        campaign is not None and campaign.organizer_id == g.user.id
    )
    if not (is_organizer or g.user.role == "admin"):
        return _error("Forbidden", 403)
    if pledge.status != "pending":
        return _error("Only pending pledges can be confirmed", 409)

    pledge.status = "confirmed"
    pledge.confirmed_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(
        {
            "pledge": pledge.to_dict(viewer=g.user),
            "campaign_id": pledge.campaign_id,
            "raised_amount": _raised_for(pledge.campaign_id),
        }
    ), 200


@pledge_bp.get("/campaign/<int:campaign_id>/manage")
@_require_user
def organizer_manage_view(campaign_id):
    if Campaign is None:
        return _error("Campaign module not available yet", 503)
    campaign = _get_campaign(campaign_id)
    if campaign is None:
        return _error("Campaign not found", 404)
    if campaign.organizer_id != g.user.id and g.user.role != "admin":
        return _error("Forbidden", 403)

    try:
        query_data = pledge_query_schema.load(request.args.to_dict())
    except ValidationError as error:
        return _error("Invalid query", 422, error.messages)

    query = db.select(Pledge).where(Pledge.campaign_id == campaign_id)
    if query_data.get("status"):
        query = query.where(Pledge.status == query_data["status"])
    pagination = _page(query, query_data["page"], query_data["per_page"])
    return jsonify(
        {
            "campaign_id": campaign_id,
            "raised_amount": _raised_for(campaign_id),
            "counts": _status_counts(campaign_id),
            **_pagination_data(pagination),
            "pledges": [
                pledge.to_dict(viewer=g.user) for pledge in pagination["items"]
            ],
        }
    ), 200


@pledge_bp.post("/<int:pledge_id>/remind")
@_require_user
def remind_pledge(pledge_id):
    if send_email is None:
        return _error("Email service not available yet", 503)
    if Campaign is None:
        return _error("Campaign module not available yet", 503)
    pledge = db.session.get(Pledge, pledge_id)
    if pledge is None:
        return _error("Pledge not found", 404)
    campaign = getattr(pledge, "campaign", None)
    if campaign is None or campaign.organizer_id != g.user.id:
        return _error("Forbidden", 403)
    if pledge.contributor is None or not getattr(pledge.contributor, "email", None):
        return _error("Contributor email not available", 400)

    subject = "Pledge reminder"
    body = (
        f"Hi {getattr(pledge.contributor, 'name', None) or pledge.contributor.email}, "
        f"this is a reminder about your pledge of {float(pledge.amount)} "
        f"to '{campaign.title}'."
    )
    send_email(pledge.contributor.email, subject, body)
    return jsonify({"message": "Reminder queued"}), 200


def _can_view(pledge, user):
    campaign = getattr(pledge, "campaign", None)
    return (
        user.role == "admin"
        or pledge.contributor_id == user.id
        or (
            campaign is not None and campaign.organizer_id == user.id
        )
    )