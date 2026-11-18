import os
from datetime import datetime, timezone
from decimal import Decimal

import click
from flask import current_app
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
    """Display platform-wide statistics."""
    campaigns = db.session.query(func.count(Campaign.id)).scalar()
    pledges = db.session.query(func.count(Pledge.id)).scalar()

    confirmed = db.session.query(
        func.coalesce(func.sum(Pledge.amount), 0)
    ).filter(Pledge.status == "confirmed").scalar()

    click.echo("\n========== HARAMBEE HUB DASHBOARD ==========")
    click.echo("Total campaigns:   {}".format(campaigns))
    click.echo("Total pledges:     {}".format(pledges))
    click.echo("Confirmed amount:  {}".format(confirmed))
    click.echo("============================================\n")


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
    """Display all ongoing campaigns across the platform."""
    campaigns = Campaign.query.filter_by(
        status="active"
    ).order_by(Campaign.id.asc()).all()

    click.echo("\n========== ALL ONGOING CAMPAIGNS ==========")

    if not campaigns:
        click.echo("There are currently no ongoing campaigns.")
        return

    for campaign in campaigns:
        organizer_name = (
            campaign.organizer.name if campaign.organizer else "Unknown"
        )

        click.echo(
            "ID: {} | Title: {} | Organizer: {} | Goal: {} | Status: {}".format(
                campaign.id,
                campaign.title,
                organizer_name,
                campaign.goal_amount,
                campaign.status,
            )
        )

    click.echo("Total ongoing campaigns: {}".format(len(campaigns)))
    click.echo("===========================================\n")


def list_pledges():
    """Display pledges with contributor names."""
    pledges = Pledge.query.order_by(Pledge.id.asc()).limit(20).all()

    click.echo("\n========== PLEDGES (MAX 20) ==========")

    if not pledges:
        click.echo("No pledges found.")
    else:
        for pledge in pledges:
            contributor = (
                pledge.contributor_name
                or (pledge.contributor.name if pledge.contributor else "Unassigned")
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
        "role": None,
    }

    while data["role"] is None:
        role_choice = click.prompt(
            "Account type (1 = Organizer, 2 = Contributor)"
        ).strip().lower()

        role_choices = {
            "1": "organizer",
            "organizer": "organizer",
            "2": "contributor",
            "contributor": "contributor",
        }

        data["role"] = role_choices.get(role_choice)

        if data["role"] is None:
            click.echo("Please enter 1, 2, organizer, or contributor.")

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
            click.echo("Please verify your email before logging in.")
        elif current_app.config.get("HARAMBEE_ENV") == "development":
            user.email_verified = True
            db.session.commit()
            click.echo("You can now log in.")
        else:
            click.echo("Please verify your email before logging in.")

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
            click.echo("\nWrong email or password.")

            attempts_left = max_attempts - attempt - 1

            if attempts_left == 0:
                click.echo("Too many failed attempts. Please try again later.")
                return None

            click.echo("{} attempt(s) left.".format(attempts_left))
            continue

        if not user.email_verified:
            click.echo("\nPlease verify your email before logging in.")
            return None

        click.echo("\nLogged in successfully.")

        return user

    return None



def organizer_menu(user):
    while True:
        click.echo("\n========== ORGANIZER DASHBOARD ==========")
        click.echo("1. View dashboard statistics")
        click.echo("2. View all campaigns")
        click.echo("3. Create a campaign")
        click.echo("4. Update any campaign")
        click.echo("5. Delete any campaign")
        click.echo("6. View campaign pledges")
        click.echo("7. Cancel a pending pledge")
        click.echo("8. Confirm a pending pledge")
        click.echo("9. Logout")

        choice = click.prompt("Select an option").strip()
        if choice not in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            click.echo("Wrong number. Try again.")
            continue

        if choice == "1":
            show_dashboard(user)
        elif choice == "2":
            show_organizer_campaigns(user)
        elif choice == "3":
            create_organizer_campaign(user)
        elif choice == "4":
            update_organizer_campaign(user)
        elif choice == "5":
            delete_organizer_campaign(user)
        elif choice == "6":
            show_organizer_pledges(user)
        elif choice == "7":
            cancel_organizer_pledge(user)
        elif choice == "8":
            confirm_organizer_pledge(user)
        elif choice == "9":
            click.echo("\nLogged out.")
            break


def get_organizer_campaign(user, campaign_id):
    return Campaign.query.filter_by(id=campaign_id).first()


def show_organizer_campaigns(user):
    campaigns = Campaign.query.order_by(Campaign.id.asc()).all()

    click.echo("\n========== ALL CAMPAIGNS ==========")
    if not campaigns:
        click.echo("No campaigns found.")
    for campaign in campaigns:
        click.echo(
            "ID: {} | Title: {} | Goal: {} | Status: {}".format(
                campaign.id, campaign.title,
                campaign.goal_amount, campaign.status
            )
        )
    return campaigns


def create_organizer_campaign(user):
    click.echo("\n========== CREATE CAMPAIGN ==========")
    title = click.prompt("Campaign title").strip()
    description = click.prompt("Description").strip()
    goal = click.prompt("Goal amount", type=float)

    if len(title) < 3 or len(title) > 150:
        click.echo("Title must be 3-150 characters.")
        return
    if len(description) < 10 or goal <= 0:
        click.echo("Description must be at least 10 characters and goal must be positive.")
        return

    try:
        campaign = Campaign(
            title=title,
            description=description,
            goal_amount=goal,
            organizer_id=user.id,
            status="active",
        )
        db.session.add(campaign)
        db.session.commit()
        click.echo("Campaign created. ID: {}".format(campaign.id))
    except Exception:
        db.session.rollback()
        click.echo("Could not create campaign. Check application logs.")


def update_organizer_campaign(user):
    show_organizer_campaigns(user)
    campaign_id = click.prompt("Campaign ID to update", type=int)
    campaign = get_organizer_campaign(user, campaign_id)

    if campaign is None:
        click.echo("Campaign not found.")
        return

    title = click.prompt("Title", default=campaign.title).strip()
    description = click.prompt("Description", default=campaign.description).strip()
    goal = click.prompt("Goal amount", default=float(campaign.goal_amount), type=float)

    if len(title) < 3 or len(title) > 150 or len(description) < 10 or goal <= 0:
        click.echo("Invalid campaign details.")
        return

    try:
        campaign.title = title
        campaign.description = description
        campaign.goal_amount = goal
        db.session.commit()
        click.echo("Campaign updated.")
    except Exception:
        db.session.rollback()
        click.echo("Could not update campaign. Check application logs.")


def delete_organizer_campaign(user):
    show_organizer_campaigns(user)
    campaign_id = click.prompt("Campaign ID to delete", type=int)
    campaign = get_organizer_campaign(user, campaign_id)

    if campaign is None:
        click.echo("Campaign not found.")
        return

    if Pledge.query.filter_by(campaign_id=campaign.id).first():
        click.echo("Cannot delete: this campaign has pledge history.")
        return

    if not click.confirm("Delete this campaign?", default=False):
        click.echo("Deletion cancelled.")
        return

    try:
        db.session.delete(campaign)
        db.session.commit()
        click.echo("Campaign deleted.")
    except Exception:
        db.session.rollback()
        click.echo("Could not delete campaign. Check application logs.")


def show_organizer_pledges(user):
    campaign_id = click.prompt("Campaign ID", type=int)
    campaign = get_organizer_campaign(user, campaign_id)

    if campaign is None:
        click.echo("Campaign not found.")
        return

    pledges = Pledge.query.filter_by(
        campaign_id=campaign.id
    ).order_by(Pledge.id.asc()).all()

    click.echo("\n========== CAMPAIGN PLEDGES ==========")
    if not pledges:
        click.echo("No pledges found.")
    for pledge in pledges:
        contributor = (
            pledge.contributor_name
            or (pledge.contributor.name if pledge.contributor else "Unassigned")
        )

        click.echo(
            "ID: {} | Amount: {} | Status: {} | Contributor: {}".format(
                pledge.id, pledge.amount, pledge.status, contributor
            )
        )


def cancel_organizer_pledge(user):
    campaign_id = click.prompt("Campaign ID", type=int)
    campaign = get_organizer_campaign(user, campaign_id)

    if campaign is None:
        click.echo("Campaign not found.")
        return

    pledges = Pledge.query.filter_by(
        campaign_id=campaign.id
    ).order_by(Pledge.id.asc()).all()

    if not pledges:
        click.echo("No pledges found.")
        return

    for pledge in pledges:
        click.echo(
            "ID: {} | Amount: {} | Status: {}".format(
                pledge.id, pledge.amount, pledge.status
            )
        )

    pledge_id = click.prompt("Pledge ID to cancel", type=int)
    pledge = Pledge.query.filter_by(
        id=pledge_id, campaign_id=campaign.id
    ).first()

    if pledge is None:
        click.echo("Pledge not found in this campaign.")
        return
    if pledge.status != "pending":
        click.echo("Only pending pledges can be cancelled.")
        return
    if not click.confirm("Cancel this pledge?", default=False):
        click.echo("Cancellation aborted.")
        return

    try:
        pledge.status = "cancelled"
        db.session.commit()
        click.echo("Pledge cancelled. History preserved.")
    except Exception:
        db.session.rollback()
        click.echo("Could not cancel pledge. Check application logs.")



def confirm_organizer_pledge(user):
    pledges = Pledge.query.filter_by(
        status="pending"
    ).order_by(Pledge.id.asc()).all()

    click.echo("\n========== PENDING PLEDGES ==========")

    if not pledges:
        click.echo("No pending pledges found.")
        return

    for pledge in pledges:
        campaign = pledge.campaign
        title = campaign.title if campaign else "Unknown campaign"

        contributor = (
            pledge.contributor_name
            or (pledge.contributor.name if pledge.contributor else "Unassigned")
        )

        click.echo(
            "ID: {} | Campaign: {} | Amount: {} | Contributor: {}".format(
                pledge.id, title, pledge.amount, contributor
            )
        )

    pledge_id = click.prompt("Pledge ID to confirm", type=int)
    pledge = db.session.get(Pledge, pledge_id)

    if pledge is None or pledge.status != "pending":
        click.echo("Pending pledge not found.")
        return

    if not click.confirm("Confirm this pledge?", default=False):
        click.echo("Confirmation cancelled.")
        return

    try:
        pledge.status = "confirmed"
        pledge.confirmed_at = datetime.now(timezone.utc)
        db.session.commit()
        click.echo("Pledge confirmed.")
    except Exception:
        db.session.rollback()
        click.echo("Could not confirm pledge. Check application logs.")

def create_contributor_pledge(user):
    """Allow a contributor to pledge to an active campaign."""
    campaigns = Campaign.query.filter_by(
        status="active"
    ).order_by(Campaign.id.asc()).all()

    click.echo("\n========== ACTIVE CAMPAIGNS ==========")

    if not campaigns:
        click.echo("There are no active campaigns available.")
        return

    for campaign in campaigns:
        click.echo(
            "ID: {} | {} | Goal: {}".format(
                campaign.id,
                campaign.title,
                campaign.goal_amount,
            )
        )

    campaign_id = click.prompt("Enter the campaign ID", type=int)

    campaign = Campaign.query.filter_by(
        id=campaign_id,
        status="active",
    ).first()

    if campaign is None:
        click.echo("Invalid campaign ID or campaign is not active.")
        return

    amount = click.prompt(
        "Pledge amount",
        type=click.FloatRange(min=1, max=10_000_000),
    )

    message = click.prompt(
        "Message (optional)",
        default="",
        show_default=False,
    ).strip()

    if len(message) > 500:
        click.echo("Message cannot exceed 500 characters.")
        return

    pledge = Pledge(
        campaign_id=campaign.id,
        contributor_id=user.id,
        amount=Decimal(str(amount)),
        message=message or None,
    )

    try:
        db.session.add(pledge)
        db.session.commit()
        click.echo("\nPledge created successfully.")
        click.echo("Pledge ID: {}".format(pledge.id))
        click.echo("Campaign: {}".format(campaign.title))
        click.echo("Amount: {}".format(pledge.amount))
        click.echo("Status: {}".format(pledge.status))
    except Exception:
        db.session.rollback()
        click.echo("Could not create the pledge. Please try again.")


def contributor_menu(user):
    """Show contributor options."""
    while True:
        click.echo("\n========== CONTRIBUTOR DASHBOARD ==========")
        click.echo("1. View campaigns")
        click.echo("2. Create a pledge")
        click.echo("3. View my pledges")
        click.echo("4. Logout")

        choice = click.prompt("Select an option").strip()
        if choice not in ["1", "2", "3", "4"]:
            click.echo("Wrong number. Try again.")
            continue

        if choice == "1":
            list_campaigns()

        elif choice == "2":
            create_contributor_pledge(user)

        elif choice == "3":
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

        elif choice == "4":
            click.echo("\nLogged out.")
            break

def admin_menu(user):
    """Show admin options."""
    while True:
        click.echo("\n========== ADMIN DASHBOARD ==========")
        click.echo("1. View dashboard statistics")
        click.echo("2. View all users")
        click.echo("3. View active campaigns")
        click.echo("4. View all pledges")
        click.echo("5. Check database connection")
        click.echo("6. Logout")

        choice = click.prompt("Select an option").strip()

        if choice == "1":
            show_dashboard(user)

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

        else:
            click.echo("Wrong number. Try again.")

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

        choice = click.prompt("Select an option").strip()
        if choice not in ["1", "2", "3"]:
            click.echo("Wrong number. Try again.")
            continue

        if choice == "1":
            signup()

        elif choice == "2":
            user = login()

            if user is None:
                continue

            if user.role == "organizer":
                organizer_menu(user)
            elif user.role == "contributor":
                contributor_menu(user)
            elif user.role == "admin":
                admin_menu(user)
            else:
                click.echo("\nYour account has an unsupported role.")

        elif choice == "3":
            click.echo("\nExiting Harambee Hub CLI.")
            break

@click.command("seed-admin")
def seed_admin_cli():
    """Create the initial admin account."""
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD")

    if not email or not password:
        raise click.ClickException(
            "ADMIN_EMAIL and ADMIN_PASSWORD must both be set."
        )

    if len(password) < 8:
        raise click.ClickException(
            "Admin password must contain at least 8 characters."
        )

    existing_user = User.query.filter_by(email=email).first()

    if existing_user:
        if existing_user.role == "admin":
            click.echo("Admin already exists. No changes made.")
            return

        raise click.ClickException(
            "A user with this email already exists with another role."
        )

    admin = User(
        name=email.split("@", 1)[0],
        email=email,
        role="admin",
        email_verified=True,
    )

    admin.set_password(password)

    try:
        db.session.add(admin)
        db.session.commit()
        click.echo("Admin account created successfully.")
    except Exception:
        db.session.rollback()
        raise click.ClickException(
            "Could not create admin account. Check application logs."
        )

def register_cli(app):
    """Register custom CLI commands with Flask."""
    app.cli.add_command(hub_cli)
    app.cli.add_command(seed_admin_cli)

