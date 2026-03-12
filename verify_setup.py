#!/usr/bin/env python3
"""Verify the project setup and core functionality."""

import logging
import tempfile
import os
from datetime import datetime

from app.config import setup_logging, settings
from app.db import Database
from app.models import (
    Tenant,
    Customer,
    Site,
    Gateway,
    Device,
    User,
    DataStream,
)

setup_logging("INFO")
logger = logging.getLogger(__name__)


def test_models():
    """Test that all models can be instantiated."""
    logger.info("Testing model instantiation...")

    tenant = Tenant(
        id="tenant-1",
        name="Test Tenant",
        identifier="test-tenant",
        status="active",
    )
    assert tenant.id == "tenant-1"
    logger.info("✓ Tenant model works")

    customer = Customer(
        id="customer-1",
        tenant_id="tenant-1",
        name="Test Customer",
        identifier="test-customer",
        status="active",
    )
    assert customer.id == "customer-1"
    logger.info("✓ Customer model works")

    site = Site(
        id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Site",
        identifier="test-site",
        location="New York",
    )
    assert site.id == "site-1"
    logger.info("✓ Site model works")

    gateway = Gateway(
        id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Gateway",
        identifier="test-gateway",
        gateway_type="edge-device",
        status="online",
    )
    assert gateway.id == "gateway-1"
    logger.info("✓ Gateway model works")

    device = Device(
        id="device-1",
        gateway_id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Device",
        identifier="test-device",
        device_type="sensor",
        status="online",
    )
    assert device.id == "device-1"
    logger.info("✓ Device model works")

    user = User(
        id="user-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test User",
        identifier="test-user",
        role="operator",
    )
    assert user.id == "user-1"
    logger.info("✓ User model works")

    datastream = DataStream(
        id="stream-1",
        device_id="device-1",
        gateway_id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Temperature Stream",
        identifier="temp-stream",
        data_type="temperature",
        unit="celsius",
    )
    assert datastream.id == "stream-1"
    logger.info("✓ DataStream model works")


def test_database_operations():
    """Test database operations with a temporary database."""
    logger.info("\nTesting database operations...")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"

        db = Database(db_url)
        db.initialize()
        logger.info("✓ Database initialized")

        db.create_tables()
        logger.info("✓ Tables created")

        session = db.get_session()
        try:
            # Create a complete hierarchy
            tenant = Tenant(
                id="tenant-1",
                name="Test Tenant",
                identifier="test-tenant",
                status="active",
            )
            customer = Customer(
                id="customer-1",
                tenant_id="tenant-1",
                name="Test Customer",
                identifier="test-customer",
                status="active",
            )
            site = Site(
                id="site-1",
                customer_id="customer-1",
                tenant_id="tenant-1",
                name="Test Site",
                identifier="test-site",
                location="New York",
            )
            gateway = Gateway(
                id="gateway-1",
                site_id="site-1",
                customer_id="customer-1",
                tenant_id="tenant-1",
                name="Test Gateway",
                identifier="test-gateway",
                gateway_type="edge-device",
                status="online",
            )
            device = Device(
                id="device-1",
                gateway_id="gateway-1",
                site_id="site-1",
                customer_id="customer-1",
                tenant_id="tenant-1",
                name="Test Device",
                identifier="test-device",
                device_type="sensor",
                status="online",
            )
            user = User(
                id="user-1",
                site_id="site-1",
                customer_id="customer-1",
                tenant_id="tenant-1",
                name="Test User",
                identifier="test-user",
                role="operator",
            )
            datastream = DataStream(
                id="stream-1",
                device_id="device-1",
                gateway_id="gateway-1",
                site_id="site-1",
                customer_id="customer-1",
                tenant_id="tenant-1",
                name="Temperature Stream",
                identifier="temp-stream",
                data_type="temperature",
                unit="celsius",
            )

            session.add_all([tenant, customer, site, gateway, device, user, datastream])
            session.commit()
            logger.info("✓ Hierarchy inserted successfully")

            # Retrieve and verify
            retrieved_device = session.query(Device).filter_by(id="device-1").first()
            assert retrieved_device is not None
            assert retrieved_device.name == "Test Device"
            logger.info("✓ Device retrieved successfully")

            retrieved_gateway = session.query(Gateway).filter_by(id="gateway-1").first()
            assert retrieved_gateway is not None
            assert len(retrieved_gateway.devices) == 1
            logger.info("✓ Gateway relationships work")

            retrieved_site = session.query(Site).filter_by(id="site-1").first()
            assert retrieved_site is not None
            assert len(retrieved_site.gateways) == 1
            assert len(retrieved_site.users) == 1
            logger.info("✓ Site relationships work")

            retrieved_customer = session.query(Customer).filter_by(id="customer-1").first()
            assert retrieved_customer is not None
            assert len(retrieved_customer.sites) == 1
            logger.info("✓ Customer relationships work")

        finally:
            session.close()

        db.close()
        logger.info("✓ Database closed successfully")


def main():
    """Run all verification tests."""
    logger.info("=" * 60)
    logger.info("Hierarchical Device Dashboard - Setup Verification")
    logger.info("=" * 60)

    try:
        test_models()
        test_database_operations()

        logger.info("\n" + "=" * 60)
        logger.info("✓ All verification tests passed!")
        logger.info("=" * 60)
        logger.info("\nProject structure is ready for implementation:")
        logger.info("  - Core data models defined (Tenant, Customer, Site, etc.)")
        logger.info("  - SQLAlchemy ORM configured")
        logger.info("  - SQLite database setup")
        logger.info("  - Logging and configuration management")
        logger.info("  - Database initialization and migration support")
        logger.info("\nNext steps:")
        logger.info("  1. Implement hierarchical data access layer (Task 1.2)")
        logger.info("  2. Add CRDT-based state management (Task 1.4)")
        logger.info("  3. Implement offline-first caching (Task 1.6)")

    except Exception as e:
        logger.error(f"✗ Verification failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
