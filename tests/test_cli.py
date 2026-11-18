"""Tests for the interactive `flask hub` CLI.

The CLI reads its answers from `input=`, one line per prompt.

Menu numbers used below:
  main menu:         1 sign up, 2 login, 3 exit
  organizer menu:    1 stats, 2 campaigns, 6 campaign pledges, 10 logout
  contributor menu:  1 campaigns, 3 my pledges, 4 logout
"""
from datetime import datetime, timezone

import pytest

from app.extensions import db
from app.models.campaign import Campaign
from app.models.pledge import Pledge
from app.models.user import User


def run_cli(app, text):
    return app.test_cli_runner().invoke(args=["hub"], input=text)


def make_campaign(organizer, title="Wedding fund", goal=100000):
    """Create a campaign, filling only the fields this model really has."""
    candidate = {
        "title": title,
        "description": "Test campaign",
        "category": "wedding",
        "status": "open",
        "organizer_id": organizer.id,
        "deadline": datetime.now(timezone.utc),
        "goal_amount": goal,
        "target_amount": goal,
    }
    values = {key: value for key, value in candidate.items() if hasattr(Campaign, key)}
    campaign = Campaign(**values)
    db.session.add(campaign)
    db.session.commit()
    return campaign


def make_pledge(campaign, contributor, amount, status="confirmed"):
    pledge = Pledge(
        campaign_id=campaign.id,
        contributor_id=contributor.id,
        amount=amount,
        status=status,
    )
    db.session.add(pledge)
    db.session.commit()
    return pledge


# ---------- login ----------


def test_login_success_for_contributor(app, make_user):
    make_user(email="a@b.co", role="contributor")
    result = run_cli(app, "2\na@b.co\nsecret123\n4\n3\n")
    assert result.exit_code == 0
    assert "Logged in successfully." in result.output
    assert "CONTRIBUTOR DASHBOARD" in result.output


def test_login_email_is_case_and_space_insensitive(app, make_user):
    make_user(email="a@b.co", role="contributor")
    result = run_cli(app, "2\n  A@B.CO \nsecret123\n4\n3\n")
    assert "Logged in successfully." in result.output


def test_login_wrong_password_then_right_password(app, make_user):
    make_user(email="a@b.co", role="contributor")
    result = run_cli(app, "2\na@b.co\nbad\na@b.co\nsecret123\n4\n3\n")
    assert "2 attempt(s) left" in result.output
    assert "Logged in successfully." in result.output


def test_login_locks_out_after_three_failures(app, make_user):
    make_user(email="a@b.co", role="contributor")
    attempts = "a@b.co\nbad1\n" + "a@b.co\nbad2\n" + "a@b.co\nbad3\n"
    result = run_cli(app, "2\n" + attempts + "3\n")
    assert "Too many failed attempts" in result.output
    assert "Welcome" not in result.output


def test_login_unknown_email_gets_the_same_message_as_wrong_password(app, make_user):
    make_user(email="a@b.co", role="contributor")
    wrong_password = run_cli(app, "2\na@b.co\nbad\na@b.co\nbad\na@b.co\nbad\n3\n")
    unknown_email = run_cli(app, "2\nno@one.co\nbad\nno@one.co\nbad\nno@one.co\nbad\n3\n")
    assert "Wrong email or password." in wrong_password.output
    assert "Wrong email or password." in unknown_email.output
    assert "does not exist" not in unknown_email.output.lower()


def test_login_blocks_unverified_email(app, make_user):
    user = make_user(email="a@b.co", role="contributor")
    user.email_verified = False
    db.session.commit()
    result = run_cli(app, "2\na@b.co\nsecret123\n3\n")
    assert "verify your email" in result.output
    assert "Welcome" not in result.output


def test_unverified_status_is_not_revealed_for_a_wrong_password(app, make_user):
    user = make_user(email="a@b.co", role="contributor")
    user.email_verified = False
    db.session.commit()
    result = run_cli(app, "2\na@b.co\nbad\na@b.co\nbad\na@b.co\nbad\n3\n")
    assert "verify your email" not in result.output


# ---------- organizer and contributor permissions ----------


def test_organizer_sees_platform_wide_numbers(app, make_user):
    make_user(email="amina@x.co", role="organizer")
    brian = make_user(email="brian@x.co", role="organizer")
    donor = make_user(email="donor@x.co", role="contributor")

    make_pledge(make_campaign(brian, title="Amina wedding"), donor, 500)
    make_pledge(make_campaign(brian, title="Brian school fees"), donor, 900)

    result = run_cli(app, "2\namina@x.co\nsecret123\n1\n10\n3\n")

    assert "HARAMBEE HUB DASHBOARD" in result.output
    assert "Total campaigns:   2" in result.output
    assert "Total pledges:     2" in result.output
    assert "Confirmed amount:  1400" in result.output
    assert "Total users" not in result.output


def test_organizer_sees_all_campaigns(app, make_user):
    amina = make_user(email="amina@x.co", role="organizer")
    brian = make_user(email="brian@x.co", role="organizer")
    make_campaign(amina, title="Amina wedding")
    make_campaign(brian, title="Brian school fees")

    result = run_cli(app, "2\namina@x.co\nsecret123\n2\n10\n3\n")

    assert "Amina wedding" in result.output
    assert "Brian school fees" in result.output


def test_contributor_sees_only_their_own_pledges(app, make_user):
    amina = make_user(email="amina@x.co", role="organizer")
    mine = make_user(email="mine@x.co", role="contributor")
    other = make_user(email="other@x.co", role="contributor")
    campaign = make_campaign(amina)
    make_pledge(campaign, mine, 111)
    make_pledge(campaign, other, 222)

    result = run_cli(app, "2\nmine@x.co\nsecret123\n3\n4\n3\n")

    assert "Amount: 111" in result.output
    assert "Amount: 222" not in result.output


def test_organizer_pledge_list_shows_contributor_full_name(app, make_user):
    organizer = make_user(email="organizer@x.co", role="organizer")
    donor = make_user(
        email="donor@x.co", name="Full Contributor Name", role="contributor"
    )
    campaign = make_campaign(organizer)
    make_pledge(campaign, donor, 300)

    result = run_cli(
        app,
        "2\norganizer@x.co\nsecret123\n6\n{}\n10\n3\n".format(
            campaign.id
        ),
    )

    assert "Contributor: Full Contributor Name" in result.output
    assert "Anonymous" not in result.output


# ---------- sign up ----------


SIGNUP_OK = (
    "1\n"            # main menu: sign up
    "New Person\n"   # full name
    "new@example.com\n"
    "Strongpass1\n"  # password
    "Strongpass1\n"  # password confirmation
    "\n"             # phone (optional, left empty)
    "contributor\n"  # account type
    "3\n"            # main menu: exit
)


def test_signup_creates_an_unverified_account_and_sends_the_email(app, monkeypatch):
    sent = {}

    def fake_send(email, url):
        sent["email"] = email
        sent["url"] = url
        return True

    monkeypatch.setattr("app.cli.send_verification_email", fake_send)

    result = run_cli(app, SIGNUP_OK)

    assert "Account created successfully" in result.output
    assert "Please verify your email before logging in." in result.output
    assert sent["email"] == "new@example.com"
    assert "/api/auth/verify-email/" in sent["url"]

    user = User.query.filter_by(email="new@example.com").first()
    assert user is not None
    assert user.email_verified is False
    assert user.password_hash != "Strongpass1"


def test_signup_still_succeeds_when_the_email_cannot_be_sent(app, monkeypatch):
    monkeypatch.setattr("app.cli.send_verification_email", lambda email, url: False)
    result = run_cli(app, SIGNUP_OK)
    assert "Account created successfully" in result.output
    assert "Account created successfully" in result.output


def test_signup_shows_friendly_messages_for_invalid_input(app, monkeypatch):
    monkeypatch.setattr("app.cli.send_verification_email", lambda email, url: True)
    bad = "1\nNew Person\nnot-an-email\nStrongpass1\nStrongpass1\n\ncontributor\n3\n"
    result = run_cli(app, bad)
    assert "Please fix these problems" in result.output
    assert "email" in result.output.lower()
    assert "Traceback" not in result.output
    assert User.query.filter_by(email="not-an-email").first() is None


def test_signup_rejects_a_short_password(app, monkeypatch):
    monkeypatch.setattr("app.cli.send_verification_email", lambda email, url: True)
    short = "1\nNew Person\nnew@example.com\nabc\nabc\n\ncontributor\n3\n"
    result = run_cli(app, short)
    assert "password" in result.output.lower()
    assert User.query.filter_by(email="new@example.com").first() is None


def test_signup_rejects_a_duplicate_email(app, make_user, monkeypatch):
    make_user(email="new@example.com")
    monkeypatch.setattr("app.cli.send_verification_email", lambda email, url: True)
    result = run_cli(app, SIGNUP_OK)
    assert "already exists" in result.output
    assert User.query.filter_by(email="new@example.com").count() == 1


def test_signup_cannot_create_an_admin(app, monkeypatch):
    monkeypatch.setattr("app.cli.send_verification_email", lambda email, url: True)
    # "admin" is not an allowed account type, so the prompt asks again and the
    # test then falls back to a valid type.
    attempt = (
        "1\nNew Person\nnew@example.com\nStrongpass1\nStrongpass1\n\n"
        "admin\ncontributor\n3\n"
    )
    result = run_cli(app, attempt)
    user = User.query.filter_by(email="new@example.com").first()
    assert user is not None
    assert user.role == "contributor"
    assert "Please enter 1, 2, organizer, or contributor." in result.output


# ---------- exit ----------


def test_exit_from_the_main_menu(app):
    result = run_cli(app, "3\n")
    assert result.exit_code == 0
    assert "Exiting Harambee Hub CLI" in result.output
    