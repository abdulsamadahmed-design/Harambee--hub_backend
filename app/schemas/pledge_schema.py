from marshmallow import Schema, ValidationError, fields, validate, validates_schema


class PledgeCreateSchema(Schema):
    amount = fields.Decimal(
        as_string=False,
        places=2,
        required=True,
        validate=validate.Range(min=1, max=10_000_000),
    )
    message = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=500),
    )
    is_anonymous = fields.Boolean(load_default=False)


class PledgeUpdateSchema(Schema):
    amount = fields.Decimal(
        as_string=False,
        places=2,
        validate=validate.Range(min=1, max=10_000_000),
    )
    message = fields.String(allow_none=True, validate=validate.Length(max=500))

    @validates_schema
    def require_update_field(self, data, **kwargs):
        if not data:
            raise ValidationError("At least one field must be provided.")


class PledgeQuerySchema(Schema):
    status = fields.String(
        allow_none=True,
        validate=validate.OneOf(["pending", "confirmed", "cancelled"]),
        load_default=None,
    )
    mine = fields.Boolean(load_default=False)
    page = fields.Integer(load_default=1, validate=validate.Range(min=1))
    per_page = fields.Integer(
        load_default=10,
        validate=validate.Range(min=1, max=100),
    )


pledge_create_schema = PledgeCreateSchema()
pledge_update_schema = PledgeUpdateSchema()
pledge_query_schema = PledgeQuerySchema()
