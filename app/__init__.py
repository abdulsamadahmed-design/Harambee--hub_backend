import os
import click

from flask import Flask
from app.config import Config
from app.extensions import db, jwt, cors, migrate
from app.utils.errors import register_error_handlers


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Ensure required secrets are configured
    for secret_name in ("SECRET_KEY", "JWT_SECRET_KEY"):
        if not app.config.get(secret_name):
            raise RuntimeError(f"{secret_name} must be configured.")

    # Configure CORS for the frontend
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": frontend_url.split(",")
            }
        }
    )
    migrate.init_app(app, db)

    from app import models
    from app.models.user import User
    from app.routes.auth_routes import auth_bp
    from app.routes.registration_routes import registration_bp
    from app.routes.pledge_routes import pledge_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.campaign_routes import campaign_bp
    from app.routes.health_routes import health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(registration_bp)
    app.register_blueprint(pledge_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(campaign_bp)

    @app.cli.command("seed-admin")
    def seed_admin():
        """Create the initial administrator account."""
        email = os.environ.get("ADMIN_EMAIL", "").strip()
        password = os.environ.get("ADMIN_PASSWORD")

        if not email or not password:
            raise click.ClickException(
                "ADMIN_EMAIL and ADMIN_PASSWORD must both be set."
            )

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            if existing_user.role == "admin":
                click.echo("Admin already exists. No changes made.")
                return

            raise click.ClickException(
                "A user with this email already exists and is not an admin."
            )

        admin = User(
            name=email.split("@", 1)[0],
            email=email,
            role="admin",
            email_verified=True,
        )
        admin.set_password(password)

        db.session.add(admin)
        db.session.commit()

        click.echo("Admin account created successfully.")

    from app.cli import register_cli
    register_cli(app)

    register_error_handlers(app)

    return app
