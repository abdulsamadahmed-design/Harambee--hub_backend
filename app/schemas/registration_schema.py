
from marshmallow import Schema, fields, validate, pre_load


class RegistrationSchema(Schema):
    name = fields.String(
        required=True,
        validate=[
            validate.Length(min=1, max=100),
            validate.Regexp(r".*\S.*", error="Name cannot be empty.")
        ]
    )

    email = fields.Email(
        required=True,
        validate=validate.Length(max=120)
    )

    password = fields.String(
        required=True,
        load_only=True,
        validate=validate.Length(min=8)
    )

    phone = fields.String(
        required=False,
        allow_none=True,
        validate=validate.Length(max=20)
    )

    role = fields.String(
        required=True,
        validate=validate.OneOf(["organizer", "contributor"])
    )

class ResendVerificationSchema(Schema):
    email = fields.Email(
        required=True,
        validate=validate.Length(max=120)
    )

    @pre_load
    def normalize_email(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("email"), str):
            data = {**data, "email": data["email"].strip().lower()}
        return data
