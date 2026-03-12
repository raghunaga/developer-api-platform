"""Tests for database initialization and operations."""

import pytest
import tempfile
import os
from sqlalchemy import inspect

from app.db import Database
from app.models import Tenant, Customer, Site, Gateway, Device, User, DataStream


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_url = f"sqlite:///{db_path}"
        db = Database(db_url)
        db.initialize()
        yield db
        db.close()


def test_database_initialization(temp_db):
    """Test database initialization."""
    assert temp_db.engine is not None
    assert temp_db.SessionLocal is not None


def test_create_tables(temp_db):
    """Test creating database tables."""
    temp_db.create_tables()

    # Verify tables exist
    inspector = inspect(temp_db.engine)
    tables = inspector.get_table_names()

    expected_tables = [
        "tenants",
        "customers",
        "sites",
        "gateways",
        "devices",
        "users",
        "data_streams",
    ]

    for table in expected_tables:
        assert table in tables, f"Table {table} not found in database"


def test_insert_and_retrieve_tenant(temp_db):
    """Test inserting and retrieving a tenant."""
    temp_db.create_tables()

    session = temp_db.get_session()
    try:
        tenant = Tenant(
            id="tenant-1",
            name="Test Tenant",
            identifier="test-tenant",
            status="active",
        )
        session.add(tenant)
        session.commit()

        # Retrieve the tenant
        retrieved = session.query(Tenant).filter_by(id="tenant-1").first()
        assert retrieved is not None
        assert retrieved.name == "Test Tenant"
        assert retrieved.identifier == "test-tenant"
    finally:
        session.close()


def test_insert_and_retrieve_hierarchy(temp_db):
    """Test inserting and retrieving a complete hierarchy."""
    temp_db.create_tables()

    session = temp_db.get_session()
    try:
        # Create hierarchy
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

        session.add_all([tenant, customer, site, gateway, device])
        session.commit()

        # Retrieve and verify
        retrieved_device = session.query(Device).filter_by(id="device-1").first()
        assert retrieved_device is not None
        assert retrieved_device.name == "Test Device"
        assert retrieved_device.gateway_id == "gateway-1"

        retrieved_gateway = session.query(Gateway).filter_by(id="gateway-1").first()
        assert retrieved_gateway is not None
        assert len(retrieved_gateway.devices) == 1
        assert retrieved_gateway.devices[0].id == "device-1"

    finally:
        session.close()


def test_drop_tables(temp_db):
    """Test dropping database tables."""
    temp_db.create_tables()

    # Verify tables exist
    inspector = inspect(temp_db.engine)
    tables_before = inspector.get_table_names()
    assert len(tables_before) > 0

    # Drop tables
    temp_db.drop_tables()

    # Verify tables are gone
    inspector = inspect(temp_db.engine)
    tables_after = inspector.get_table_names()
    assert len(tables_after) == 0
