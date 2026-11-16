import os

import click
from sqlalchemy import func, text

from app.extensions import db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.pledge import Pledge
from app.schemas.registration_schema import RegistrationSchema
from app.routes.registration_routes import generate_verification_token
from app.utils.email import send_verification_email


registration_schema = RegistrationSchema()



def show_dashboard(user=None):
    """Display platform-wide or organizer-specific statistics."""

    if user is None:
        users = db.session.query(func.count(User.id)).scalar()
        campaigns = db.session.query(func.count(Campaign.id)).scalar()
        pledges = db.session.query(func.count(Pledge.id)).scalar()

        confirmed = db.session.query(
            func.coalesce(func.sum(Pledge.amount), 0)
        ).filter(Pledge.status == "confirmed").scalar()

        click.echo("\n========== PLATFORM STATISTICS ==========")
        click.echo("Total users:       {}".format(users))
        click.echo("Total campaigns:   {}".format(campaigns))
        click.echo("Total pledges:     {}".format(pledges))
        click.echo("Confirmed amount:  {}".format(confirmed))
        click.echo("=========================================\n")

    else:
        campaigns = Campaign.query.filter_by(
            organizer_id=user.id
        ).count()

        pledges = db.session.query(
            func.count(Pledge.id)
        ).join(
            Campaign, Pledge.campaign_id == Campaign.id
        ).filter(
            Campaign.organizer_id == user.id
        ).scalar()

        confirmed = db.session.query(
            func.coalesce(func.sum(Pledge.amount), 0)
        ).join(
            Campaign, Pledge.campaign_id == Campaign.id
        ).filter(
            Campaign.organizer_id == user.id,
            Pledge.status == "confirmed"
        ).scalar()

        click.echo("\n========== MY STATISTICS ==========")
        click.echo("My campaigns:               {}".format(campaigns))
        click.echo("My pledges:                 {}".format(pledges))
        click.echo("Confirmed amount:           {}".format(confirmed))
        click.echo("===================================\n")


def list_users():
    """Display users without exposing password hashes."""
    users = User.query.order_by(User.id.asc()).limit(20).all()

    click.echo("\n========== USERS (MAX 20) ==========")

    if not users:
        click.echo("No users found.")
    else:
        for user in users:
            click.echo(
                "ID: {} | Name: {} | Email: {} | Role: {} | Verified: {}".format(
                    user.id,
                    user.name,
                    user.email,
                    user.role or "unassigned",
                    user.email_verified,
                )
            )

    click.echo("===================================\n")


def list_campaigns():
    """Display campaigns."""
    campaigns = Campaign.query.order_by(Campaign.id.asc()).limit(20).all()

    click.echo("\n========== CAMPAIGNS (MAX 20) ==========")

    if not campaigns:
        click.echo("No campaigns found.")
    else:
        for campaign in campaigns:
            click.echo(
                "ID: {} | Title: {} | Goal: {} | Status: {} | Organizer: {}".format(
                    campaign.id,
                    campaign.title,
                    campaign.goal_amount,
                    campaign.status,
                    campaign.organizer_id,
                )
            )

    click.echo("=======================================\n")


def list_pledges():
    """Display pledges while respecting anonymous contributions."""
    pledges = Pledge.query.order_by(Pledge.id.asc()).limit(20).all()

    click.echo("\n========== PLEDGES (MAX 20) ==========")

    if not pledges:
        click.echo("No pledges found.")
    else:
        for pledge in pledges:
            contributor = (
                "Anonymous"
                if pledge.is_anonymous
                else str(pledge.contributor_id or "Guest")
            )

            click.echo(
                "ID: {} | Campaign: {} | Amount: {} | Status: {} | Contributor: {}".format(
                    pledge.id,
                    pledge.campaign_id,
                    pledge.amount,
                    pledge.status,
                    contributor,
                )
            )

    click.echo("=====================================\n")


def check_database():
    """Check whether the database is reachable."""
    try:
        db.session.execute(text("SELECT 1"))
        click.echo("\nDatabase connection: OK\n")
    except Exception:
        db.session.rollback()
        click.echo("\nDatabase connection: FAILED")
        click.echo(
            "Unable to connect to the database. "
            "Check the application logs."
        )
        

def signup():
    """Register an organizer or contributor."""
    click.echo("\n========== CREATE ACCOUNT ==========")

    data = {
        "name": click.prompt("Full name").strip(),
        "email": click.prompt("Email").strip().lower(),
        "password": click.prompt(
            "Password", hide_input=True, confirmation_prompt=True
        ),
        "phone": click.prompt("Phone (optional)", default="", show_default=False),
        "role": click.prompt(
            "Account type",
            type=click.Choice(["organizer", "contributor"], case_sensitive=False),
        ).lower(),
    }

    if not data["phone"]:
        data.pop("phone")

    try:
        validated = registration_schema.load(data)
    except Exception as error:
        click.echo("\nPlease fix these problems:")

        messages = getattr(error, "messages", {})

        if isinstance(messages, dict):
            for field, errors in messages.items():
                if not isinstance(errors, list):
                    errors = [str(errors)]

                click.echo("{}: {}".format(field, ", ".join(errors)))
        else:
            click.echo("Invalid registration details.")

        return

    existing_user = User.query.filter_by(
        email=validated["email"].strip().lower()
    ).first()

    if existing_user:
        click.echo("\nAn account with this email already exists.")
        return


    user = User(
        name=validated["name"].strip(),
        email=validated["email"].strip().lower(),
        phone=validated.get("phone"),
        role=validated["role"],
    )
    user.set_password(validated["password"])

    try:
        db.session.add(user)
        db.session.commit()

        token = generate_verification_token(user.email)
        backend_url = os.getenv(
            "BACKEND_URL",
            "http://localhost:5000"
        ).rstrip("/")

        verification_url = (
            f"{backend_url}/api/auth/verify-email/{token}"
        )

        email_sent = send_verification_email(
            user.email,
            verification_url,
        )

        click.echo("\nAccount created successfully.")

        if email_sent:
            click.echo("A verification email has been sent to {}.".format(user.email))
        else:
            click.echo("Verification email could not be sent.")
            click.echo("Check your SendGrid configuration.")

        click.echo("You must verify your email before logging in.")

    except Exception:
        db.session.rollback()
        click.echo("\nCould not create account. Please try again.")
        click.echo("Check the application logs for details.")



def login():
    """Authenticate a user with a maximum of three attempts."""
    click.echo("\n========== LOGIN ==========")

    max_attempts = 3

    for attempt in range(max_attempts):
        email = click.prompt("Email").strip().lower()
        password = click.prompt("Password", hide_input=True)

        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            click.echo("\nInvalid email or password.")

            attempts_left = max_attempts - attempt - 1

            if attempts_left == 0:
                click.echo("Too many failed attempts. Please try again later.")
                return None

            click.echo("{} attempt(s) left.".format(attempts_left))
            continue

        if not user.email_verified:
            click.echo("\nPlease verify your email before logging in.")
            return None

        click.echo("\nWelcome, {}!".format(user.name))
        click.echo("Role: {}".format(user.role))

        return user

    return None



def admin_menu(user):
    """Show administrator options."""
    while True:
        click.echo("\n========== ADMIN DASHBOARD ==========")
        click.echo("1. Dashboard statistics")
        click.echo("2. List users")
        click.echo("3. List campaigns")
        click.echo("4. List pledges")
        click.echo("5. Check database connection")
        click.echo("6. Logout")

        choice = click.prompt(
            "Select an option",
            type=click.Choice(["1", "2", "3", "4", "5", "6"]),
        )

        if choice == "1":
            show_dashboard()
        elif choice == "2":
            list_users()
        elif choice == "3":
            list_campaigns()
        elif choice == "4":
            list_pledges()
        elif choice == "5":
            check_database()
        elif choice == "6":
            click.echo("\nLogged out.")
            break


def organizer_menu(user):
    """Show organizer options."""
    while True:
        click.echo("\n========== ORGANIZER DASHBOARD ==========")
        click.echo("1. View dashboard statistics")
        click.echo("2. View campaigns")
        click.echo("3. Logout")

        choice = click.prompt(
            "Select an option",
            type=click.Choice(["1", "2", "3"]),
        )

        if choice == "1":
            show_dashboard(user)
        elif choice == "2":
            campaigns = Campaign.query.filter_by(
                organizer_id=user.id
            ).order_by(Campaign.id.asc()).all()

            click.echo("\n========== MY CAMPAIGNS ==========")

            if not campaigns:
                click.echo("You have not created any campaigns.")
            else:
                for campaign in campaigns:
                    click.echo(
                        "ID: {} | Title: {} | Goal: {} | Status: {}".format(
                            campaign.id,
                            campaign.title,
                            campaign.goal_amount,
                            campaign.status,
                        )
                    )

        elif choice == "3":
            click.echo("\nLogged out.")
            break


def contributor_menu(user):
    """Show contributor options."""
    while True:
        click.echo("\n========== CONTRIBUTOR DASHBOARD ==========")
        click.echo("1. View campaigns")
        click.echo("2. View my pledges")
        click.echo("3. Logout")

        choice = click.prompt(
            "Select an option",
            type=click.Choice(["1", "2", "3"]),
        )

        if choice == "1":
            list_campaigns()

        elif choice == "2":
            pledges = Pledge.query.filter_by(
                contributor_id=user.id
            ).order_by(Pledge.id.asc()).all()

            click.echo("\n========== MY PLEDGES ==========")

            if not pledges:
                click.echo("You have not made any pledges.")
            else:
                for pledge in pledges:
                    click.echo(
                        "ID: {} | Campaign: {} | Amount: {} | Status: {}".format(
                            pledge.id,
                            pledge.campaign_id,
                            pledge.amount,
                            pledge.status,
                        )
                    )

        elif choice == "3":
            click.echo("\nLogged out.")
            break


@click.command("hub")
def hub_cli():
    """Open the interactive Harambee Hub CLI."""
    click.echo("\n====================================")
    click.echo("          HARAMBEE HUB CLI")
    click.echo("====================================")

    while True:
        click.echo("\n1. Sign up")
        click.echo("2. Login")
        click.echo("3. Exit")

        choice = click.prompt(
            "Select an option",
            type=click.Choice(["1", "2", "3"]),
        )

        if choice == "1":
            signup()

        elif choice == "2":
            user = login()

            if user is None:
                continue

            if user.role == "admin":
                admin_menu(user)
            elif user.role == "organizer":
                organizer_menu(user)
            elif user.role == "contributor":
                contributor_menu(user)
            else:
                click.echo("\nYour account has an unsupported role.")

        elif choice == "3":
            click.echo("\nExiting Harambee Hub CLI.")
            break


def register_cli(app):
    """Register custom CLI commands with Flask."""
    app.cli.add_command(hub_cli)
