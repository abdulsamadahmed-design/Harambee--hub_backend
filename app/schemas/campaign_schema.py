
from marshmallow import Schema, fields, validate, validates_schema, ValidationError


class CampaignSchema(Schema):
    id = fields.Int(dump_only=True)

    title = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=150)
    )

    description = fields.Str(
        required=True,
        validate=validate.Length(min=10)
    )

    goal_amount = fields.Decimal(
        required=True,
        as_string=True,
        places=2,
        validate=validate.Range(min=0.01)
    )

    image_url = fields.Str(allow_none=True)

    status = fields.Str(dump_only=True)

    end_date = fields.DateTime(allow_none=True)

    created_at = fields.DateTime(dump_only=True)

    organizer_id = fields.Int(dump_only=True)
