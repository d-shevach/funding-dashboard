"""Configuration management using environment variables"""

import os
import secrets
from dotenv import load_dotenv
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Application configuration from environment variables"""

    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "caixa")
    DB_POOL_SIZE = 5
    DB_POOL_NAME = "funding_pool"

    # APIs
    OPENEXCHANGERATES_API_KEY = os.getenv("OPENEXCHANGERATES_API_KEY", "")

    # Application
    APP_LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO")
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
    FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

    # Backup
    BACKUP_BUCKET = os.getenv("BACKUP_BUCKET", "")

    # Email (daily report)
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM = os.getenv("SMTP_FROM", "")

    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent
    LOG_DIR = PROJECT_ROOT / "logs"

    @classmethod
    def validate(cls):
        """Validate that required environment variables are set"""
        required = ["DB_PASSWORD", "OPENEXCHANGERATES_API_KEY"]
        missing = [var for var in required if not getattr(cls, var)]

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        # Create logs directory if it doesn't exist
        cls.LOG_DIR.mkdir(exist_ok=True)
