import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "development-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///harambee.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False