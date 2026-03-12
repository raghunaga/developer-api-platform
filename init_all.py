#!/usr/bin/env python3
"""Initialize database and seed with mock data."""

import logging
import sys
from app.db.database import Database, initialize_db, create_db_tables
from app.services.database_seeder import DatabaseSeeder

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize and seed database."""
    try:
        logger.info("=" * 60)
        logger.info("Hierarchical Device Dashboard - Database Initialization")
        logger.info("=" * 60)
        
        # Step 1: Initialize database
        logger.info("\n[1/3] Initializing database...")
        initialize_db()
        create_db_tables()
        logger.info("✓ Database initialized successfully")
        
        # Step 2: Seed database
        logger.info("\n[2/3] Seeding database with mock data...")
        db = Database()
        session = db.get_session()
        seeder = DatabaseSeeder(session)
        counts = seeder.seed_all()
        logger.info("✓ Database seeding completed")
        
        # Step 3: Verify seeding
        logger.info("\n[3/3] Verifying seeding...")
        verification = seeder.verify_seeding()
        logger.info("✓ Verification completed")
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("SEEDING SUMMARY")
        logger.info("=" * 60)
        
        expected = {
            "tenants": 1,
            "customers": 2,
            "sites": 10,
            "gateways": 30,
            "devices": 300,
            "users": 50,
            "data_streams": 900,
        }
        
        all_match = True
        for entity_type, expected_count in expected.items():
            actual_count = verification.get(entity_type, 0)
            status = "✓" if actual_count == expected_count else "✗"
            logger.info(f"{status} {entity_type:20s}: {actual_count:5d} (expected {expected_count})")
            if actual_count != expected_count:
                all_match = False
        
        logger.info("=" * 60)
        
        if all_match:
            logger.info("✓ All counts match expected values!")
            logger.info("✓ Database is ready for use")
            return 0
        else:
            logger.warning("✗ Some counts do not match expected values")
            return 1
            
    except Exception as e:
        logger.error(f"✗ Error during initialization: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
