from marshmallow import EXCLUDE, Schema, fields, pre_load, validate


class LoginSchema(Schema):
    """Validates the JSON body of POST /api/auth/login.

    Usage in the route:

        from marshmallow import ValidationError
        from app.schemas.auth_schema import LoginSchema

        try:
            data = LoginSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return jsonify({"error": "Validation failed", "details": err.messages}), 422

    Login does NOT enforce a minimum password length on purpose. A rule like
    "at least 8 characters" would tell someone guessing passwords which guesses
    are not worth trying, and the stored hash is what really decides.
    """

    class Meta:
        # Ignore extra fields (for example "remember_me") instead of failing.
        unknown = EXCLUDE

    email = fields.Email(
        required=True,
        error_messages={
            "required": "Email is required.",
            "null": "Email is required.",
            "invalid": "Enter a valid email address.",
        },
    )
    password = fields.Str(
        required=True,
        validate=validate.Length(min=1, error="Password is required."),
        error_messages={
            "required": "Password is required.",
            "null": "Password is required.",
            "invalid": "Password must be text.",
        },
    )

    @pre_load
    def clean_email(self, data, **kwargs):
        """Trim spaces and lowercase the email before it is validated.

        The password is never touched: spaces in a password are meaningful.
        Anything that is not a dict is returned unchanged so Marshmallow can
        report its own "Invalid input type." error.
        """
        if isinstance(data, dict) and isinstance(data.get("email"), str):
            data = {**data, "email": data["email"].strip().lower()}
        return data
