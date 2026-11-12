from flask import jsonify
from app.extensions import jwt


def error_response(message, status=400):
    return jsonify({"error": message}), status


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return error_response("Not found", 404)

    @app.errorhandler(500)
    def server_error(error):
        return error_response("Something went wrong on the server", 500)

    @jwt.unauthorized_loader
    def missing_token(reason):
        return error_response("Please log in first", 401)