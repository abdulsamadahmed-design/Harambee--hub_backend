import os

from flask import Flask, jsonify

from app.config import Config
from app.extensions import db, jwt, migrate


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    from app.models import Campaign, Pledge, User
    from app.routes.pledge_routes import pledge_bp

    app.register_blueprint(pledge_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @jwt.unauthorized_loader
    def unauthorized(_reason):
        return jsonify({"error": "Authorization token is required"}), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify({"error": "Invalid authorization token"}), 401

    @jwt.expired_token_loader
    def expired_token(_jwt_header, _jwt_payload):
        return jsonify({"error": "Authorization token has expired"}), 401

    return app