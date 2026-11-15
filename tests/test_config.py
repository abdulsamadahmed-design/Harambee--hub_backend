import pytest

from app import create_app
from app.config import Config


@pytest.mark.parametrize("secret_name", ["SECRET_KEY", "JWT_SECRET_KEY"])
def test_app_rejects_missing_required_secret(monkeypatch, secret_name):
    monkeypatch.setattr(Config, secret_name, None)

    with pytest.raises(RuntimeError, match=secret_name):
        create_app()
