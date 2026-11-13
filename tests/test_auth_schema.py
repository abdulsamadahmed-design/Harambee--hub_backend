import pytest
from marshmallow import ValidationError

from app.schemas.auth_schema import LoginSchema


def test_valid_input_loads():
    data = LoginSchema().load({"email": "amina@example.com", "password": "secret123"})
    assert data == {"email": "amina@example.com", "password": "secret123"}


def test_email_is_trimmed_and_lowercased():
    data = LoginSchema().load({"email": "  Amina@Example.COM ", "password": "x"})
    assert data["email"] == "amina@example.com"


def test_password_is_not_modified():
    data = LoginSchema().load({"email": "a@b.co", "password": "  keep my spaces  "})
    assert data["password"] == "  keep my spaces  "


def test_missing_email_gives_clear_message():
    with pytest.raises(ValidationError) as error:
        LoginSchema().load({"password": "secret123"})
    assert error.value.messages["email"] == ["Email is required."]


@pytest.mark.parametrize("bad_email", ["nope", "a@", "@b.com", "", "   ", 123, None])
def test_invalid_email_is_rejected(bad_email):
    with pytest.raises(ValidationError) as error:
        LoginSchema().load({"email": bad_email, "password": "secret123"})
    assert "email" in error.value.messages


def test_missing_password_gives_clear_message():
    with pytest.raises(ValidationError) as error:
        LoginSchema().load({"email": "amina@example.com"})
    assert error.value.messages["password"] == ["Password is required."]


@pytest.mark.parametrize("bad_password", ["", None, 12345])
def test_invalid_password_is_rejected(bad_password):
    with pytest.raises(ValidationError) as error:
        LoginSchema().load({"email": "amina@example.com", "password": bad_password})
    assert "password" in error.value.messages


def test_both_errors_are_reported_together():
    with pytest.raises(ValidationError) as error:
        LoginSchema().load({})
    assert set(error.value.messages) == {"email", "password"}


def test_extra_fields_are_ignored():
    data = LoginSchema().load(
        {"email": "a@b.co", "password": "x", "remember_me": True, "role": "admin"}
    )
    assert data == {"email": "a@b.co", "password": "x"}


@pytest.mark.parametrize("not_a_dict", [[], "text", 42, None])
def test_non_object_input_is_rejected_without_crashing(not_a_dict):
    with pytest.raises(ValidationError):
        LoginSchema().load(not_a_dict)
