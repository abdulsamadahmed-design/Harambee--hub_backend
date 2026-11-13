
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from marshmallow import ValidationError
from cloudinary.exceptions import Error as CloudinaryError

from app.extensions import db
from app.models.campaign import Campaign
from app.schemas.campaign_schema import CampaignSchema
from app.utils.decorators import roles_required
from app.utils.errors import error_response
from app.utils.pagination import paginate_query
from app.utils.uploads import upload_image


campaign_bp = Blueprint(
    "campaign",
    __name__,
    url_prefix="/api/campaigns"
)

campaign_schema = CampaignSchema()


@campaign_bp.get("/")
def list_campaigns():
    """Return a paginated list of campaigns."""
    try:
        result = paginate_query(
            Campaign.query.order_by(Campaign.created_at.desc()),
            serializer=lambda campaign: campaign_schema.dump(campaign)
        )

        return jsonify(result), 200

    except ValueError as error:
        return error_response(str(error), 400)


@campaign_bp.get("/<int:campaign_id>")
def get_campaign(campaign_id):
    """Return details of a single campaign."""
    campaign = db.session.get(Campaign, campaign_id)

    if not campaign:
        return error_response("Campaign not found", 404)

    return jsonify(campaign_schema.dump(campaign)), 200


@campaign_bp.post("/")
@roles_required("organizer")
def create_campaign():
    """Create a campaign. Only organizers can create campaigns."""

    if request.files:
        data = request.form.to_dict()
    else:
        data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return error_response("Request body must be a JSON object", 400)

    try:
        campaign_data = campaign_schema.load(data)

        image_file = request.files.get("image")

        if image_file:
            if not image_file.filename:
                return error_response("No image selected", 400)

            campaign_data["image_url"] = upload_image(image_file)

        campaign = Campaign(
            **campaign_data,
            organizer_id=int(get_jwt_identity())
        )

        db.session.add(campaign)
        db.session.commit()

        return jsonify(campaign_schema.dump(campaign)), 201

    except ValidationError as error:
        return jsonify({"errors": error.messages}), 400

    except (CloudinaryError, RuntimeError) as error:
        db.session.rollback()
        print(f"Cloudinary upload error: {type(error).__name__}: {error}")
        return error_response("Image upload failed. Please try again.", 502)
