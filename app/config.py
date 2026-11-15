import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def get_database_url():
    # Hosting sites often give a postgres:// link, but SQLAlchemy needs postgresql://
    url = os.getenv("DATABASE_URL", "sqlite:///harambee.db")
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    # development or production (production refuses the default secret keys)
    APP_ENV = os.getenv("APP_ENV", "development")
    # Where the React app runs (used in the links we email)
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    # Websites allowed to call this API, comma separated in .env
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", os.getenv("FRONTEND_URL", "http://localhost:5173")).split(",")
    # Check a database connection is alive before using it
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_DATABASE_URI = get_database_url()

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
