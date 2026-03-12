#!/usr/bin/env python3
"""Initialize the database with schema."""

import logging
from app.config import setup_logging, settings
from app.db import Database

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


def main():
    """Initialize database."""
    logger.info(f"Initializing database at {settings.database_url}")

    db = Database(settings.database_url)
    db.initialize()
    db.create_tables()

    logger.info("Database initialized successfully")
    logger.info("Tables created:")
    logger.info("  - tenants")
    logger.info("  - customers")
    logger.info("  - sites")
    logger.info("  - gateways")
    logger.info("  - devices")
    logger.info("  - users")
    logger.info("  - data_streams")


if __name__ == "__main__":
    main()
