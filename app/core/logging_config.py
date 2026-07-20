import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    # Ensure logs folder exists in the current working directory
    os.makedirs("logs", exist_ok=True)

    # Formatting standard
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    max_bytes = 5 * 1024 * 1024  # 5 MB
    backup_count = 5

    # 1. Console Stream Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 2. General App Log Handler
    app_handler = RotatingFileHandler(
        "logs/app.log", maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)

    # 3. Centralized Errors Log Handler
    errors_handler = RotatingFileHandler(
        "logs/errors.log", maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    errors_handler.setLevel(logging.ERROR)
    errors_handler.setFormatter(formatter)

    # 4. Auth Audit Log Handler
    auth_handler = RotatingFileHandler(
        "logs/auth.log", maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    auth_handler.setLevel(logging.INFO)
    auth_handler.setFormatter(formatter)

    # Configure Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    root_logger.addHandler(app_handler)
    root_logger.addHandler(errors_handler)
    root_logger.addHandler(console_handler)

    # Configure Auth Specific Logger
    auth_logger = logging.getLogger("auth")
    auth_logger.setLevel(logging.INFO)
    auth_logger.handlers = []
    auth_logger.addHandler(auth_handler)
    auth_logger.addHandler(console_handler)
    auth_logger.propagate = False
