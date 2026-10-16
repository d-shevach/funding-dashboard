"""Logging configuration for the application"""

import logging
import logging.handlers
from datetime import datetime
from src.config import Config

# Create logger
logger = logging.getLogger("funding_accounting")
logger.setLevel(getattr(logging, Config.APP_LOG_LEVEL))

# Create formatters
detailed_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

simple_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(simple_formatter)
logger.addHandler(console_handler)

# File handler (rotated daily)
log_file = Config.LOG_DIR / f"funding_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = logging.handlers.RotatingFileHandler(
    log_file,
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=10,
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(detailed_formatter)
logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module"""
    return logging.getLogger(f"funding_accounting.{name}")
