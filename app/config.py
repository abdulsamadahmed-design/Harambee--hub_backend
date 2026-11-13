import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///harambee.db")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)