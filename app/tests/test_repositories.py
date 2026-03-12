"""Tests for repository classes and hierarchy traversal."""

import pytest
from datetime import datetime
from sqlalchemy.orm import Session

# Import models first to register them with Base
from app.models.entities import (
    Tenant, Customer, Site, Gateway, Device, User, DataStream
)
from app.db.database import Database
from app.db.repositories import (
    TenantRepository, CustomerRepository, SiteRepository,
    GatewayRepository, DeviceRepository, UserRepository,
    DataStreamRepository, RepositoryFactory
)


@pytest.fixture
def db():
    """Create an in-memory SQLite database for testing."""
    # Ensure models are imported and registered with Base
    from app.models.base import Base
    from app.models import entities  # noqa: F401
    
    database = Database("sqlite:///:memory:")
    database.initialize()
    database.create_tables()
    yield database
    database.drop_tables()
    database.close()


@pytest.fixture
def session(db):
    """Create a database session for testing."""
    return db.get_session()


@pytest.fixture
def sample_data(session):
    """Create sample data for testing."""
    # Create tenant
    tenant = Tenant(
        id="tenant-1",
        name="Test Tenant",
        identifier="test-tenant",
        status="active"
    )
    session.add(tenant)
    session.flush()

    # Create customer
    customer = Customer(
        id="customer-1",
        tenant_id="tenant-1",
        name="Test Customer",
        identifier="test-customer",
        status="active"
    )
    session.add(customer)
    session.flush()

    # Create site
    site = Site(
        id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Site",
        identifier="test-site",
        location="New York"
    )
    session.add(site)
    session.flush()

    # Create gateway
    gateway = Gateway(
        id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Gateway",
        identifier="test-gateway",
        gateway_type="edge",
        status="online"
    )
    session.add(gateway)
    session.flush()

    # Create device
    device = Device(
        id="device-1",
        gateway_id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test Device",
        identifier="test-device",
        device_type="sensor",
        status="online"
    )
    session.add(device)
    session.flush()

    # Create user
    user = User(
        id="user-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Test User",
        identifier="test-user",
        role="operator"
    )
    session.add(user)
    session.flush()

    # Create data stream
    data_stream = DataStream(
        id="stream-1",
        device_id="device-1",
        gateway_id="gateway-1",
        site_id="site-1",
        customer_id="customer-1",
        tenant_id="tenant-1",
        name="Temperature Stream",
        identifier="temp-stream",
        data_type="temperature",
        unit="celsius"
    )
    session.add(data_stream)
    session.commit()

    return {
        "tenant": tenant,
        "customer": customer,
        "site": site,
        "gateway": gateway,
        "device": device,
        "user": user,
        "data_stream": data_stream
    }


class TestTenantRepository:
    """Tests for TenantRepository."""

    def test_create_tenant(self, session):
        """Test creating a tenant."""
        repo = TenantRepository(session)
        tenant = repo.create(
            id="tenant-1",
            name="Test Tenant",
            identifier="test-tenant",
            status="active"
        )
        repo.commit()

        assert tenant.id == "tenant-1"
        assert tenant.name == "Test Tenant"
        assert tenant.identifier == "test-tenant"

    def test_get_tenant_by_id(self, session, sample_data):
        """Test getting a tenant by ID."""
        repo = TenantRepository(session)
        tenant = repo.get_by_id("tenant-1")

        assert tenant is not None
        assert tenant.name == "Test Tenant"

    def test_get_tenant_by_identifier(self, session, sample_data):
        """Test getting a tenant by identifier."""
        repo = TenantRepository(session)
        tenant = repo.get_by_identifier("test-tenant")

        assert tenant is not None
        assert tenant.id == "tenant-1"

    def test_get_active_tenants(self, session, sample_data):
        """Test getting all active tenants."""
        repo = TenantRepository(session)
        tenants = repo.get_active_tenants()

        assert len(tenants) >= 1
        assert all(t.status == "active" for t in tenants)


class TestCustomerRepository:
    """Tests for CustomerRepository."""

    def test_get_by_tenant(self, session, sample_data):
        """Test getting customers by tenant."""
        repo = CustomerRepository(session)
        customers = repo.get_by_tenant("tenant-1")

        assert len(customers) == 1
        assert customers[0].id == "customer-1"

    def test_get_parent(self, session, sample_data):
        """Test getting parent tenant of a customer."""
        repo = CustomerRepository(session)
        parent = repo.get_parent("customer-1")

        assert parent is not None
        assert parent.id == "tenant-1"

    def test_get_children(self, session, sample_data):
        """Test getting children (sites) of a customer."""
        repo = CustomerRepository(session)
        children = repo.get_children("customer-1")

        assert len(children) == 1
        assert children[0].id == "site-1"

    def test_get_path(self, session, sample_data):
        """Test getting hierarchy path for a customer."""
        repo = CustomerRepository(session)
        path = repo.get_path("customer-1")

        assert len(path) == 2
        assert path[0] == ("tenant", "tenant-1")
        assert path[1] == ("customer", "customer-1")

    def test_get_path_nonexistent(self, session):
        """Test getting path for nonexistent customer."""
        repo = CustomerRepository(session)
        path = repo.get_path("nonexistent")

        assert path == []


class TestSiteRepository:
    """Tests for SiteRepository."""

    def test_get_by_customer(self, session, sample_data):
        """Test getting sites by customer."""
        repo = SiteRepository(session)
        sites = repo.get_by_customer("customer-1")

        assert len(sites) == 1
        assert sites[0].id == "site-1"

    def test_get_parent(self, session, sample_data):
        """Test getting parent customer of a site."""
        repo = SiteRepository(session)
        parent = repo.get_parent("site-1")

        assert parent is not None
        assert parent.id == "customer-1"

    def test_get_children(self, session, sample_data):
        """Test getting children (gateways and users) of a site."""
        repo = SiteRepository(session)
        gateways, users = repo.get_children("site-1")

        assert len(gateways) == 1
        assert gateways[0].id == "gateway-1"
        assert len(users) == 1
        assert users[0].id == "user-1"

    def test_get_path(self, session, sample_data):
        """Test getting hierarchy path for a site."""
        repo = SiteRepository(session)
        path = repo.get_path("site-1")

        assert len(path) == 3
        assert path[0] == ("tenant", "tenant-1")
        assert path[1] == ("customer", "customer-1")
        assert path[2] == ("site", "site-1")


class TestGatewayRepository:
    """Tests for GatewayRepository."""

    def test_get_by_site(self, session, sample_data):
        """Test getting gateways by site."""
        repo = GatewayRepository(session)
        gateways = repo.get_by_site("site-1")

        assert len(gateways) == 1
        assert gateways[0].id == "gateway-1"

    def test_get_parent(self, session, sample_data):
        """Test getting parent site of a gateway."""
        repo = GatewayRepository(session)
        parent = repo.get_parent("gateway-1")

        assert parent is not None
        assert parent.id == "site-1"

    def test_get_children(self, session, sample_data):
        """Test getting children (devices) of a gateway."""
        repo = GatewayRepository(session)
        children = repo.get_children("gateway-1")

        assert len(children) == 1
        assert children[0].id == "device-1"

    def test_get_path(self, session, sample_data):
        """Test getting hierarchy path for a gateway."""
        repo = GatewayRepository(session)
        path = repo.get_path("gateway-1")

        assert len(path) == 4
        assert path[0] == ("tenant", "tenant-1")
        assert path[1] == ("customer", "customer-1")
        assert path[2] == ("site", "site-1")
        assert path[3] == ("gateway", "gateway-1")

    def test_get_by_status(self, session, sample_data):
        """Test getting gateways by status."""
        repo = GatewayRepository(session)
        gateways = repo.get_by_status("online")

        assert len(gateways) >= 1
        assert all(g.status == "online" for g in gateways)


class TestDeviceRepository:
    """Tests for DeviceRepository."""

    def test_get_by_gateway(self, session, sample_data):
        """Test getting devices by gateway."""
        repo = DeviceRepository(session)
        devices = repo.get_by_gateway("gateway-1")

        assert len(devices) == 1
        assert devices[0].id == "device-1"

    def test_get_by_site(self, session, sample_data):
        """Test getting devices by site."""
        repo = DeviceRepository(session)
        devices = repo.get_by_site("site-1")

        assert len(devices) == 1
        assert devices[0].id == "device-1"

    def test_get_by_customer(self, session, sample_data):
        """Test getting devices by customer."""
        repo = DeviceRepository(session)
        devices = repo.get_by_customer("customer-1")

        assert len(devices) == 1
        assert devices[0].id == "device-1"

    def test_get_parent(self, session, sample_data):
        """Test getting parent gateway of a device."""
        repo = DeviceRepository(session)
        parent = repo.get_parent("device-1")

        assert parent is not None
        assert parent.id == "gateway-1"

    def test_get_children(self, session, sample_data):
        """Test getting children (data streams) of a device."""
        repo = DeviceRepository(session)
        children = repo.get_children("device-1")

        assert len(children) == 1
        assert children[0].id == "stream-1"

    def test_get_path(self, session, sample_data):
        """Test getting hierarchy path for a device."""
        repo = DeviceRepository(session)
        path = repo.get_path("device-1")

        assert len(path) == 5
        assert path[0] == ("tenant", "tenant-1")
        assert path[1] == ("customer", "customer-1")
        assert path[2] == ("site", "site-1")
        assert path[3] == ("gateway", "gateway-1")
        assert path[4] == ("device", "device-1")

    def test_get_by_status(self, session, sample_data):
        """Test getting devices by status."""
        repo = DeviceRepository(session)
        devices = repo.get_by_status("online")

        assert len(devices) >= 1
        assert all(d.status == "online" for d in devices)


class TestUserRepository:
    """Tests for UserRepository."""

    def test_get_by_site(self, session, sample_data):
        """Test getting users by site."""
        repo = UserRepository(session)
        users = repo.get_by_site("site-1")

        assert len(users) == 1
        assert users[0].id == "user-1"

    def test_get_parent(self, session, sample_data):
        """Test getting parent site of a user."""
        repo = UserRepository(session)
        parent = repo.get_parent("user-1")

        assert parent is not None
        assert parent.id == "site-1"

    def test_get_path(self, session, sample_data):
        """Test getting hierarchy path for a user."""
        repo = UserRepository(session)
        path = repo.get_path("user-1")

        assert len(path) == 4
        assert path[0] == ("tenant", "tenant-1")
        assert path[1] == ("customer", "customer-1")
        assert path[2] == ("site", "site-1")
        assert path[3] == ("user", "user-1")

    def test_get_by_role(self, session, sample_data):
        """Test getting users by role."""
        repo = UserRepository(session)
        users = repo.get_by_role("operator")

        assert len(users) >= 1
        assert all(u.role == "operator" for u in users)


class TestDataStreamRepository:
    """Tests for DataStreamRepository."""

    def test_get_by_device(self, session, sample_data):
        """Test getting data streams by device."""
        repo = DataStreamRepository(session)
        streams = repo.get_by_device("device-1")

        assert len(streams) == 1
        assert streams[0].id == "stream-1"

    def test_get_parent(self, session, sample_data):
        """Test getting parent device of a data stream."""
        repo = DataStreamRepository(session)
        parent = repo.get_parent("stream-1")

        assert parent is not None
        assert parent.id == "device-1"

    def test_get_path(self, session, sample_data):
        """Test getting hierarchy path for a data stream."""
        repo = DataStreamRepository(session)
        path = repo.get_path("stream-1")

        assert len(path) == 6
        assert path[0] == ("tenant", "tenant-1")
        assert path[1] == ("customer", "customer-1")
        assert path[2] == ("site", "site-1")
        assert path[3] == ("gateway", "gateway-1")
        assert path[4] == ("device", "device-1")
        assert path[5] == ("data_stream", "stream-1")

    def test_get_by_data_type(self, session, sample_data):
        """Test getting data streams by data type."""
        repo = DataStreamRepository(session)
        streams = repo.get_by_data_type("temperature")

        assert len(streams) >= 1
        assert all(s.data_type == "temperature" for s in streams)


class TestRepositoryFactory:
    """Tests for RepositoryFactory."""

    def test_factory_creates_repositories(self, session):
        """Test that factory creates all repository types."""
        factory = RepositoryFactory(session)

        assert isinstance(factory.get_tenant_repository(), TenantRepository)
        assert isinstance(factory.get_customer_repository(), CustomerRepository)
        assert isinstance(factory.get_site_repository(), SiteRepository)
        assert isinstance(factory.get_gateway_repository(), GatewayRepository)
        assert isinstance(factory.get_device_repository(), DeviceRepository)
        assert isinstance(factory.get_user_repository(), UserRepository)
        assert isinstance(factory.get_data_stream_repository(), DataStreamRepository)

    def test_factory_caches_repositories(self, session):
        """Test that factory caches repository instances."""
        factory = RepositoryFactory(session)

        repo1 = factory.get_tenant_repository()
        repo2 = factory.get_tenant_repository()

        assert repo1 is repo2


class TestHierarchyConsistency:
    """Tests for hierarchy consistency and bidirectional relationships."""

    def test_parent_child_consistency(self, session, sample_data):
        """Test that parent-child relationships are consistent."""
        # Customer -> Site
        customer_repo = CustomerRepository(session)
        site_repo = SiteRepository(session)

        customer = customer_repo.get_by_id("customer-1")
        sites = customer_repo.get_children("customer-1")
        site = site_repo.get_by_id("site-1")
        parent = site_repo.get_parent("site-1")

        assert len(sites) == 1
        assert sites[0].id == site.id
        assert parent.id == customer.id

    def test_hierarchy_path_acyclic(self, session, sample_data):
        """Test that hierarchy paths are acyclic."""
        device_repo = DeviceRepository(session)
        path = device_repo.get_path("device-1")

        # Check that all entity types are unique (no cycles)
        entity_types = [entity_type for entity_type, _ in path]
        assert len(entity_types) == len(set(entity_types))

    def test_hierarchy_path_valid(self, session, sample_data):
        """Test that hierarchy paths are valid."""
        device_repo = DeviceRepository(session)
        path = device_repo.get_path("device-1")

        # Expected order: tenant -> customer -> site -> gateway -> device
        expected_order = ["tenant", "customer", "site", "gateway", "device"]
        actual_order = [entity_type for entity_type, _ in path]

        assert actual_order == expected_order

    def test_multiple_hierarchy_levels(self, session, sample_data):
        """Test traversal through multiple hierarchy levels."""
        # Create additional levels
        gateway_repo = GatewayRepository(session)
        device_repo = DeviceRepository(session)
        stream_repo = DataStreamRepository(session)

        # Traverse from gateway to device to stream
        gateway = gateway_repo.get_by_id("gateway-1")
        devices = gateway_repo.get_children("gateway-1")
        device = devices[0]
        streams = device_repo.get_children(device.id)
        stream = streams[0]

        assert gateway.id == "gateway-1"
        assert device.id == "device-1"
        assert stream.id == "stream-1"


class TestTransactionManagement:
    """Tests for transaction management."""

    def test_transaction_commit(self, db):
        """Test transaction commit."""
        with db.transaction() as session:
            tenant = Tenant(
                id="tenant-tx-1",
                name="Transaction Test",
                identifier="tx-test",
                status="active"
            )
            session.add(tenant)

        # Verify data was committed
        session = db.get_session()
        repo = TenantRepository(session)
        tenant = repo.get_by_id("tenant-tx-1")
        assert tenant is not None
        session.close()

    def test_transaction_rollback(self, db):
        """Test transaction rollback on error."""
        try:
            with db.transaction() as session:
                tenant = Tenant(
                    id="tenant-tx-2",
                    name="Rollback Test",
                    identifier="tx-rollback",
                    status="active"
                )
                session.add(tenant)
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify data was rolled back
        session = db.get_session()
        repo = TenantRepository(session)
        tenant = repo.get_by_id("tenant-tx-2")
        assert tenant is None
        session.close()
