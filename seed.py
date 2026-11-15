from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.campaign import Campaign
from app.models.pledge import Pledge


DEMO_PASSWORD = "DemoPass123!"


def get_or_create_user(name, email, role):
    user = User.query.filter_by(email=email).first()

    if user:
        if user.role != role:
            raise ValueError(
                f"{email} already exists with role '{user.role}', "
                f"expected '{role}'. No changes made to that user."
            )
        return user

    user = User(
        name=name,
        email=email,
        role=role,
        email_verified=True,
    )
    user.set_password(DEMO_PASSWORD)
    db.session.add(user)
    db.session.flush()

    return user


def get_or_create_campaign(title, description, goal_amount, organizer):
    campaign = Campaign.query.filter_by(title=title).first()

    if campaign:
        return campaign

    campaign = Campaign(
        title=title,
        description=description,
        goal_amount=Decimal(goal_amount),
        status="active",
        end_date=datetime.now(timezone.utc) + timedelta(days=60),
        organizer_id=organizer.id,
    )
    db.session.add(campaign)
    db.session.flush()

    return campaign


def get_or_create_pledge(campaign, contributor, amount, message, status):
    pledge = Pledge.query.filter_by(
        campaign_id=campaign.id,
        contributor_id=contributor.id,
        message=message,
    ).first()

    if pledge:
        return pledge

    pledge = Pledge(
        campaign_id=campaign.id,
        contributor_id=contributor.id,
        amount=Decimal(amount),
        message=message,
        is_anonymous=False,
        status=status,
        confirmed_at=(
            datetime.now(timezone.utc) if status == "confirmed" else None
        ),
    )
    db.session.add(pledge)

    return pledge


def seed_data():
    organizer = get_or_create_user(
        "Demo Organizer",
        "organizer@example.com",
        "organizer",
    )

    contributor_one = get_or_create_user(
        "Amina Contributor",
        "amina@example.com",
        "contributor",
    )

    contributor_two = get_or_create_user(
        "Brian Contributor",
        "brian@example.com",
        "contributor",
    )

    library_campaign = get_or_create_campaign(
        "Community Library Project",
        "Help build a community library and provide learning materials "
        "for children.",
        "150000.00",
        organizer,
    )

    school_campaign = get_or_create_campaign(
        "School Fees Support",
        "Help vulnerable students access education by supporting their "
        "school fees.",
        "100000.00",
        organizer,
    )

    get_or_create_pledge(
        library_campaign,
        contributor_one,
        "2000.00",
        "Supporting community education.",
        "confirmed",
    )

    get_or_create_pledge(
        library_campaign,
        contributor_two,
        "1000.00",
        "A contribution towards the library.",
        "pending",
    )

    get_or_create_pledge(
        school_campaign,
        contributor_one,
        "1500.00",
        "Helping students stay in school.",
        "confirmed",
    )

    db.session.commit()

    print("Sample data created or already exists.")
    print("Demo login accounts:")
    print("organizer@example.com")
    print("amina@example.com")
    print("brian@example.com")
    print(f"Password for newly created accounts: {DEMO_PASSWORD}")


if __name__ == "__main__":
    app = create_app()

    with app.app_context():
        try:
            seed_data()
        except Exception:
            db.session.rollback()
            raise
