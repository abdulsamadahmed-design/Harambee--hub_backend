from flask import Flask
from app.config import Config
from app.extensions import db, jwt, cors
from app.utils.errors import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)

    from app import models
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(auth_bp)
    register_error_handlers(app)

    with app.app_context():
        db.create_all()

    return app