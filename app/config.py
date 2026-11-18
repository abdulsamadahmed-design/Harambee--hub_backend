import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "sqlite:///harambee.db")

if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)


class Config:
    HARAMBEE_ENV = os.getenv("HARAMBEE_ENV", "production").lower()
    SQLALCHEMY_DATABASE_URI = db_url

    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)

    MAX_CONTENT_LENGTH = 6 * 1024 * 1024
