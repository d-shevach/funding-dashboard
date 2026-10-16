"""User accounts for dashboard login"""

from werkzeug.security import generate_password_hash, check_password_hash
from src.database import Database
from src.logger import get_logger

logger = get_logger("web.auth")


def ensure_users_table():
    Database.execute_transaction([(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            email VARCHAR(255) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        (),
    )])
    has_email = Database.fetch_one(
        """
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'usuarios' AND COLUMN_NAME = 'email'
        """
    )[0]
    if not has_email:
        Database.execute_transaction([(
            "ALTER TABLE usuarios ADD COLUMN email VARCHAR(255) NULL",
            (),
        )])


def create_or_update_user(username: str, password: str, email: str = None):
    password_hash = generate_password_hash(password)
    Database.execute_transaction([(
        """
        INSERT INTO usuarios (username, password_hash, email) VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash), email = VALUES(email)
        """,
        (username, password_hash, email or None),
    )])
    logger.info(f"User saved: {username}")


def list_report_recipients() -> list:
    rows = Database.fetch_all(
        "SELECT email FROM usuarios WHERE email IS NOT NULL AND email <> ''"
    )
    return [row[0] for row in rows]


def verify_credentials(username: str, password: str) -> bool:
    row = Database.fetch_one(
        "SELECT password_hash FROM usuarios WHERE username = %s",
        (username,),
    )
    if not row:
        return False
    return check_password_hash(row[0], password)
