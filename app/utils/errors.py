from flask import jsonify
from app.extensions import jwt


def error_response(message, status=400):
    return jsonify({"error": message}), status


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return error_response("Not found", 404)

    @app.errorhandler(413)
    def request_too_large(error):
        return error_response("Request is too large. Maximum size is 6 MB.", 413)

    @app.errorhandler(500)
    def server_error(error):
        return error_response(
            "Something went wrong on the server",
            500
        )

    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response("Please log in first", 401)

    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return error_response("Your access token has expired", 401)

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return error_response("Invalid access token", 401)
