
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
    from app.routes.sendgrid_webhook_routes import sendgrid_webhook_bp

    from app.routes.docs_routes import docs_bp, swaggerui_blueprint


    app.register_blueprint(auth_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(registration_bp)
    app.register_blueprint(pledge_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(campaign_bp)
    app.register_blueprint(sendgrid_webhook_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(swaggerui_blueprint)

    @app.cli.command("seed-organizer")
    def seed_organizer():
        """Create the initial organizer account."""
        email = os.environ.get("ORGANIZER_EMAIL", "").strip().lower()
        password = os.environ.get("ORGANIZER_PASSWORD")

        if not email or not password:
            raise click.ClickException(
                "ORGANIZER_EMAIL and ORGANIZER_PASSWORD must both be set."
            )

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            if existing_user.role == "organizer":
                click.echo("Organizer already exists. No changes made.")
                return

            raise click.ClickException(
                "A user with this email already exists and is not an organizer."
            )

        organizer = User(
            name=email.split("@", 1)[0],
            email=email,
            role="organizer",
            email_verified=True,
        )
        organizer.set_password(password)

        db.session.add(organizer)
        db.session.commit()

        click.echo("Organizer account created successfully.")

    @app.cli.command("reset-organizer-password")
    def reset_organizer_password():
        """Reset an existing organizer's password."""
        email = click.prompt("Organizer email").strip().lower()

        organizer = User.query.filter_by(
            email=email,
            role="organizer"
        ).first()

        if not organizer:
            raise click.ClickException("Organizer account not found.")

        password = click.prompt(
            "New organizer password",
            hide_input=True,
            confirmation_prompt=True
        )

        if len(password) < 8:
            raise click.ClickException(
                "Password must contain at least 8 characters."
            )

        organizer.set_password(password)
        db.session.commit()

        click.echo("Organizer password updated successfully.")

    from app.cli import register_cli
    register_cli(app)

    register_error_handlers(app)

    return app
