import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789-abcdefghijklmnop"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-0123456789-abcdefghij"

import pytest  #E402
from flask_jwt_extended import create_access_token  # E402

from app import create_app #E402
from app.extensions import db  # E402
from app.models.user import User  # E402


@pytest.fixture()
def app():
    """A fresh app with its own empty in-memory database for every test."""
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
    

        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    """Create a user straight in the database.

    Usage:  user = make_user(role="organizer")
    """
    counter = {"n": 0}

    def _make(role="contributor", email=None, password="secret123", name="Test User"):
        counter["n"] += 1
        user = User(
            name=name,
            email=email or f"user{counter['n']}@example.com",
            role=role,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make


@pytest.fixture()
def auth_header(app):
    """Build an Authorization header for a user.

    Usage:  client.get(url, headers=auth_header(user))
    Pass with_role=False to make a token that has no role claim.
    """

    def _header(user, with_role=True, **token_options):
        claims = {"role": user.role} if with_role else {}
        token = create_access_token(
            identity=str(user.id), additional_claims=claims, **token_options
        )
        return {"Authorization": f"Bearer {token}"}

    return _header
